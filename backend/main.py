"""FastAPI backend for the HR policy RAG assistant.

Run from the project root:
    python -m uvicorn backend.main:app --reload
"""

from __future__ import annotations

import base64
from datetime import datetime
import hashlib
import hmac
from io import BytesIO
import json
import logging
import os
from pathlib import Path
import re
import secrets
from time import perf_counter, time
from typing import Any
import unicodedata
from uuid import uuid4
import zipfile
import xml.etree.ElementTree as ET

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from src.enterprise_rag import is_sensitive_hr_case, user_can_access
from src.enterprise_connectors import HRMConnector, SharePointConnector
from src.llm_provider import generate_text, get_llm_api_key, get_ocr_provider, ocr_enabled, ocr_image_with_provider
from src.task5_semantic_search import semantic_search
from src.task6_lexical_search import lexical_search
from src.task8_pageindex_vectorless import pageindex_search
from src.task9_retrieval_pipeline import retrieve
from src.task10_generation import (
    _acknowledgement_answer,
    _clarification_answer as _shared_clarification_answer,
    _needs_more_information as _shared_needs_more_information,
    generate_with_citation,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("rag_api")

PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=False)

DATA_ROOT = Path(os.getenv("DATA_DIR", str(PROJECT_ROOT / "data"))).resolve()
UPLOAD_LANDING_DIR = DATA_ROOT / "landing" / "uploads"
UPLOAD_STANDARDIZED_DIR = DATA_ROOT / "standardized" / "news"
GOLDEN_DATASET_PATH = PROJECT_ROOT / "group_project" / "evaluation" / "golden_dataset.json"
USERS_PATH = DATA_ROOT / "app_users.json"
PASSWORD_RESET_REQUESTS_PATH = DATA_ROOT / "password_reset_requests.json"
SUPPORT_CONVERSATIONS_PATH = DATA_ROOT / "support_conversations.json"
HR_REQUESTS_PATH = DATA_ROOT / "hr_requests.json"
HR_REQUEST_ATTACHMENTS_DIR = DATA_ROOT / "hr_request_attachments"
CHAT_HISTORY_PATH = DATA_ROOT / "chat_history.json"
NOTIFICATIONS_PATH = DATA_ROOT / "notifications.json"
ANNOUNCEMENTS_PATH = DATA_ROOT / "announcements.json"
ANNOUNCEMENT_ATTACHMENTS_DIR = DATA_ROOT / "announcement_attachments"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
TOKEN_TTL_SECONDS = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", str(7 * 24 * 60 * 60)))
AUTH_SECRET = os.getenv("AUTH_SECRET", "dev-secret-change-me")

ALLOWED_UPLOAD_EXTENSIONS = {
    ".pdf",
    ".ppt",
    ".pptx",
    ".doc",
    ".docx",
    ".txt",
    ".md",
    ".html",
    ".htm",
    ".json",
}
ALLOWED_UPLOAD_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
    "text/html",
    "application/json",
}

BAD_EXTRACTED_TEXT_CHARS = {"\u25a0", "\ufffd"}
BAD_TEXT_RATIO_THRESHOLD = 0.02


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=20)
    score_threshold: float = Field(0.3, ge=0.0, le=1.0)
    use_reranking: bool = True


class GenerateRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=20)


class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1)
    useHyDE: bool = False
    topK: int = Field(5, ge=1, le=20)
    threshold: float = Field(0.3, ge=0.0, le=1.0)
    searchMode: str = "Hybrid kết hợp"
    history: list["ChatTurn"] = Field(default_factory=list, max_length=12)


class ChatTurn(BaseModel):
    role: str
    content: str = Field(..., min_length=1, max_length=4000)


class RetrievalRequest(BaseModel):
    query: str = Field(..., min_length=1)
    method: str = "Hybrid"
    topK: int = Field(5, ge=1, le=20)
    threshold: float = Field(0.3, ge=0.0, le=1.0)


class SourceChunk(BaseModel):
    id: int | None = None
    content: str
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str | None = None


class SearchResponse(BaseModel):
    query: str
    top_k: int
    results: list[SourceChunk]


class GenerateResponse(BaseModel):
    query: str
    answer: str
    retrieval_source: str
    sources: list[SourceChunk]
    context: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    logs: list[str] = Field(default_factory=list)
    traceId: str | None = None
    needsClarification: bool = False
    rewrittenQuery: str | None = None
    handoffRecommended: bool = False


class RetrievalResponse(BaseModel):
    results: list[SourceChunk]
    logs: list[str] = Field(default_factory=list)
    traceId: str | None = None


class UploadResponse(BaseModel):
    status: str
    message: str
    fileName: str
    size: int
    logs: list[str]
    landingPath: str | None = None
    markdownPath: str | None = None


class EvaluationMetricResponse(BaseModel):
    faithfulness: float
    answerRelevance: float
    contextPrecision: float
    contextRecall: float


class ABTestItem(BaseModel):
    name: str
    score: float


class WorstPerformer(BaseModel):
    query: str
    expected: str
    actual: str
    issue: str


class EvaluationResponse(BaseModel):
    metrics: EvaluationMetricResponse
    abTest: list[ABTestItem]
    worstPerformers: list[WorstPerformer]
    goldenDatasetCount: int


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3)
    name: str = Field(..., min_length=1)
    password: str = Field(..., min_length=6)


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., min_length=3)


class MessageResponse(BaseModel):
    status: str
    message: str


class SupportCreateRequest(BaseModel):
    subject: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class SupportMessageRequest(BaseModel):
    content: str = Field(..., min_length=1)


class SupportMessagePublic(BaseModel):
    id: str
    senderId: str
    senderName: str
    senderRole: str
    content: str
    createdAt: str


class SupportConversationPublic(BaseModel):
    id: str
    employeeId: str
    employeeName: str
    employeeEmail: str
    hrId: str | None = None
    hrName: str | None = None
    status: str
    subject: str
    createdAt: str
    updatedAt: str
    acceptedAt: str | None = None
    messages: list[SupportMessagePublic] = Field(default_factory=list)


class HrRequestAttachmentPublic(BaseModel):
    id: str
    fileName: str
    contentType: str
    size: int
    url: str


class HrRequestPublic(BaseModel):
    id: str
    type: str
    title: str
    employeeId: str
    employeeName: str
    employeeEmail: str
    status: str
    leaveType: str
    startDate: str
    endDate: str
    totalDays: float
    reason: str
    contactDuringLeave: str | None = None
    handoverNote: str | None = None
    attachments: list[HrRequestAttachmentPublic] = Field(default_factory=list)
    hrNote: str | None = None
    reviewedBy: str | None = None
    reviewedByName: str | None = None
    reviewedAt: str | None = None
    createdAt: str
    updatedAt: str
    queuePosition: int | None = None


class ChatHistoryItem(BaseModel):
    id: str
    userId: str
    userName: str
    userEmail: str
    query: str
    answer: str
    sources: list[SourceChunk] = Field(default_factory=list)
    traceId: str | None = None
    createdAt: str


class UpdateHrRequestStatusRequest(BaseModel):
    status: str
    hrNote: str | None = None


class NotificationPublic(BaseModel):
    id: str
    userId: str
    type: str
    title: str
    message: str
    relatedType: str | None = None
    relatedId: str | None = None
    read: bool = False
    createdAt: str


class AnnouncementRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    content: str = Field(..., min_length=5, max_length=10000)
    category: str = "general"
    priority: str = "normal"
    audienceType: str = "all_employees"
    department: str | None = None


class AnnouncementReviewRequest(BaseModel):
    action: str
    note: str | None = None


class AnnouncementChatRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=2000)


class AnnouncementPublic(BaseModel):
    id: str
    title: str
    content: str
    category: str
    priority: str
    audienceType: str
    department: str | None = None
    status: str
    createdBy: str
    createdByName: str
    submittedAt: str | None = None
    reviewedBy: str | None = None
    reviewedByName: str | None = None
    reviewedAt: str | None = None
    reviewNote: str | None = None
    publishedAt: str | None = None
    recipientCount: int = 0
    readCount: int = 0
    attachments: list[dict[str, Any]] = Field(default_factory=list)
    createdAt: str
    updatedAt: str


class UserPublic(BaseModel):
    id: str
    email: str
    name: str
    role: str
    department: str = ""
    isActive: bool = True
    annualLeaveDays: float | None = None
    createdAt: str | None = None


class AuthResponse(BaseModel):
    token: str
    user: UserPublic
    message: str | None = None


class CreateUserRequest(BaseModel):
    email: str = Field(..., min_length=3)
    name: str = Field(..., min_length=1)
    password: str = Field(..., min_length=6)
    role: str = "employee"
    department: str = ""
    annualLeaveDays: float | None = Field(default=None, ge=0, le=365)


class UpdateUserRequest(BaseModel):
    email: str | None = None
    name: str | None = None
    role: str | None = None
    department: str | None = None
    password: str | None = Field(default=None, min_length=6)
    isActive: bool | None = None
    annualLeaveDays: float | None = Field(default=None, ge=0, le=365)


class LeaveBalancePublic(BaseModel):
    userId: str
    name: str
    email: str
    role: str
    year: int
    annualEntitlement: float
    approvedUsed: float
    pendingDays: float
    remaining: float


class UpdateLeaveBalanceRequest(BaseModel):
    annualEntitlement: float = Field(..., ge=0, le=365)


class UpdateProfileRequest(BaseModel):
    name: str | None = None
    password: str | None = Field(default=None, min_length=6)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _password_hash(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256${salt}${digest.hex()}"


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, salt, expected = password_hash.split("$", 2)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    actual = _password_hash(password, salt).split("$", 2)[2]
    return hmac.compare_digest(actual, expected)


def _default_annual_leave_days() -> float:
    try:
        return float(os.getenv("ANNUAL_LEAVE_DAYS", "12"))
    except ValueError:
        return 12.0


def _annual_leave_entitlement(user: dict[str, Any]) -> float:
    try:
        return float(user.get("annualLeaveDays", _default_annual_leave_days()))
    except (TypeError, ValueError):
        return _default_annual_leave_days()


def _public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "email": user["email"],
        "name": user.get("name", user["email"]),
        "role": user.get("role", "employee"),
        "department": user.get("department", ""),
        "isActive": bool(user.get("isActive", True)),
        "annualLeaveDays": _annual_leave_entitlement(user),
        "createdAt": user.get("createdAt"),
    }


def _normalize_role(role: str | None) -> str:
    normalized = (role or "employee").strip().lower()
    if normalized == "user":
        return "employee"
    if normalized in {"admin", "hr", "employee"}:
        return normalized
    return "employee"


def _sync_env_admin_user(users: list[dict[str, Any]]) -> bool:
    """Keep Railway/env admin credentials usable even when /app/data already exists."""
    if "ADMIN_EMAIL" not in os.environ and "ADMIN_PASSWORD" not in os.environ:
        return False

    admin_email = os.getenv("ADMIN_EMAIL", "admin@gmail.com").strip().lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123456")
    admin_name = os.getenv("ADMIN_NAME", "Quan tri vien")
    now = datetime.now().isoformat(timespec="seconds")
    changed = False

    admin = next((user for user in users if user.get("email", "").strip().lower() == admin_email), None)
    if not admin:
        users.append(
            {
                "id": uuid4().hex,
                "email": admin_email,
                "name": admin_name,
                "role": "admin",
                "isActive": True,
                "passwordHash": _password_hash(admin_password),
                "createdAt": now,
            }
        )
        logger.info("AUTH_SYNC_ADMIN_CREATED email=%s", admin_email)
        return True

    if admin.get("role") != "admin":
        admin["role"] = "admin"
        changed = True
    if not admin.get("isActive", True):
        admin["isActive"] = True
        changed = True
    if admin.get("name") != admin_name and "ADMIN_NAME" in os.environ:
        admin["name"] = admin_name
        changed = True
    if admin.get("email") != admin_email:
        admin["email"] = admin_email
        changed = True
    if "ADMIN_PASSWORD" in os.environ and not _verify_password(admin_password, admin.get("passwordHash", "")):
        admin["passwordHash"] = _password_hash(admin_password)
        changed = True

    if changed:
        logger.info("AUTH_SYNC_ADMIN_UPDATED email=%s", admin_email)
    return changed


def _load_users() -> list[dict[str, Any]]:
    USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if USERS_PATH.exists():
        try:
            data = json.loads(USERS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list) and data:
                if _sync_env_admin_user(data):
                    _save_users(data)
                return data
        except json.JSONDecodeError:
            logger.warning("USERS_FILE_INVALID path=%s", USERS_PATH)

    admin_email = os.getenv("ADMIN_EMAIL", "admin@gmail.com").strip().lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123456")
    now = datetime.now().isoformat(timespec="seconds")
    users = [
        {
            "id": uuid4().hex,
            "email": admin_email,
            "name": os.getenv("ADMIN_NAME", "Quản trị viên"),
            "role": "admin",
            "isActive": True,
            "passwordHash": _password_hash(admin_password),
            "createdAt": now,
        },
        {
            "id": uuid4().hex,
            "email": os.getenv("HR_DEMO_EMAIL", "hr.demo@company.local").strip().lower(),
            "name": os.getenv("HR_DEMO_NAME", "HR Demo"),
            "role": "hr",
            "isActive": True,
            "passwordHash": _password_hash(os.getenv("HR_DEMO_PASSWORD", "hr123456")),
            "createdAt": now,
        },
        {
            "id": uuid4().hex,
            "email": os.getenv("USER_DEMO_EMAIL", "user.demo@company.local").strip().lower(),
            "name": os.getenv("USER_DEMO_NAME", "User Demo"),
            "role": "employee",
            "isActive": True,
            "passwordHash": _password_hash(os.getenv("USER_DEMO_PASSWORD", "user123456")),
            "createdAt": now,
        },
    ]
    _save_users(users)
    logger.info("AUTH_BOOTSTRAP_ADMIN email=%s", admin_email)
    return users


def _save_users(users: list[dict[str, Any]]) -> None:
    USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    USERS_PATH.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_notifications() -> list[dict[str, Any]]:
    if not NOTIFICATIONS_PATH.exists():
        return []
    try:
        data = json.loads(NOTIFICATIONS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _save_notifications(notifications: list[dict[str, Any]]) -> None:
    NOTIFICATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    NOTIFICATIONS_PATH.write_text(
        json.dumps(notifications, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _append_notification(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    related_type: str | None = None,
    related_id: str | None = None,
) -> None:
    notifications = _load_notifications()
    notifications.append({
        "id": uuid4().hex,
        "userId": user_id,
        "type": notification_type,
        "title": title,
        "message": message,
        "relatedType": related_type,
        "relatedId": related_id,
        "read": False,
        "createdAt": datetime.now().isoformat(timespec="seconds"),
    })
    _save_notifications(notifications)


def _load_announcements() -> list[dict[str, Any]]:
    if not ANNOUNCEMENTS_PATH.exists():
        return []
    try:
        data = json.loads(ANNOUNCEMENTS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def _save_announcements(items: list[dict[str, Any]]) -> None:
    ANNOUNCEMENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ANNOUNCEMENTS_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def _find_announcement(announcement_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    items = _load_announcements()
    item = next((entry for entry in items if entry.get("id") == announcement_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo nội bộ")
    return items, item


def _announcement_recipients(item: dict[str, Any]) -> list[dict[str, Any]]:
    users = [user for user in _load_users() if user.get("role") == "employee" and user.get("isActive", True)]
    if item.get("audienceType") == "department":
        department = str(item.get("department") or "").strip().casefold()
        users = [user for user in users if str(user.get("department") or "").strip().casefold() == department]
    return users


def _can_view_announcement(user: dict[str, Any], item: dict[str, Any]) -> bool:
    if user.get("role") == "admin":
        return True
    if user.get("role") == "hr":
        return item.get("createdBy") == user.get("id")
    if user.get("role") != "employee" or item.get("status") != "published":
        return False
    if item.get("audienceType") == "all_employees":
        return True
    return str(item.get("department") or "").strip().casefold() == str(user.get("department") or "").strip().casefold()


def _find_announcement_attachment(item: dict[str, Any], attachment_id: str) -> dict[str, Any]:
    attachment = next((entry for entry in item.get("attachments", []) if entry.get("id") == attachment_id), None)
    if not attachment:
        raise HTTPException(status_code=404, detail="Không tìm thấy file đính kèm")
    return attachment


def _extract_pdf_text(path: Path) -> tuple[str, int]:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    parts = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            parts.append(text.strip())
    return "\n\n".join(parts), len(reader.pages)


def _public_announcement(item: dict[str, Any]) -> dict[str, Any]:
    notifications = _load_notifications()
    deliveries = [entry for entry in notifications if entry.get("relatedType") == "announcement" and entry.get("relatedId") == item["id"] and entry.get("type") == "announcement_published"]
    return {**item, "recipientCount": len(deliveries), "readCount": sum(1 for entry in deliveries if entry.get("read"))}


def _create_hr_request_notification(item: dict[str, Any]) -> None:
    status_content = {
        "approved": (
            "Đơn nghỉ đã được duyệt",
            f"Đơn {item.get('leaveType') or 'nghỉ phép'} từ {item.get('startDate')} đến {item.get('endDate')} đã được HR phê duyệt.",
        ),
        "rejected": (
            "Đơn nghỉ đã bị từ chối",
            f"Đơn {item.get('leaveType') or 'nghỉ phép'} từ {item.get('startDate')} đến {item.get('endDate')} đã bị từ chối.",
        ),
        "needs_info": (
            "Đơn nghỉ cần bổ sung thông tin",
            item.get("hrNote") or "HR yêu cầu bạn bổ sung thêm thông tin cho đơn nghỉ.",
        ),
    }
    content = status_content.get(item.get("status"))
    if not content:
        return
    title, message = content
    notifications = _load_notifications()
    notifications.append({
        "id": uuid4().hex,
        "userId": item["employeeId"],
        "type": f"hr_request_{item['status']}",
        "title": title,
        "message": message,
        "relatedType": "hr_request",
        "relatedId": item["id"],
        "read": False,
        "createdAt": datetime.now().isoformat(timespec="seconds"),
    })
    _save_notifications(notifications)


def _append_password_reset_request(email: str, status: str = "pending", password: str | None = None) -> None:
    PASSWORD_RESET_REQUESTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    requests: list[dict[str, Any]] = []
    if PASSWORD_RESET_REQUESTS_PATH.exists():
        try:
            data = json.loads(PASSWORD_RESET_REQUESTS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, list):
                requests = data
        except json.JSONDecodeError:
            logger.warning("PASSWORD_RESET_REQUESTS_INVALID path=%s", PASSWORD_RESET_REQUESTS_PATH)

    request_entry = {
        "id": uuid4().hex,
        "email": email.strip().lower(),
        "status": status,
        "createdAt": datetime.now().isoformat(timespec="seconds"),
    }
    if password:
        request_entry["tempPassword"] = password

    requests.append(request_entry)
    PASSWORD_RESET_REQUESTS_PATH.write_text(json.dumps(requests, ensure_ascii=False, indent=2), encoding="utf-8")


def _send_password_email(email: str, password: str, purpose: str = "reset") -> tuple[bool, str]:
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    if purpose == "register":
        subject = "Thong tin tai khoan moi - HR Helpdesk AI"
        body = f"""Chao ban,

Tai khoan HR Helpdesk AI cua ban da duoc tao thanh cong.

Email dang nhap: {email}
Mat khau cua ban la: {password}

Vui long dang nhap va doi lai mat khau neu can de bao mat tai khoan.

Tran trong,
HR Helpdesk AI Team"""
    else:
        subject = "Dat lai mat khau - HR Helpdesk AI"
        body = f"""Chao ban,

Mat khau cua ban da duoc dat lai thanh cong.

Mat khau moi cua ban la: {password}

Vui long dang nhap va doi lai mat khau ngay lap tuc de bao mat tai khoan.

Tran trong,
HR Helpdesk AI Team"""

    # 1. Log to server console
    logger.info("SENDING_EMAIL_TO: %s | purpose=%s", email, purpose)

    # 2. Save to data/sent_emails.json for easy local testing
    sent_emails_path = DATA_ROOT / "sent_emails.json"
    try:
        sent_emails_path.parent.mkdir(parents=True, exist_ok=True)
        emails = []
        if sent_emails_path.exists():
            try:
                emails = json.loads(sent_emails_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        emails.append({
            "to": email,
            "subject": subject,
            "body": body,
            "password": password,
            "purpose": purpose,
            "sentAt": datetime.now().isoformat(timespec="seconds")
        })
        sent_emails_path.write_text(json.dumps(emails, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error("Failed to write sent_emails.json: %s", e)

    delivery_errors: list[str] = []

    # 3. Prefer Resend HTTP API on hosted platforms where SMTP is blocked.
    resend_api_key = (os.getenv("RESEND_API_KEY") or "").strip()
    resend_sender = (
        (os.getenv("RESEND_SENDER") or "").strip()
        or (os.getenv("EMAIL_SENDER") or "").strip()
        or "HR Helpdesk AI <onboarding@resend.dev>"
    )
    if resend_api_key:
        try:
            import requests as http_requests

            response = http_requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {resend_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": resend_sender,
                    "to": [email],
                    "subject": subject,
                    "text": body,
                },
                timeout=15,
            )
            if 200 <= response.status_code < 300:
                logger.info("Successfully sent password email to %s via Resend. purpose=%s", email, purpose)
                return True, "sent"
            reason = f"Resend trả lỗi {response.status_code}: {response.text[:240]}"
            delivery_errors.append(reason)
            logger.error("%s", reason)
        except Exception as e:
            reason = f"Không gửi được qua Resend ({type(e).__name__}: {e})"
            delivery_errors.append(reason)
            logger.error("%s", reason)

    # 4. Check if SMTP configuration is set as a fallback.
    smtp_host = (os.getenv("SMTP_HOST") or "").strip()
    smtp_port = (os.getenv("SMTP_PORT") or "587").strip()
    smtp_username = (os.getenv("SMTP_USERNAME") or "").strip()
    smtp_password = (os.getenv("SMTP_PASSWORD") or "").replace(" ", "").strip()
    smtp_sender = (os.getenv("SMTP_SENDER") or smtp_username).strip()

    if not smtp_host or not smtp_username or not smtp_password:
        missing = [
            key
            for key, value in {
                "SMTP_HOST": smtp_host,
                "SMTP_USERNAME": smtp_username,
                "SMTP_PASSWORD": smtp_password,
            }.items()
            if not value
        ]
        reason = f"Thiếu cấu hình SMTP trên server: {', '.join(missing)}"
        if delivery_errors:
            reason = "; ".join(delivery_errors + [reason])
        logger.warning("%s. Email sent was logged and saved to data/sent_emails.json.", reason)
        return False, reason

    def _send_with_port(port: int) -> None:
        msg = MIMEMultipart()
        msg["From"] = smtp_sender
        msg["To"] = email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        if port == 465:
            with smtplib.SMTP_SSL(smtp_host, port, timeout=10) as server:
                server.login(smtp_username, smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, port, timeout=10) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.send_message(msg)

    try:
        port = int(smtp_port)
        try:
            _send_with_port(port)
        except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, TimeoutError, OSError):
            if port != 587:
                raise
            logger.warning("SMTP port 587 failed for %s, retrying Gmail SSL port 465", email)
            _send_with_port(465)
        logger.info("Successfully sent password email to %s via SMTP. purpose=%s", email, purpose)
        return True, "sent"
    except smtplib.SMTPAuthenticationError as e:
        reason = "Gmail từ chối đăng nhập SMTP. Kiểm tra SMTP_USERNAME và Gmail App Password"
        if delivery_errors:
            reason = "; ".join(delivery_errors + [reason])
        logger.error("%s for %s: %s", reason, email, e)
        return False, reason
    except smtplib.SMTPRecipientsRefused as e:
        reason = "Gmail từ chối email người nhận. Kiểm tra email tài khoản có tồn tại không"
        if delivery_errors:
            reason = "; ".join(delivery_errors + [reason])
        logger.error("%s for %s: %s", reason, email, e)
        return False, reason
    except (smtplib.SMTPConnectError, smtplib.SMTPServerDisconnected, TimeoutError, OSError) as e:
        reason = f"Không kết nối được SMTP Gmail từ server ({type(e).__name__}: {e}). Thử SMTP_PORT=465 hoặc dùng dịch vụ email API như Resend"
        if delivery_errors:
            reason = "; ".join(delivery_errors + [reason])
        logger.error("%s for %s: %s", reason, email, e)
        return False, reason
    except Exception as e:
        reason = f"Lỗi SMTP không xác định: {type(e).__name__}"
        if delivery_errors:
            reason = "; ".join(delivery_errors + [reason])
        logger.error("Failed to send email to %s via SMTP: %s", email, e)
        return False, reason



def _auto_close_idle_conversations(conversations: list[dict[str, Any]]) -> bool:
    modified = False
    now_dt = datetime.now()
    for conv in conversations:
        if conv.get("status") == "active":
            # Tìm tin nhắn cuối cùng của nhân viên (senderRole == "employee" hoặc senderId == employeeId)
            emp_messages = [
                m for m in conv.get("messages", [])
                if m.get("senderRole") == "employee" or m.get("senderId") == conv.get("employeeId")
            ]

            # Lấy mốc thời gian hoạt động cuối cùng của nhân viên
            if emp_messages:
                last_emp_msg = emp_messages[-1]
                last_active_str = last_emp_msg.get("createdAt")
            else:
                last_active_str = conv.get("acceptedAt") or conv.get("createdAt")

            if last_active_str:
                try:
                    last_active_dt = datetime.fromisoformat(last_active_str)
                    elapsed_seconds = (now_dt - last_active_dt).total_seconds()
                    if elapsed_seconds > 120:  # 2 phút
                         conv["status"] = "closed"
                         conv["updatedAt"] = now_dt.isoformat(timespec="seconds")

                         # Thêm tin nhắn thông báo của hệ thống
                         conv.setdefault("messages", []).append({
                             "id": uuid4().hex,
                             "senderId": "system",
                             "senderName": "Hệ thống",
                             "senderRole": "system",
                             "content": "Cuộc trò chuyện đã tự động kết thúc do nhân viên không gửi tin nhắn trong 2 phút.",
                             "createdAt": now_dt.isoformat(timespec="seconds")
                         })
                         modified = True
                         logger.info("SUPPORT_AUTO_CLOSED id=%s employee=%s due to inactivity", conv["id"], conv["employeeEmail"])
                except Exception as e:
                    logger.error("Error parsing date in auto-close check: %s", e)
    return modified


def _cleanup_old_support_conversations(conversations: list[dict[str, Any]]) -> bool:
    from datetime import timedelta
    modified = False
    now_dt = datetime.now()
    cutoff_dt = now_dt - timedelta(days=10)

    original_len = len(conversations)
    new_conversations = []

    for conv in conversations:
        updated_at_str = conv.get("updatedAt") or conv.get("createdAt")
        if updated_at_str:
            try:
                updated_at_dt = datetime.fromisoformat(updated_at_str)
                if updated_at_dt >= cutoff_dt:
                    new_conversations.append(conv)
            except Exception as e:
                logger.error("Error parsing date in support cleanup: %s", e)
                new_conversations.append(conv)
        else:
            new_conversations.append(conv)

    if len(new_conversations) < original_len:
        conversations.clear()
        conversations.extend(new_conversations)
        modified = True
        logger.info("SUPPORT_CLEANUP_OLD_CONVERSATIONS removed %d conversations older than 10 days", original_len - len(new_conversations))

    return modified


def _load_support_conversations() -> list[dict[str, Any]]:
    SUPPORT_CONVERSATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not SUPPORT_CONVERSATIONS_PATH.exists():
        return []
    try:
        data = json.loads(SUPPORT_CONVERSATIONS_PATH.read_text(encoding="utf-8"))
        conversations = data if isinstance(data, list) else []

        # Tự động quét và đóng các cuộc hội thoại nhân viên không chat sau 2 phút
        modified_close = _auto_close_idle_conversations(conversations)

        # Tự động quét và xóa lịch sử chat quá 10 ngày
        modified_cleanup = _cleanup_old_support_conversations(conversations)

        if modified_close or modified_cleanup:
            _save_support_conversations(conversations)

        return conversations
    except json.JSONDecodeError:
        logger.warning("SUPPORT_CONVERSATIONS_INVALID path=%s", SUPPORT_CONVERSATIONS_PATH)
        return []



def _save_support_conversations(conversations: list[dict[str, Any]]) -> None:
    SUPPORT_CONVERSATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUPPORT_CONVERSATIONS_PATH.write_text(json.dumps(conversations, ensure_ascii=False, indent=2), encoding="utf-8")


def _public_support_conversation(conversation: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": conversation["id"],
        "employeeId": conversation["employeeId"],
        "employeeName": conversation["employeeName"],
        "employeeEmail": conversation["employeeEmail"],
        "hrId": conversation.get("hrId"),
        "hrName": conversation.get("hrName"),
        "status": conversation.get("status", "pending"),
        "subject": conversation.get("subject", ""),
        "createdAt": conversation.get("createdAt", ""),
        "updatedAt": conversation.get("updatedAt", conversation.get("createdAt", "")),
        "acceptedAt": conversation.get("acceptedAt"),
        "messages": conversation.get("messages", []),
    }


def _can_view_support_conversation(user: dict[str, Any], conversation: dict[str, Any]) -> bool:
    role = user.get("role")
    if role == "admin":
        return True
    if role == "hr":
        return conversation.get("status") == "pending" or conversation.get("hrId") == user.get("id")
    return conversation.get("employeeId") == user.get("id")


def _can_send_support_message(user: dict[str, Any], conversation: dict[str, Any]) -> bool:
    if conversation.get("status") != "active":
        return False
    role = user.get("role")
    if role == "admin":
        return conversation.get("status") == "active"
    if role == "hr":
        return conversation.get("status") == "active" and conversation.get("hrId") == user.get("id")
    return conversation.get("employeeId") == user.get("id")


def _find_support_conversation(conversation_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    conversations = _load_support_conversations()
    conversation = next((item for item in conversations if item.get("id") == conversation_id), None)
    if not conversation:
        raise HTTPException(status_code=404, detail="Không tìm thấy phiên hỗ trợ")
    return conversations, conversation


def _load_hr_requests() -> list[dict[str, Any]]:
    HR_REQUESTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not HR_REQUESTS_PATH.exists():
        return []
    try:
        data = json.loads(HR_REQUESTS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        logger.warning("HR_REQUESTS_INVALID path=%s", HR_REQUESTS_PATH)
        return []


def _save_hr_requests(requests: list[dict[str, Any]]) -> None:
    HR_REQUESTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    HR_REQUESTS_PATH.write_text(json.dumps(requests, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_chat_history() -> list[dict[str, Any]]:
    CHAT_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not CHAT_HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(CHAT_HISTORY_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        logger.warning("CHAT_HISTORY_INVALID path=%s", CHAT_HISTORY_PATH)
        return []


def _save_chat_history(items: list[dict[str, Any]]) -> None:
    CHAT_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHAT_HISTORY_PATH.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def _append_chat_history(
    user: dict[str, Any],
    query: str,
    answer: str,
    sources: list[dict[str, Any]],
    trace_id: str | None,
) -> None:
    history = _load_chat_history()
    history.append(
        {
            "id": uuid4().hex,
            "userId": user["id"],
            "userName": user.get("name", user["email"]),
            "userEmail": user["email"],
            "query": query,
            "answer": answer,
            "sources": sources,
            "traceId": trace_id,
            "createdAt": datetime.now().isoformat(timespec="seconds"),
        }
    )
    _save_chat_history(history[-500:])


def _public_hr_request(item: dict[str, Any]) -> dict[str, Any]:
    request_id = item["id"]
    attachments = [
        {
            **attachment,
            "url": f"/api/hr-requests/{request_id}/attachments/{attachment['id']}",
        }
        for attachment in item.get("attachments", [])
    ]
    return {**item, "attachments": attachments}


def _can_view_hr_request(user: dict[str, Any], item: dict[str, Any]) -> bool:
    return user.get("role") in {"hr", "admin"} or item.get("employeeId") == user.get("id")


def _ascii_fold(text: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(char) != "Mn"
    )


def _is_leave_balance_query(query: str) -> bool:
    folded = _ascii_fold(query)
    asks_balance = any(
        phrase in folded
        for phrase in (
            "con nghi phep",
            "ngay phep con",
            "phep con",
            "con bao nhieu ngay phep",
            "con may ngay phep",
            "so ngay phep con lai",
            "leave balance",
            "remaining leave",
        )
    )
    asks_annual_leave = any(
        phrase in folded
        for phrase in ("nghi phep", "phep nam", "ngay phep", "annual leave")
    )
    return asks_balance and asks_annual_leave


def _is_ambiguous_context_query(query: str) -> bool:
    return _shared_needs_more_information(query)


def _clarification_answer(query: str) -> str:
    return _shared_clarification_answer(query)


def _rewrite_chat_query(query: str, history: list[ChatTurn], api_key_override: str | None) -> str:
    """Turn a contextual follow-up into a standalone retrieval query."""
    clean_query = query.strip()
    relevant_history = [turn for turn in history[-8:] if turn.content.strip()]
    if not relevant_history:
        return clean_query

    api_key = get_llm_api_key(override=api_key_override)
    if api_key:
        transcript = "\n".join(f"{turn.role}: {turn.content.strip()}" for turn in relevant_history)
        try:
            rewritten = generate_text(
                system_prompt=(
                    "Viết lại câu hỏi HR cuối thành một câu hỏi độc lập để tìm kiếm tài liệu. "
                    "Giữ nguyên dữ kiện, không tự thêm chính sách hay kết luận. Chỉ trả về câu hỏi đã viết lại."
                ),
                user_message=f"Lịch sử:\n{transcript}\n\nCâu mới:\n{clean_query}",
                temperature=0,
                top_p=1,
                api_key_override=api_key_override,
            ).strip()
            if rewritten:
                return rewritten[:4000]
        except Exception as exc:
            logger.warning("QUERY_REWRITE_FAILED error=%s", exc)

    previous_user = next(
        (turn.content.strip() for turn in reversed(relevant_history) if turn.role == "user"),
        "",
    )
    return f"{previous_user}\nThông tin bổ sung: {clean_query}".strip() if previous_user else clean_query


def _with_conversational_follow_up(answer: str, query: str) -> str:
    """Keep policy answers conversational without duplicating an existing question."""
    clean_answer = answer.strip()
    if not clean_answer or "?" in clean_answer[-240:]:
        return clean_answer

    folded = _ascii_fold(query)
    if any(term in folded for term in ("nghi om", "om dau", "bi om", "dang om", "bi benh", "khong khoe")):
        follow_up = "Bạn có muốn mình kiểm tra trường hợp nghỉ ốm cụ thể của bạn cần chuẩn bị giấy tờ gì không?"
    elif any(term in folded for term in ("nghi phep", "xin nghi", "phep nam")):
        follow_up = "Bạn có muốn mình hướng dẫn tiếp thủ tục hoặc hỗ trợ tạo đơn nghỉ không?"
    elif any(term in folded for term in ("bao hiem", "bhxh", "bhyt", "bhtn")):
        follow_up = "Bạn đang cần mình hỗ trợ thêm về hồ sơ, quyền lợi hay thủ tục bảo hiểm?"
    elif any(term in folded for term in ("cham cong", "di muon", "lam them", "overtime", " ot ")):
        follow_up = "Bạn có muốn mình hướng dẫn xử lý đúng tình huống chấm công hoặc OT của bạn không?"
    else:
        follow_up = "Bạn còn cần mình hỗ trợ thêm nội dung nào về trường hợp này không?"

    return f"{clean_answer}\n\n{follow_up}"


def _is_annual_leave_request(item: dict[str, Any]) -> bool:
    leave_type = _ascii_fold(str(item.get("leaveType", "")))
    return "nghi phep nam" in leave_type or "phep nam" in leave_type


def _request_year(item: dict[str, Any]) -> int | None:
    raw_date = str(item.get("startDate") or item.get("createdAt") or "")
    try:
        return datetime.fromisoformat(raw_date[:10]).year
    except ValueError:
        return None


def _leave_balance_stats(
    user: dict[str, Any],
    year: int | None = None,
    requests: list[dict[str, Any]] | None = None,
) -> dict[str, float | int]:
    target_year = year or datetime.now().year
    approved_used = 0.0
    pending_days = 0.0

    for item in requests if requests is not None else _load_hr_requests():
        if item.get("employeeId") != user.get("id"):
            continue
        if item.get("type") != "leave" or not _is_annual_leave_request(item):
            continue
        if _request_year(item) != target_year:
            continue

        days = float(item.get("totalDays") or 0)
        if item.get("status") == "approved":
            approved_used += days
        elif item.get("status") in {"pending", "needs_info"}:
            pending_days += days

    entitlement = _annual_leave_entitlement(user)
    return {
        "year": target_year,
        "annualEntitlement": entitlement,
        "approvedUsed": approved_used,
        "pendingDays": pending_days,
        "remaining": max(entitlement - approved_used, 0.0),
    }


def _public_leave_balance(
    user: dict[str, Any],
    year: int | None = None,
    requests: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    stats = _leave_balance_stats(user, year, requests)
    return {
        "userId": user["id"],
        "name": user.get("name", user["email"]),
        "email": user["email"],
        "role": user.get("role", "employee"),
        **stats,
    }


def _leave_balance_answer(user: dict[str, Any], query: str) -> str:
    entitlement = _annual_leave_entitlement(user)
    current_year = datetime.now().year
    approved_used = 0.0
    pending_days = 0.0

    for item in _load_hr_requests():
        if item.get("employeeId") != user.get("id"):
            continue
        if item.get("type") != "leave" or not _is_annual_leave_request(item):
            continue
        if _request_year(item) != current_year:
            continue

        days = float(item.get("totalDays") or 0)
        if item.get("status") == "approved":
            approved_used += days
        elif item.get("status") in {"pending", "needs_info"}:
            pending_days += days

    remaining = max(entitlement - approved_used, 0.0)

    def fmt(value: float) -> str:
        return str(int(value)) if value.is_integer() else f"{value:.1f}".rstrip("0").rstrip(".")

    lines = [
        f"Câu hỏi HR: {query}",
        "",
        f"Theo dữ liệu đơn từ HR của bạn trong năm {current_year}:",
        f"- Quota phép năm cấu hình: {fmt(entitlement)} ngày.",
        f"- Số ngày phép năm đã được HR duyệt: {fmt(approved_used)} ngày.",
        f"- Số ngày phép năm còn lại tạm tính: {fmt(remaining)} ngày.",
    ]
    if pending_days:
        lines.append(f"- Có {fmt(pending_days)} ngày phép năm đang chờ HR xử lý/chờ bổ sung, chưa trừ vào số đã duyệt.")
    lines.append("")
    lines.append("Lưu ý: đây là số liệu tạm tính từ các đơn nghỉ phép năm đã được duyệt trong hệ thống. Nếu HR có điều chỉnh thủ công hoặc dữ liệu phép tồn từ năm trước, hãy kiểm tra thêm trên HR Portal/phòng HR.")
    return "\n".join(lines)


def _find_hr_request(request_id: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    requests = _load_hr_requests()
    item = next((entry for entry in requests if entry.get("id") == request_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Không tìm thấy đơn nhân sự")
    return requests, item


async def _save_hr_request_attachments(request_id: str, files: list[UploadFile] | None) -> list[dict[str, Any]]:
    if not files:
        return []

    allowed_types = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
    request_dir = HR_REQUEST_ATTACHMENTS_DIR / request_id
    request_dir.mkdir(parents=True, exist_ok=True)
    attachments: list[dict[str, Any]] = []

    for file in files:
        if not file or not file.filename:
            continue
        content_type = (file.content_type or "").lower()
        if content_type not in allowed_types:
            raise HTTPException(status_code=400, detail="Chỉ hỗ trợ ảnh PNG, JPG, JPEG hoặc WEBP")

        content = await file.read()
        attachment_id = uuid4().hex
        safe_name = _safe_filename(file.filename)
        stored_name = f"{attachment_id}_{safe_name}"
        stored_path = request_dir / stored_name
        stored_path.write_bytes(content)
        attachments.append(
            {
                "id": attachment_id,
                "fileName": safe_name,
                "contentType": content_type,
                "size": len(content),
                "path": str(stored_path.relative_to(PROJECT_ROOT)),
            }
        )
    return attachments


def _find_user_by_email(email: str) -> dict[str, Any] | None:
    normalized = email.strip().lower()
    return next((user for user in _load_users() if user.get("email", "").lower() == normalized), None)


def _find_user_by_id(user_id: str) -> dict[str, Any] | None:
    return next((user for user in _load_users() if user.get("id") == user_id), None)


def _create_token(user: dict[str, Any]) -> str:
    issued_at = int(time())
    header = {
        "alg": "HS256",
        "typ": "JWT",
    }
    payload = {
        "sub": user["id"],
        "email": user["email"],
        "role": user.get("role", "employee"),
        "iat": issued_at,
        "exp": issued_at + TOKEN_TTL_SECONDS,
    }
    encoded_header = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}"
    signature = hmac.new(AUTH_SECRET.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url_encode(signature)}"


def _decode_token(token: str) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, signature = token.split(".", 2)
        header = json.loads(_b64url_decode(encoded_header).decode("utf-8"))
        payload = json.loads(_b64url_decode(encoded_payload).decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc

    if header.get("alg") != "HS256" or header.get("typ") != "JWT":
        raise HTTPException(status_code=401, detail="Invalid token header")

    signing_input = f"{encoded_header}.{encoded_payload}"
    expected = _b64url_encode(
        hmac.new(AUTH_SECRET.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
    )
    if not hmac.compare_digest(signature, expected):
        raise HTTPException(status_code=401, detail="Invalid token signature")

    if int(payload.get("exp", 0)) < int(time()):
        raise HTTPException(status_code=401, detail="Token expired")
    if not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid token subject")
    return payload


def _current_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
    token: str | None = Query(default=None),
) -> dict[str, Any]:
    actual_token = None
    if authorization and authorization.startswith("Bearer "):
        actual_token = authorization.removeprefix("Bearer ").strip()
    elif token:
        actual_token = token.strip()

    if not actual_token:
        raise HTTPException(status_code=401, detail="Missing bearer token")
    payload = _decode_token(actual_token)
    user = _find_user_by_id(payload.get("sub", ""))
    if not user or not user.get("isActive", True):
        raise HTTPException(status_code=401, detail="User is inactive or missing")
    return user


def _admin_user(user: dict[str, Any] = Depends(_current_user)) -> dict[str, Any]:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


def _hr_or_admin_user(user: dict[str, Any] = Depends(_current_user)) -> dict[str, Any]:
    if user.get("role") not in {"hr", "admin"}:
        raise HTTPException(status_code=403, detail="HR or admin role required")
    return user


def _with_ids(results: list[dict]) -> list[dict]:
    return [{**item, "id": index} for index, item in enumerate(results, start=1)]


def _new_trace_id() -> str:
    return f"ai-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid4().hex[:8]}"


def _log_step(logs: list[str], message: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    logs.append(f"{timestamp} | {message}")


def _safe_filename(filename: str) -> str:
    return Path(filename).name.replace("\\", "_").replace("/", "_")


def _validate_upload_file(file: UploadFile, filename: str) -> None:
    suffix = Path(filename).suffix.lower()
    content_type = (file.content_type or "").lower()

    if suffix not in ALLOWED_UPLOAD_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_UPLOAD_EXTENSIONS))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{suffix or '(none)'}'. Allowed: {allowed}",
        )

    if content_type and content_type not in ALLOWED_UPLOAD_CONTENT_TYPES:
        allowed = ", ".join(sorted(ALLOWED_UPLOAD_CONTENT_TYPES))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported content type '{content_type}'. Allowed: {allowed}",
        )


def _bad_extracted_text_count(text: str) -> int:
    return sum(text.count(char) for char in BAD_EXTRACTED_TEXT_CHARS)


def _has_bad_text_layer(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    bad_count = _bad_extracted_text_count(stripped)
    return bad_count >= 5 and (bad_count / len(stripped)) >= BAD_TEXT_RATIO_THRESHOLD


def _text_extraction_score(text: str) -> float:
    stripped = text.strip()
    if not stripped:
        return 0.0
    bad_count = _bad_extracted_text_count(stripped)
    return len(stripped) - (bad_count * 100)


def _extract_pdf_text(content: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("Missing pypdf. Run: python -m pip install pypdf") from exc

    reader = PdfReader(BytesIO(content))
    pages = []
    for index, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"## Slide/Page {index}\n\n{text.strip()}")
    return "\n\n".join(pages).strip()


def _extract_pdf_text_pdfplumber(content: bytes) -> str:
    try:
        import pdfplumber
    except ImportError:
        return ""

    pages = []
    with pdfplumber.open(BytesIO(content)) as pdf:
        for index, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"## Slide/Page {index}\n\n{text.strip()}")
    return "\n\n".join(pages).strip()


def _natural_slide_key(name: str) -> int:
    match = re.search(r"slide(\d+)\.xml$", name)
    return int(match.group(1)) if match else 0


def _extract_pptx_text_native(content: bytes) -> str:
    """Extract text from PPTX slide XML without external conversion tools."""
    slides: list[str] = []
    with zipfile.ZipFile(BytesIO(content)) as archive:
        slide_names = sorted(
            (name for name in archive.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", name)),
            key=_natural_slide_key,
        )
        for index, name in enumerate(slide_names, start=1):
            root = ET.fromstring(archive.read(name))
            texts = [
                (node.text or "").strip()
                for node in root.iter()
                if node.tag.endswith("}t") and (node.text or "").strip()
            ]
            if texts:
                slides.append(f"## Slide {index}\n\n" + "\n".join(texts))
    return "\n\n".join(slides).strip()


def _ocr_pdf_with_llm_vision(filename: str, content: bytes) -> str:
    """OCR image-only PDF slides through the configured LLM provider when enabled."""
    if not ocr_enabled():
        return ""

    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        logger.warning("LLM_OCR_UNAVAILABLE filename=%r error=%s", filename, exc)
        return ""

    max_pages = max(1, int(os.getenv("OCR_MAX_PAGES", "40")))
    provider = get_ocr_provider()
    document = fitz.open(stream=content, filetype="pdf")
    parts: list[str] = []

    for index, page in enumerate(document, start=1):
        if index > max_pages:
            parts.append(f"## Slide/Page {index}\n\n[OCR skipped: reached OCR_MAX_PAGES={max_pages}]")
            break

        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        text = ocr_image_with_provider(
            image_bytes=pixmap.tobytes("png"),
            mime_type="image/png",
            prompt=(
                "Extract all visible text from this lecture slide. "
                "Keep Vietnamese accents, English terms, headings, bullet order, numbers, tables if visible. "
                "Return only extracted text. If no text is visible, return an empty string."
            ),
            temperature=0,
        ).strip()
        if text:
            parts.append(f"## Slide/Page {index}\n\n{text}")

    document.close()
    if parts:
        return "\n\n".join(parts).strip()
    logger.warning("LLM_OCR_EMPTY provider=%s filename=%r", provider, filename)
    return ""


def _extract_with_markitdown(filename: str, content: bytes) -> str:
    try:
        from markitdown import MarkItDown
    except ImportError as exc:
        raise RuntimeError("Missing markitdown. Run: python -m pip install markitdown[pdf]") from exc

    temp_path = UPLOAD_LANDING_DIR / f"__extract_{uuid4().hex}_{Path(filename).name}"
    temp_path.write_bytes(content)
    try:
        result = MarkItDown().convert(str(temp_path))
        return (getattr(result, "text_content", "") or "").strip()
    finally:
        try:
            temp_path.unlink()
        except OSError:
            pass


def _extract_text_from_upload(filename: str, content: bytes) -> str:
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        candidates: list[tuple[str, str]] = []
        try:
            candidates.append(("pypdf", _extract_pdf_text(content)))
        except Exception as exc:  # noqa: BLE001
            logger.warning("PYPDF_EXTRACT_FAILED filename=%r error=%s", filename, exc)
        try:
            candidates.append(("pdfplumber", _extract_pdf_text_pdfplumber(content)))
        except Exception as exc:  # noqa: BLE001
            logger.warning("PDFPLUMBER_EXTRACT_FAILED filename=%r error=%s", filename, exc)
        try:
            candidates.append(("markitdown", _extract_with_markitdown(filename, content)))
        except Exception as exc:  # noqa: BLE001
            logger.warning("MARKITDOWN_PDF_EXTRACT_FAILED filename=%r error=%s", filename, exc)

        valid_candidates = [(name, text) for name, text in candidates if text.strip()]
        best_name = ""
        best_text = ""
        if valid_candidates:
            best_name, best_text = max(valid_candidates, key=lambda item: _text_extraction_score(item[1]))
            if not _has_bad_text_layer(best_text):
                if any(_has_bad_text_layer(text) for _, text in valid_candidates):
                    logger.info("PDF_EXTRACT_SELECTED filename=%r extractor=%s after rejecting noisy text layer", filename, best_name)
                return best_text

            logger.warning(
                "PDF_EXTRACT_NOISY_TEXT filename=%r extractor=%s bad_chars=%s chars=%s",
                filename,
                best_name,
                _bad_extracted_text_count(best_text),
                len(best_text),
            )

        try:
            text = _ocr_pdf_with_llm_vision(filename, content)
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM_OCR_FAILED filename=%r error=%s", filename, exc)
            text = ""
        if text:
            return text
        if best_text:
            return best_text
        return (
            f"Uploaded PDF slide document: {filename}\n\n"
            "No selectable text was extracted. This PDF may be image-only/scanned slides. "
            "Export the slides with selectable text, upload the original PPTX, or enable OCR_ENABLED=1."
        )

    if suffix == ".pptx":
        try:
            text = _extract_pptx_text_native(content)
        except Exception as exc:  # noqa: BLE001
            logger.warning("PPTX_NATIVE_EXTRACT_FAILED filename=%r error=%s", filename, exc)
            text = ""
        if text:
            return text

    if suffix in {".ppt", ".pptx", ".doc", ".docx"}:
        try:
            text = _extract_with_markitdown(filename, content)
        except Exception as exc:  # noqa: BLE001
            logger.warning("MARKITDOWN_EXTRACT_FAILED filename=%r error=%s", filename, exc)
            text = ""
        if text:
            return text
        return (
            f"Uploaded binary document: {filename}\n\n"
            "No text was extracted. If this is a slide deck made from images, export text or run OCR first."
        )

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("utf-8", errors="ignore")

    if text.strip():
        return text.strip()
    return (
        f"Uploaded binary document: {filename}\n\n"
        "Text extraction fallback: this file was saved, but plain text could not be "
        "extracted without an external document parser."
    )


def _golden_dataset_count() -> int:
    if not GOLDEN_DATASET_PATH.exists():
        return 0
    try:
        data = json.loads(GOLDEN_DATASET_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 0
    return len(data) if isinstance(data, list) else 0


def _index_uploaded_markdown(markdown_path: Path) -> int:
    """Add one uploaded markdown file to BM25/PageIndex cache; optionally add Chroma."""
    from src import task8_pageindex_vectorless
    from src.task4_chunking_indexing import (
        CHUNKS_JSON,
        chunk_documents,
        embed_chunks,
        get_chroma_collection,
        markdown_document_metadata,
    )
    from src.task6_lexical_search import _load_corpus

    content = markdown_path.read_text(encoding="utf-8")
    document = {
        "content": content,
        "metadata": markdown_document_metadata(markdown_path, content),
    }
    chunks = chunk_documents([document])
    if not chunks:
        return 0

    vector_chunks = embed_chunks([dict(chunk) for chunk in chunks])
    try:
        collection = get_chroma_collection(create=False)
    except Exception:
        collection = get_chroma_collection(create=True)

    try:
        collection.delete(where={"source": markdown_path.name})
    except Exception:  # noqa: BLE001
        pass

    base_id = f"upload_{markdown_path.stem}"
    collection.add(
        ids=[f"{base_id}_{idx}" for idx in range(len(vector_chunks))],
        documents=[chunk["content"] for chunk in vector_chunks],
        metadatas=[chunk["metadata"] for chunk in vector_chunks],
        embeddings=[chunk["embedding"] for chunk in vector_chunks],
    )

    existing = []
    if CHUNKS_JSON.exists():
        try:
            existing = json.loads(CHUNKS_JSON.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = []

    existing = [
        item for item in existing
        if (item.get("metadata") or {}).get("source") != markdown_path.name
    ]
    existing.extend(
        {"content": chunk["content"], "metadata": chunk["metadata"]}
        for chunk in chunks
    )
    CHUNKS_JSON.parent.mkdir(parents=True, exist_ok=True)
    CHUNKS_JSON.write_text(json.dumps(existing, ensure_ascii=False), encoding="utf-8")

    _load_corpus.cache_clear()
    task8_pageindex_vectorless._SECTIONS_CACHE = None
    return len(chunks)


def _search_mode_results(request: ChatRequest) -> list[dict]:
    mode = request.searchMode.strip().lower()
    if mode.startswith("lexical"):
        results = lexical_search(request.query, top_k=request.topK)
        for item in results:
            item["source"] = "lexical"
        return results
    if mode.startswith("semantic"):
        results = semantic_search(request.query, top_k=request.topK)
        for item in results:
            item["source"] = "semantic"
        return results
    return retrieve(request.query, top_k=request.topK, score_threshold=request.threshold)


app = FastAPI(
    title="HR Helpdesk AI API",
    description="Backend API for HR policy retrieval, procedure guidance, user auth, and citation generation.",
    version="1.0.0",
)


@app.get("/api/integrations/status", tags=["System"])
def integration_status(_: dict[str, Any] = Depends(_admin_user)) -> dict[str, Any]:
    return {
        "llm": {"configured": bool(get_llm_api_key()), "provider": os.getenv("LLM_PROVIDER", "auto")},
        "hrm": {"configured": HRMConnector().configured},
        "sharepoint": {"configured": SharePointConnector().configured},
        "ocr": {"enabled": ocr_enabled(), "provider": get_ocr_provider()},
    }

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["System"], response_model=None)
def root():
    index_path = FRONTEND_DIST / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {
        "message": "HR Helpdesk AI API",
        "swagger_ui": "/docs",
        "openapi_json": "/openapi.json",
    }


@app.get("/health", tags=["System"])
def health() -> dict[str, str]:
    return {"status": "ok", "build": "admin-sync-v2"}


@app.get("/logo.svg", include_in_schema=False, response_model=None)
def favicon_logo():
    logo_path = FRONTEND_DIST / "logo.svg"
    if logo_path.exists():
        return FileResponse(logo_path, media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Logo not found")


@app.post("/api/auth/login", response_model=AuthResponse, tags=["Auth"])
def login(request: LoginRequest) -> AuthResponse:
    email = request.email.strip().lower()
    logger.info("LOGIN_ATTEMPT email=%s", email)
    user = _find_user_by_email(request.email)
    if not user:
        logger.warning("LOGIN_FAILED_USER_NOT_FOUND email=%s", email)
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")
    if not _verify_password(request.password, user.get("passwordHash", "")):
        logger.warning("LOGIN_FAILED_WRONG_PASSWORD email=%s", email)
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")
    if not user.get("isActive", True):
        logger.warning("LOGIN_FAILED_USER_LOCKED email=%s", email)
        raise HTTPException(status_code=403, detail="Tài khoản đã bị khóa")
    logger.info("LOGIN_SUCCESS email=%s role=%s", email, user.get("role"))
    return AuthResponse(token=_create_token(user), user=UserPublic(**_public_user(user)))


@app.post("/api/auth/register", response_model=AuthResponse, tags=["Auth"])
def register(request: RegisterRequest) -> AuthResponse:
    if os.getenv("ALLOW_PUBLIC_REGISTRATION", "0") != "1":
        raise HTTPException(status_code=403, detail="Đăng ký công khai đang tắt")

    email = request.email.strip().lower()
    users = _load_users()
    if any(user.get("email", "").lower() == email for user in users):
        raise HTTPException(status_code=409, detail="Email đã tồn tại")

    user = {
        "id": uuid4().hex,
        "email": email,
        "name": request.name.strip(),
        "role": "employee",
        "isActive": True,
        "passwordHash": _password_hash(request.password),
        "createdAt": datetime.now().isoformat(timespec="seconds"),
    }
    users.append(user)
    _save_users(users)
    email_sent, email_reason = _send_password_email(email, request.password, purpose="register")
    if not email_sent:
        logger.warning("REGISTER_EMAIL_DELIVERY_FAILED email=%s reason=%s", email, email_reason)
    logger.info("AUTH_REGISTER_USER email=%s role=employee", email)
    return AuthResponse(
        token=_create_token(user),
        user=UserPublic(**_public_user(user)),
        message="Tài khoản đã được đăng ký thành công. Vui lòng đăng nhập.",
    )


@app.post("/api/auth/forgot-password", response_model=MessageResponse, tags=["Auth"])
def forgot_password(request: ForgotPasswordRequest) -> MessageResponse:
    email = request.email.strip().lower()
    users = _load_users()
    user = next((u for u in users if u.get("email", "").lower() == email), None)
    if not user:
        raise HTTPException(status_code=404, detail="Email không tồn tại trong hệ thống")

    import string
    chars = string.ascii_lowercase + string.digits
    new_password = "".join(secrets.choice(chars) for _ in range(8))

    user["passwordHash"] = _password_hash(new_password)
    _save_users(users)

    # Gửi email qua Resend/SMTP (nếu có cấu hình) hoặc ghi file log local fallback
    email_sent, email_reason = _send_password_email(email, new_password, purpose="reset")

    # Ghi nhận yêu cầu đã xử lý xong kèm theo thông tin mật khẩu tạm thời
    _append_password_reset_request(email, status="completed", password=new_password)

    msg_suffix = ""
    if not email_sent:
        msg_suffix = f" (Lưu ý: Chưa gửi được email: {email_reason}. Mật khẩu mới được lưu tại data/sent_emails.json và in ra log để kiểm tra.)"

    logger.info("AUTH_PASSWORD_RESET_SUCCESS email=%s", email)
    return MessageResponse(
        status="success",
        message=f"Mật khẩu mới đã được tạo và gửi đến email của bạn.{msg_suffix}",
    )



@app.get("/api/auth/me", response_model=UserPublic, tags=["Auth"])
def me(user: dict[str, Any] = Depends(_current_user)) -> UserPublic:
    return UserPublic(**_public_user(user))


@app.patch("/api/auth/profile", response_model=UserPublic, tags=["Auth"])
def update_profile(
    request: UpdateProfileRequest,
    user: dict[str, Any] = Depends(_current_user),
) -> UserPublic:
    users = _load_users()
    user_item = next((item for item in users if item.get("id") == user["id"]), None)
    if not user_item:
        raise HTTPException(status_code=404, detail="Không tìm thấy user")

    if request.name is not None:
        user_item["name"] = request.name.strip()
    if request.password:
        user_item["passwordHash"] = _password_hash(request.password)

    _save_users(users)
    return UserPublic(**_public_user(user_item))


@app.get("/api/users", response_model=list[UserPublic], tags=["Users"])
def list_users(_: dict[str, Any] = Depends(_admin_user)) -> list[UserPublic]:
    return [UserPublic(**_public_user(user)) for user in _load_users()]


@app.post("/api/users", response_model=UserPublic, tags=["Users"])
def create_user(request: CreateUserRequest, _: dict[str, Any] = Depends(_admin_user)) -> UserPublic:
    raw_role = request.role.strip().lower()
    if raw_role not in {"admin", "hr", "employee", "user"}:
        raise HTTPException(status_code=400, detail="Role không hợp lệ")
    role = _normalize_role(request.role)
    email = request.email.strip().lower()
    users = _load_users()
    if any(user.get("email", "").lower() == email for user in users):
        raise HTTPException(status_code=409, detail="Email đã tồn tại")
    user = {
        "id": uuid4().hex,
        "email": email,
        "name": request.name.strip(),
        "role": role,
        "department": request.department.strip(),
        "isActive": True,
        "passwordHash": _password_hash(request.password),
        "createdAt": datetime.now().isoformat(timespec="seconds"),
    }
    if request.annualLeaveDays is not None:
        user["annualLeaveDays"] = request.annualLeaveDays
    users.append(user)
    _save_users(users)
    return UserPublic(**_public_user(user))


@app.patch("/api/users/{user_id}", response_model=UserPublic, tags=["Users"])
def update_user(
    user_id: str,
    request: UpdateUserRequest,
    admin: dict[str, Any] = Depends(_admin_user),
) -> UserPublic:
    users = _load_users()
    user = next((item for item in users if item.get("id") == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="Không tìm thấy user")
    if request.email is not None:
        new_email = request.email.strip().lower()
        if not new_email:
            raise HTTPException(status_code=400, detail="Email không được để trống")
        if any(item.get("email", "").lower() == new_email and item.get("id") != user_id for item in users):
            raise HTTPException(status_code=409, detail="Email đã tồn tại ở tài khoản khác")
        user["email"] = new_email
    if request.name is not None:
        user["name"] = request.name.strip()
    if request.role is not None:
        raw_role = request.role.strip().lower()
        if raw_role not in {"admin", "hr", "employee", "user"}:
            raise HTTPException(status_code=400, detail="Role không hợp lệ")
        role = _normalize_role(request.role)
        user["role"] = role
    if request.department is not None:
        user["department"] = request.department.strip()
    if request.password:
        user["passwordHash"] = _password_hash(request.password)
    if request.isActive is not None:
        if user["id"] == admin["id"] and request.isActive is False:
            raise HTTPException(status_code=400, detail="Không thể khóa chính tài khoản admin đang dùng")
        user["isActive"] = request.isActive
    if request.annualLeaveDays is not None:
        user["annualLeaveDays"] = request.annualLeaveDays
    _save_users(users)
    return UserPublic(**_public_user(user))


@app.delete("/api/users/{user_id}", tags=["Users"])
def delete_user(user_id: str, admin: dict[str, Any] = Depends(_admin_user)) -> dict[str, str]:
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Không thể xóa chính tài khoản admin đang dùng")
    users = _load_users()
    next_users = [user for user in users if user.get("id") != user_id]
    if len(next_users) == len(users):
        raise HTTPException(status_code=404, detail="Không tìm thấy user")
    _save_users(next_users)
    return {"status": "deleted"}


@app.get("/api/leave-balances", response_model=list[LeaveBalancePublic], tags=["Leave Balances"])
def list_leave_balances(
    year: int | None = Query(default=None, ge=2000, le=2100),
    _: dict[str, Any] = Depends(_hr_or_admin_user),
) -> list[LeaveBalancePublic]:
    requests = _load_hr_requests()
    employees = [
        user
        for user in _load_users()
        if user.get("role", "employee") == "employee" and bool(user.get("isActive", True))
    ]
    employees.sort(key=lambda user: user.get("name", user.get("email", "")).lower())
    return [
        LeaveBalancePublic(**_public_leave_balance(user, year, requests))
        for user in employees
    ]


@app.patch("/api/leave-balances/{user_id}", response_model=LeaveBalancePublic, tags=["Leave Balances"])
def update_leave_balance(
    user_id: str,
    request: UpdateLeaveBalanceRequest,
    year: int | None = Query(default=None, ge=2000, le=2100),
    _: dict[str, Any] = Depends(_hr_or_admin_user),
) -> LeaveBalancePublic:
    users = _load_users()
    user = next((item for item in users if item.get("id") == user_id), None)
    if not user:
        raise HTTPException(status_code=404, detail="Khong tim thay user")
    if user.get("role", "employee") != "employee":
        raise HTTPException(status_code=400, detail="Chi quan ly phep nam cho nhan vien")

    user["annualLeaveDays"] = request.annualEntitlement
    _save_users(users)
    return LeaveBalancePublic(**_public_leave_balance(user, year))


@app.get("/api/support/conversations", response_model=list[SupportConversationPublic], tags=["Support"])
def list_support_conversations(user: dict[str, Any] = Depends(_current_user)) -> list[SupportConversationPublic]:
    conversations = [
        _public_support_conversation(conversation)
        for conversation in _load_support_conversations()
        if _can_view_support_conversation(user, conversation)
    ]
    conversations.sort(key=lambda item: item["updatedAt"], reverse=True)
    return [SupportConversationPublic(**conversation) for conversation in conversations]


@app.post("/api/support/conversations", response_model=SupportConversationPublic, tags=["Support"])
def create_support_conversation(
    request: SupportCreateRequest,
    user: dict[str, Any] = Depends(_current_user),
) -> SupportConversationPublic:
    if user.get("role") != "employee":
        raise HTTPException(status_code=403, detail="Chỉ User/Nhân viên mới tạo yêu cầu hỗ trợ trực tiếp")

    now = datetime.now().isoformat(timespec="seconds")
    message = {
        "id": uuid4().hex,
        "senderId": user["id"],
        "senderName": user.get("name", user["email"]),
        "senderRole": user.get("role", "employee"),
        "content": request.message.strip(),
        "createdAt": now,
    }
    conversation = {
        "id": uuid4().hex,
        "employeeId": user["id"],
        "employeeName": user.get("name", user["email"]),
        "employeeEmail": user["email"],
        "hrId": None,
        "hrName": None,
        "status": "pending",
        "subject": request.subject.strip(),
        "createdAt": now,
        "updatedAt": now,
        "acceptedAt": None,
        "messages": [message],
    }
    conversations = _load_support_conversations()
    conversations.append(conversation)
    _save_support_conversations(conversations)
    logger.info("SUPPORT_CREATED id=%s employee=%s", conversation["id"], user["email"])
    return SupportConversationPublic(**_public_support_conversation(conversation))


@app.post("/api/support/conversations/{conversation_id}/accept", response_model=SupportConversationPublic, tags=["Support"])
def accept_support_conversation(
    conversation_id: str,
    user: dict[str, Any] = Depends(_hr_or_admin_user),
) -> SupportConversationPublic:
    conversations, conversation = _find_support_conversation(conversation_id)
    if conversation.get("status") == "active" and conversation.get("hrId") != user.get("id") and user.get("role") != "admin":
        raise HTTPException(status_code=409, detail="Phiên hỗ trợ đã được HR khác nhận")
    if conversation.get("status") not in {"pending", "active"}:
        raise HTTPException(status_code=400, detail="Phiên hỗ trợ không còn mở")

    now = datetime.now().isoformat(timespec="seconds")
    conversation["status"] = "active"
    conversation["hrId"] = user["id"]
    conversation["hrName"] = user.get("name", user["email"])
    conversation["acceptedAt"] = conversation.get("acceptedAt") or now
    conversation["updatedAt"] = now
    _save_support_conversations(conversations)
    logger.info("SUPPORT_ACCEPTED id=%s hr=%s", conversation["id"], user["email"])
    return SupportConversationPublic(**_public_support_conversation(conversation))


@app.get("/api/support/conversations/{conversation_id}", response_model=SupportConversationPublic, tags=["Support"])
def get_support_conversation(
    conversation_id: str,
    user: dict[str, Any] = Depends(_current_user),
) -> SupportConversationPublic:
    _, conversation = _find_support_conversation(conversation_id)
    if not _can_view_support_conversation(user, conversation):
        raise HTTPException(status_code=403, detail="Không có quyền xem phiên hỗ trợ này")
    return SupportConversationPublic(**_public_support_conversation(conversation))


@app.post("/api/support/conversations/{conversation_id}/messages", response_model=SupportConversationPublic, tags=["Support"])
def send_support_message(
    conversation_id: str,
    request: SupportMessageRequest,
    user: dict[str, Any] = Depends(_current_user),
) -> SupportConversationPublic:
    conversations, conversation = _find_support_conversation(conversation_id)
    if not _can_view_support_conversation(user, conversation) or not _can_send_support_message(user, conversation):
        raise HTTPException(status_code=403, detail="Không có quyền gửi tin nhắn trong phiên này")

    now = datetime.now().isoformat(timespec="seconds")
    conversation.setdefault("messages", []).append(
        {
            "id": uuid4().hex,
            "senderId": user["id"],
            "senderName": user.get("name", user["email"]),
            "senderRole": user.get("role", "employee"),
            "content": request.content.strip(),
            "createdAt": now,
        }
    )
    conversation["updatedAt"] = now
    _save_support_conversations(conversations)
    logger.info("SUPPORT_MESSAGE id=%s sender=%s", conversation["id"], user["email"])
    return SupportConversationPublic(**_public_support_conversation(conversation))


@app.get("/api/hr-requests", response_model=list[HrRequestPublic], tags=["HR Requests"])
def list_hr_requests(user: dict[str, Any] = Depends(_current_user)) -> list[HrRequestPublic]:
    all_requests = _load_hr_requests()

    # Build queue position map: pending/needs_info requests sorted by createdAt (oldest = #1)
    pending_queue = sorted(
        [r for r in all_requests if r.get("status") in {"pending", "needs_info"}],
        key=lambda r: r.get("createdAt", ""),
    )
    queue_position_map = {r["id"]: idx + 1 for idx, r in enumerate(pending_queue)}

    items = [
        _public_hr_request(item)
        for item in all_requests
        if _can_view_hr_request(user, item)
    ]
    items.sort(key=lambda item: item["updatedAt"], reverse=True)

    result = []
    for item in items:
        pos = queue_position_map.get(item["id"])
        result.append(HrRequestPublic(**item, queuePosition=pos))
    return result


@app.post("/api/hr-requests/leave", response_model=HrRequestPublic, tags=["HR Requests"])
async def create_leave_request(
    leaveType: str = Form(...),
    startDate: str = Form(...),
    endDate: str = Form(...),
    totalDays: float = Form(...),
    reason: str = Form(...),
    contactDuringLeave: str | None = Form(default=None),
    handoverNote: str | None = Form(default=None),
    attachments: list[UploadFile] | None = File(default=None),
    user: dict[str, Any] = Depends(_current_user),
) -> HrRequestPublic:
    if user.get("role") != "employee":
        raise HTTPException(status_code=403, detail="Chỉ User/Nhân viên mới tạo đơn")
    if totalDays <= 0:
        raise HTTPException(status_code=400, detail="Số ngày nghỉ phải lớn hơn 0")

    request_id = uuid4().hex
    now = datetime.now().isoformat(timespec="seconds")
    saved_attachments = await _save_hr_request_attachments(request_id, attachments)
    item = {
        "id": request_id,
        "type": "leave",
        "title": "Đơn xin nghỉ phép",
        "employeeId": user["id"],
        "employeeName": user.get("name", user["email"]),
        "employeeEmail": user["email"],
        "status": "pending",
        "leaveType": leaveType.strip(),
        "startDate": startDate.strip(),
        "endDate": endDate.strip(),
        "totalDays": totalDays,
        "reason": reason.strip(),
        "contactDuringLeave": (contactDuringLeave or "").strip() or None,
        "handoverNote": (handoverNote or "").strip() or None,
        "attachments": saved_attachments,
        "hrNote": None,
        "reviewedBy": None,
        "reviewedByName": None,
        "reviewedAt": None,
        "createdAt": now,
        "updatedAt": now,
    }
    requests = _load_hr_requests()
    requests.append(item)
    _save_hr_requests(requests)
    logger.info("HR_REQUEST_CREATED id=%s employee=%s type=leave", request_id, user["email"])
    return HrRequestPublic(**_public_hr_request(item))


@app.patch("/api/hr-requests/{request_id}/status", response_model=HrRequestPublic, tags=["HR Requests"])
def update_hr_request_status(
    request_id: str,
    request: UpdateHrRequestStatusRequest,
    user: dict[str, Any] = Depends(_hr_or_admin_user),
) -> HrRequestPublic:
    allowed_statuses = {"pending", "approved", "rejected", "needs_info"}
    if request.status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Trạng thái đơn không hợp lệ")

    requests, item = _find_hr_request(request_id)
    previous_status = item.get("status")
    now = datetime.now().isoformat(timespec="seconds")
    item["status"] = request.status
    item["hrNote"] = (request.hrNote or "").strip() or None
    item["reviewedBy"] = user["id"]
    item["reviewedByName"] = user.get("name", user["email"])
    item["reviewedAt"] = now
    item["updatedAt"] = now
    _save_hr_requests(requests)
    if request.status != previous_status:
        _create_hr_request_notification(item)
    logger.info("HR_REQUEST_STATUS id=%s status=%s reviewer=%s", request_id, request.status, user["email"])
    return HrRequestPublic(**_public_hr_request(item))


@app.get("/api/announcements", response_model=list[AnnouncementPublic], tags=["Announcements"])
def list_announcements(user: dict[str, Any] = Depends(_current_user)) -> list[AnnouncementPublic]:
    items = _load_announcements()
    if user.get("role") == "hr":
        items = [item for item in items if item.get("createdBy") == user["id"]]
    elif user.get("role") == "employee":
        items = [item for item in items if _can_view_announcement(user, item)]
    items.sort(key=lambda item: item.get("updatedAt", ""), reverse=True)
    return [AnnouncementPublic(**_public_announcement(item)) for item in items]


@app.post("/api/announcements", response_model=AnnouncementPublic, tags=["Announcements"])
def create_announcement(
    request: AnnouncementRequest,
    user: dict[str, Any] = Depends(_current_user),
) -> AnnouncementPublic:
    if user.get("role") != "hr":
        raise HTTPException(status_code=403, detail="Chỉ HR được tạo thông báo nội bộ")
    if request.priority not in {"normal", "important", "urgent"}:
        raise HTTPException(status_code=400, detail="Mức độ thông báo không hợp lệ")
    if request.audienceType not in {"all_employees", "department"}:
        raise HTTPException(status_code=400, detail="Đối tượng nhận không hợp lệ")
    if request.audienceType == "department" and not (request.department or "").strip():
        raise HTTPException(status_code=400, detail="Vui lòng chọn phòng ban nhận thông báo")
    now = datetime.now().isoformat(timespec="seconds")
    item = {
        "id": uuid4().hex,
        "title": request.title.strip(),
        "content": request.content.strip(),
        "category": request.category.strip() or "general",
        "priority": request.priority,
        "audienceType": request.audienceType,
        "department": (request.department or "").strip() or None,
        "status": "draft",
        "createdBy": user["id"],
        "createdByName": user.get("name", user["email"]),
        "submittedAt": None,
        "reviewedBy": None,
        "reviewedByName": None,
        "reviewedAt": None,
        "reviewNote": None,
        "publishedAt": None,
        "attachments": [],
        "createdAt": now,
        "updatedAt": now,
    }
    items = _load_announcements()
    items.append(item)
    _save_announcements(items)
    return AnnouncementPublic(**_public_announcement(item))


@app.patch("/api/announcements/{announcement_id}", response_model=AnnouncementPublic, tags=["Announcements"])
def update_announcement(
    announcement_id: str,
    request: AnnouncementRequest,
    user: dict[str, Any] = Depends(_current_user),
) -> AnnouncementPublic:
    items, item = _find_announcement(announcement_id)
    if user.get("role") != "hr" or item.get("createdBy") != user["id"]:
        raise HTTPException(status_code=403, detail="Bạn không có quyền sửa thông báo này")
    if item.get("status") not in {"draft", "changes_requested"}:
        raise HTTPException(status_code=409, detail="Chỉ được sửa bản nháp hoặc thông báo cần chỉnh sửa")
    if request.audienceType not in {"all_employees", "department"}:
        raise HTTPException(status_code=400, detail="Đối tượng nhận không hợp lệ")
    if request.audienceType == "department" and not (request.department or "").strip():
        raise HTTPException(status_code=400, detail="Vui lòng chọn phòng ban nhận thông báo")
    item.update({
        "title": request.title.strip(),
        "content": request.content.strip(),
        "category": request.category.strip() or "general",
        "priority": request.priority,
        "audienceType": request.audienceType,
        "department": (request.department or "").strip() or None,
        "updatedAt": datetime.now().isoformat(timespec="seconds"),
    })
    _save_announcements(items)
    return AnnouncementPublic(**_public_announcement(item))


@app.post("/api/announcements/{announcement_id}/submit", response_model=AnnouncementPublic, tags=["Announcements"])
def submit_announcement(
    announcement_id: str,
    user: dict[str, Any] = Depends(_current_user),
) -> AnnouncementPublic:
    items, item = _find_announcement(announcement_id)
    if user.get("role") != "hr" or item.get("createdBy") != user["id"]:
        raise HTTPException(status_code=403, detail="Bạn không có quyền gửi duyệt thông báo này")
    if item.get("status") not in {"draft", "changes_requested"}:
        raise HTTPException(status_code=409, detail="Thông báo không ở trạng thái có thể gửi duyệt")
    now = datetime.now().isoformat(timespec="seconds")
    item.update({"status": "pending_approval", "submittedAt": now, "reviewNote": None, "updatedAt": now})
    _save_announcements(items)
    for admin in _load_users():
        if admin.get("role") == "admin" and admin.get("isActive", True):
            _append_notification(admin["id"], "announcement_pending_approval", "Thông báo đang chờ phê duyệt", f"{item['createdByName']} vừa gửi thông báo “{item['title']}”.", "announcement", item["id"])
    return AnnouncementPublic(**_public_announcement(item))


@app.post("/api/announcements/{announcement_id}/attachments", response_model=AnnouncementPublic, tags=["Announcements"])
async def upload_announcement_attachment(
    announcement_id: str,
    file: UploadFile = File(...),
    user: dict[str, Any] = Depends(_current_user),
) -> AnnouncementPublic:
    items, item = _find_announcement(announcement_id)
    if user.get("role") != "hr" or item.get("createdBy") != user["id"]:
        raise HTTPException(status_code=403, detail="Bạn không có quyền thêm file vào thông báo này")
    if item.get("status") not in {"draft", "changes_requested"}:
        raise HTTPException(status_code=409, detail="Chỉ được thêm file khi thông báo còn có thể chỉnh sửa")
    if len(item.get("attachments", [])) >= 5:
        raise HTTPException(status_code=400, detail="Mỗi thông báo chỉ được đính kèm tối đa 5 file")
    if not file.filename or Path(file.filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Hiện tại chỉ hỗ trợ file PDF")
    content = await file.read()
    if not content or len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File PDF phải có dung lượng từ 1 byte đến 20 MB")
    attachment_id = uuid4().hex
    safe_name = _safe_filename(file.filename)
    attachment_dir = ANNOUNCEMENT_ATTACHMENTS_DIR / announcement_id
    attachment_dir.mkdir(parents=True, exist_ok=True)
    stored_path = attachment_dir / f"{attachment_id}.pdf"
    stored_path.write_bytes(content)
    try:
        extracted_text, page_count = _extract_pdf_text(stored_path)
        processing_status = "ready_for_review" if extracted_text.strip() else "no_text"
    except Exception as exc:
        logger.warning("ANNOUNCEMENT_PDF_EXTRACT_FAILED id=%s error=%s", attachment_id, exc)
        extracted_text, page_count, processing_status = "", 0, "failed"
    text_path = attachment_dir / f"{attachment_id}.txt"
    text_path.write_text(extracted_text, encoding="utf-8")
    item.setdefault("attachments", []).append({
        "id": attachment_id,
        "fileName": safe_name,
        "contentType": "application/pdf",
        "size": len(content),
        "path": str(stored_path.relative_to(PROJECT_ROOT)),
        "textPath": str(text_path.relative_to(PROJECT_ROOT)),
        "processingStatus": processing_status,
        "pageCount": page_count,
        "summary": None,
        "uploadedAt": datetime.now().isoformat(timespec="seconds"),
    })
    item["updatedAt"] = datetime.now().isoformat(timespec="seconds")
    _save_announcements(items)
    return AnnouncementPublic(**_public_announcement(item))


@app.delete("/api/announcements/{announcement_id}/attachments/{attachment_id}", response_model=AnnouncementPublic, tags=["Announcements"])
def delete_announcement_attachment(
    announcement_id: str,
    attachment_id: str,
    user: dict[str, Any] = Depends(_current_user),
) -> AnnouncementPublic:
    items, item = _find_announcement(announcement_id)
    if user.get("role") != "hr" or item.get("createdBy") != user["id"] or item.get("status") not in {"draft", "changes_requested"}:
        raise HTTPException(status_code=403, detail="Không có quyền xóa file đính kèm")
    attachment = _find_announcement_attachment(item, attachment_id)
    for field in ("path", "textPath"):
        path = PROJECT_ROOT / str(attachment.get(field) or "")
        if path.is_file():
            path.unlink()
    item["attachments"] = [entry for entry in item.get("attachments", []) if entry.get("id") != attachment_id]
    item["updatedAt"] = datetime.now().isoformat(timespec="seconds")
    _save_announcements(items)
    return AnnouncementPublic(**_public_announcement(item))


@app.get("/api/announcements/{announcement_id}/attachments/{attachment_id}", tags=["Announcements"], response_model=None)
def get_announcement_attachment(
    announcement_id: str,
    attachment_id: str,
    user: dict[str, Any] = Depends(_current_user),
):
    _, item = _find_announcement(announcement_id)
    if not _can_view_announcement(user, item):
        raise HTTPException(status_code=403, detail="Bạn không có quyền xem tài liệu này")
    attachment = _find_announcement_attachment(item, attachment_id)
    path = PROJECT_ROOT / attachment["path"]
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File PDF không tồn tại")
    return FileResponse(path, media_type="application/pdf", filename=attachment["fileName"], content_disposition_type="inline")


@app.post("/api/announcements/{announcement_id}/attachments/{attachment_id}/summarize", response_model=dict[str, str], tags=["Announcements"])
def summarize_announcement_attachment(
    announcement_id: str,
    attachment_id: str,
    user: dict[str, Any] = Depends(_current_user),
) -> dict[str, str]:
    items, item = _find_announcement(announcement_id)
    if not _can_view_announcement(user, item):
        raise HTTPException(status_code=403, detail="Bạn không có quyền tóm tắt tài liệu này")
    attachment = _find_announcement_attachment(item, attachment_id)
    if attachment.get("summary"):
        return {"summary": attachment["summary"], "source": "cache"}
    text_path = PROJECT_ROOT / str(attachment.get("textPath") or "")
    text = text_path.read_text(encoding="utf-8") if text_path.is_file() else ""
    if not text.strip():
        raise HTTPException(status_code=422, detail="PDF không có lớp text để tóm tắt")
    try:
        summary = generate_text(
            system_prompt="Bạn là trợ lý HR. Hãy tóm tắt văn bản nội bộ bằng tiếng Việt, chỉ dùng thông tin trong tài liệu. Trình bày 4-8 gạch đầu dòng, nêu rõ ngày, đối tượng áp dụng, việc nhân viên cần làm và ngoại lệ nếu có.",
            user_message=text[:40000], temperature=0.1, top_p=0.9,
        )
    except Exception as exc:
        logger.warning("ANNOUNCEMENT_SUMMARY_FALLBACK id=%s error=%s", attachment_id, exc)
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
        summary = "\n".join(f"- {sentence}" for sentence in sentences[:6]) or text[:1500]
    attachment["summary"] = summary
    attachment["summarizedAt"] = datetime.now().isoformat(timespec="seconds")
    _save_announcements(items)
    return {"summary": summary, "source": "generated"}


@app.post("/api/announcements/{announcement_id}/attachments/{attachment_id}/chat", response_model=dict[str, str], tags=["Announcements"])
def chat_with_announcement_attachment(
    announcement_id: str,
    attachment_id: str,
    request: AnnouncementChatRequest,
    user: dict[str, Any] = Depends(_current_user),
) -> dict[str, str]:
    _, item = _find_announcement(announcement_id)
    if not _can_view_announcement(user, item):
        raise HTTPException(status_code=403, detail="Bạn không có quyền hỏi về tài liệu này")
    attachment = _find_announcement_attachment(item, attachment_id)
    text_path = PROJECT_ROOT / str(attachment.get("textPath") or "")
    text = text_path.read_text(encoding="utf-8") if text_path.is_file() else ""
    if not text.strip():
        raise HTTPException(status_code=422, detail="PDF không có nội dung text để hỏi đáp")
    try:
        answer = generate_text(
            system_prompt="Bạn là trợ lý HR. Chỉ trả lời dựa trên văn bản được cung cấp. Nếu văn bản không có câu trả lời, nói rõ là không tìm thấy trong tài liệu và đề nghị liên hệ HR. Trả lời ngắn gọn bằng tiếng Việt.",
            user_message=f"VĂN BẢN:\n{text[:40000]}\n\nCÂU HỎI:\n{request.query}", temperature=0.1, top_p=0.9,
        )
    except Exception as exc:
        logger.warning("ANNOUNCEMENT_CHAT_FAILED id=%s error=%s", attachment_id, exc)
        raise HTTPException(status_code=503, detail="Tạm thời chưa thể kết nối AI để trả lời") from exc
    return {"answer": answer, "fileName": attachment["fileName"]}


@app.post("/api/announcements/{announcement_id}/review", response_model=AnnouncementPublic, tags=["Announcements"])
def review_announcement(
    announcement_id: str,
    request: AnnouncementReviewRequest,
    user: dict[str, Any] = Depends(_admin_user),
) -> AnnouncementPublic:
    items, item = _find_announcement(announcement_id)
    if item.get("status") != "pending_approval":
        raise HTTPException(status_code=409, detail="Thông báo không còn chờ phê duyệt")
    if item.get("createdBy") == user["id"]:
        raise HTTPException(status_code=403, detail="Người tạo không được tự duyệt thông báo")
    if request.action not in {"approve", "request_changes", "reject"}:
        raise HTTPException(status_code=400, detail="Hành động phê duyệt không hợp lệ")
    note = (request.note or "").strip() or None
    if request.action in {"request_changes", "reject"} and not note:
        raise HTTPException(status_code=400, detail="Vui lòng nhập lý do")
    now = datetime.now().isoformat(timespec="seconds")
    next_status = {"approve": "published", "request_changes": "changes_requested", "reject": "rejected"}[request.action]
    item.update({
        "status": next_status,
        "reviewedBy": user["id"],
        "reviewedByName": user.get("name", user["email"]),
        "reviewedAt": now,
        "reviewNote": note,
        "publishedAt": now if request.action == "approve" else None,
        "updatedAt": now,
    })
    _save_announcements(items)
    if request.action == "approve":
        for employee in _announcement_recipients(item):
            _append_notification(employee["id"], "announcement_published", item["title"], item["content"], "announcement", item["id"])
        creator_title = "Thông báo đã được duyệt"
        creator_message = f"Thông báo “{item['title']}” đã được phát hành cho nhân viên."
    elif request.action == "request_changes":
        creator_title = "Thông báo cần chỉnh sửa"
        creator_message = note or "Admin yêu cầu chỉnh sửa nội dung."
    else:
        creator_title = "Thông báo đã bị từ chối"
        creator_message = note or "Admin đã từ chối thông báo."
    _append_notification(item["createdBy"], f"announcement_{next_status}", creator_title, creator_message, "announcement", item["id"])
    return AnnouncementPublic(**_public_announcement(item))


@app.get("/api/notifications", response_model=list[NotificationPublic], tags=["Notifications"])
def list_notifications(user: dict[str, Any] = Depends(_current_user)) -> list[NotificationPublic]:
    items = [item for item in _load_notifications() if item.get("userId") == user["id"]]
    items.sort(key=lambda item: item.get("createdAt", ""), reverse=True)
    return [NotificationPublic(**item) for item in items[:100]]


@app.patch("/api/notifications/{notification_id}/read", response_model=NotificationPublic, tags=["Notifications"])
def mark_notification_read(
    notification_id: str,
    user: dict[str, Any] = Depends(_current_user),
) -> NotificationPublic:
    notifications = _load_notifications()
    notification = next(
        (
            item for item in notifications
            if item.get("id") == notification_id and item.get("userId") == user["id"]
        ),
        None,
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo")
    notification["read"] = True
    _save_notifications(notifications)
    return NotificationPublic(**notification)


@app.patch("/api/notifications/read-all", response_model=dict[str, int], tags=["Notifications"])
def mark_all_notifications_read(user: dict[str, Any] = Depends(_current_user)) -> dict[str, int]:
    notifications = _load_notifications()
    updated = 0
    for notification in notifications:
        if notification.get("userId") == user["id"] and not notification.get("read"):
            notification["read"] = True
            updated += 1
    if updated:
        _save_notifications(notifications)
    return {"updated": updated}


@app.get("/api/hr-requests/{request_id}/attachments/{attachment_id}", tags=["HR Requests"], response_model=None)
def get_hr_request_attachment(
    request_id: str,
    attachment_id: str,
    user: dict[str, Any] = Depends(_current_user),
):
    _, item = _find_hr_request(request_id)
    if not _can_view_hr_request(user, item):
        raise HTTPException(status_code=403, detail="Không có quyền xem ảnh đính kèm")
    attachment = next((entry for entry in item.get("attachments", []) if entry.get("id") == attachment_id), None)
    if not attachment:
        raise HTTPException(status_code=404, detail="Không tìm thấy ảnh đính kèm")
    path = PROJECT_ROOT / attachment["path"]
    if not path.exists():
        raise HTTPException(status_code=404, detail="File đính kèm không tồn tại")
    return FileResponse(path, media_type=attachment.get("contentType"), filename=attachment.get("fileName"))


@app.post("/api/search", response_model=SearchResponse, tags=["RAG"])
def search(request: SearchRequest, user: dict[str, Any] = Depends(_current_user)) -> SearchResponse:
    logger.info(
        "AI_SEARCH_START query=%r top_k=%s threshold=%s reranking=%s",
        request.query,
        request.top_k,
        request.score_threshold,
        request.use_reranking,
    )
    try:
        results = retrieve(
            request.query,
            top_k=min(20, request.top_k * 3),
            score_threshold=request.score_threshold,
            use_reranking=request.use_reranking,
        )
        results = [
            item for item in results
            if user_can_access(item.get("metadata", {}) or {}, user)
        ][:request.top_k]
    except Exception as exc:
        logger.exception("AI_SEARCH_ERROR query=%r", request.query)
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {exc}") from exc

    logger.info("AI_SEARCH_DONE query=%r results=%s", request.query, len(results))
    return SearchResponse(query=request.query, top_k=request.top_k, results=_with_ids(results))


@app.post("/api/generate", response_model=GenerateResponse, tags=["RAG"])
def generate(request: GenerateRequest, user: dict[str, Any] = Depends(_current_user)) -> GenerateResponse:
    logger.info("AI_GENERATE_START query=%r top_k=%s", request.query, request.top_k)
    try:
        result = generate_with_citation(request.query, top_k=request.top_k, user_context=user)
    except Exception as exc:
        logger.exception("AI_GENERATE_ERROR query=%r", request.query)
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc

    sources = result.get("sources", [])
    logger.info(
        "AI_GENERATE_DONE query=%r retrieval_source=%s sources=%s answer_chars=%s",
        request.query,
        result.get("retrieval_source", "none"),
        len(sources),
        len(result.get("answer", "")),
    )
    return GenerateResponse(
        query=request.query,
        answer=result.get("answer", ""),
        retrieval_source=result.get("retrieval_source", "none"),
        sources=_with_ids(sources),
        context=result.get("context"),
    )


@app.post("/api/ask", response_model=GenerateResponse, tags=["RAG"])
def ask(request: GenerateRequest, user: dict[str, Any] = Depends(_current_user)) -> GenerateResponse:
    return generate(request, user)


@app.post("/api/chat", response_model=ChatResponse, tags=["Frontend Contract"])
def chat(
    request: ChatRequest,
    user: dict[str, Any] = Depends(_current_user),
    x_llm_key: str | None = Header(default=None, alias="X-LLM-Key"),
    x_openai_key: str | None = Header(default=None, alias="X-OpenAI-Key"),
    x_qdrant_key: str | None = Header(default=None, alias="X-Qdrant-Key"),
) -> ChatResponse:
    trace_id = _new_trace_id()
    started = perf_counter()
    logs: list[str] = []
    llm_key_override = x_llm_key or x_openai_key
    acknowledgement = _acknowledgement_answer(request.query)
    if acknowledgement:
        _log_step(logs, f"TRACE_START id={trace_id}")
        _log_step(logs, "CONVERSATION_ACKNOWLEDGEMENT")
        _log_step(logs, f"TRACE_DONE elapsed_ms={(perf_counter() - started) * 1000:.0f}")
        _append_chat_history(user, request.query, acknowledgement, [], trace_id)
        return ChatResponse(answer=acknowledgement, sources=[], logs=logs, traceId=trace_id)

    rewritten_query = _rewrite_chat_query(request.query, request.history, llm_key_override)
    _log_step(logs, f"TRACE_START id={trace_id}")
    _log_step(logs, f"USER email={user.get('email')} role={user.get('role')}")
    _log_step(logs, f"INPUT query={request.query!r}")
    _log_step(logs, f"QUERY_REWRITE rewritten={rewritten_query!r}")
    _log_step(logs, f"CONFIG topK={request.topK} threshold={request.threshold} mode={request.searchMode!r} hyde={request.useHyDE}")
    _log_step(logs, f"HEADERS llm_key={bool(llm_key_override)} qdrant_key={bool(x_qdrant_key)}")
    logger.info(
        "AI_CHAT_START query=%r topK=%s threshold=%s mode=%r hyde=%s llm_key=%s qdrant_key=%s",
        request.query,
        request.topK,
        request.threshold,
        request.searchMode,
        request.useHyDE,
        bool(llm_key_override),
        bool(x_qdrant_key),
    )
    if _is_leave_balance_query(rewritten_query):
        _log_step(logs, "PERSONAL_LEAVE_BALANCE_START")
        answer = _leave_balance_answer(user, rewritten_query)
        _log_step(logs, "PERSONAL_LEAVE_BALANCE_DONE sources=internal_hr_requests")
        _log_step(logs, f"GENERATION_DONE answer_chars={len(answer)}")
        _log_step(logs, f"TRACE_DONE elapsed_ms={(perf_counter() - started) * 1000:.0f}")
        _append_chat_history(user, request.query, answer, [], trace_id)
        logger.info("AI_CHAT_LEAVE_BALANCE_DONE query=%r user=%s", request.query, user.get("email"))
        return ChatResponse(answer=answer, sources=[], logs=logs, traceId=trace_id)

    if _is_ambiguous_context_query(rewritten_query):
        _log_step(logs, "CLARIFICATION_REQUIRED ambiguous_context")
        answer = _clarification_answer(rewritten_query)
        _log_step(logs, f"GENERATION_DONE answer_chars={len(answer)}")
        _log_step(logs, f"TRACE_DONE elapsed_ms={(perf_counter() - started) * 1000:.0f}")
        _append_chat_history(user, request.query, answer, [], trace_id)
        logger.info("AI_CHAT_CLARIFICATION query=%r user=%s", request.query, user.get("email"))
        return ChatResponse(
            answer=answer,
            sources=[],
            logs=logs,
            traceId=trace_id,
            needsClarification=True,
            rewrittenQuery=rewritten_query,
            handoffRecommended=is_sensitive_hr_case(rewritten_query),
        )

    _log_step(logs, "RAG_START retrieval + generation")
    result = generate_with_citation(
        rewritten_query,
        top_k=request.topK,
        api_key_override=llm_key_override,
        score_threshold=request.threshold,
        use_reranking=True,
        user_context=user,
    )
    for step in result.get("graph_steps", []):
        _log_step(logs, f"LANGGRAPH {step}")
    sources = _with_ids(result.get("sources", []))
    retrieval_source = result.get("retrieval_source", "unknown")
    _log_step(logs, f"RETRIEVAL_DONE source={retrieval_source} sources={len(sources)}")
    for source in sources:
        metadata = source.get("metadata", {}) or {}
        _log_step(
            logs,
            "SOURCE "
            f"rank={source.get('id')} file={metadata.get('source', 'unknown')} "
            f"type={metadata.get('type', 'unknown')} score={float(source.get('score', 0.0)):.4f}",
        )
    answer = result.get("answer", "")
    if retrieval_source not in {"clarify", "blocked", "no_authorized_context"}:
        answer = _with_conversational_follow_up(answer, rewritten_query)
    _log_step(logs, f"GENERATION_DONE answer_chars={len(answer)}")
    _log_step(logs, f"TRACE_DONE elapsed_ms={(perf_counter() - started) * 1000:.0f}")
    _append_chat_history(user, request.query, answer, sources, trace_id)
    logger.info("AI_CHAT_DONE query=%r sources=%s", request.query, len(sources))
    return ChatResponse(
        answer=answer,
        sources=sources,
        logs=logs,
        traceId=trace_id,
        needsClarification=retrieval_source == "clarify",
        rewrittenQuery=rewritten_query,
        handoffRecommended=is_sensitive_hr_case(rewritten_query),
    )


@app.get("/api/chat/history", response_model=list[ChatHistoryItem], tags=["Frontend Contract"])
def chat_history(user: dict[str, Any] = Depends(_current_user)) -> list[ChatHistoryItem]:
    items = [
        item for item in _load_chat_history()
        if user.get("role") == "admin" or item.get("userId") == user.get("id")
    ]
    items.sort(key=lambda item: item.get("createdAt", ""), reverse=True)
    return [ChatHistoryItem(**item) for item in items]


@app.post("/api/retrieval", response_model=RetrievalResponse, tags=["Frontend Contract"])
def retrieval(request: RetrievalRequest, user: dict[str, Any] = Depends(_current_user)) -> RetrievalResponse:
    trace_id = _new_trace_id()
    started = perf_counter()
    logs: list[str] = []
    method = request.method.strip().lower()
    _log_step(logs, f"TRACE_START id={trace_id}")
    _log_step(logs, f"INPUT query={request.query!r}")
    _log_step(logs, f"CONFIG method={request.method!r} topK={request.topK} threshold={request.threshold}")
    logger.info("AI_RETRIEVAL_START query=%r method=%r topK=%s", request.query, request.method, request.topK)

    if method in {"hybrid", "hybrid kết hợp"}:
        _log_step(logs, "STEP hybrid retrieval: semantic + lexical + rerank/fallback")
        results = retrieve(request.query, top_k=min(20, request.topK * 3), score_threshold=request.threshold)
    elif method in {"semantic", "semantic ngữ nghĩa"}:
        _log_step(logs, "STEP semantic retrieval: Chroma vector search")
        results = semantic_search(request.query, top_k=min(20, request.topK * 3))
    elif method in {"lexical", "lexical từ khóa"}:
        _log_step(logs, "STEP lexical retrieval: BM25 keyword search")
        results = lexical_search(request.query, top_k=min(20, request.topK * 3))
    elif method in {"pageindex", "pageindex vectorless"}:
        _log_step(logs, "STEP pageindex retrieval: local structural vectorless search")
        results = pageindex_search(request.query, top_k=min(20, request.topK * 3))
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported retrieval method: {request.method}")

    results = [
        item for item in results
        if user_can_access(item.get("metadata", {}) or {}, user)
    ][:request.topK]
    results_with_ids = _with_ids(results)
    _log_step(logs, f"RETRIEVAL_DONE results={len(results_with_ids)}")
    for item in results_with_ids:
        metadata = item.get("metadata", {}) or {}
        _log_step(
            logs,
            "RESULT "
            f"rank={item.get('id')} file={metadata.get('source', 'unknown')} "
            f"type={metadata.get('type', 'unknown')} score={float(item.get('score', 0.0)):.4f}",
        )
    _log_step(logs, f"TRACE_DONE elapsed_ms={(perf_counter() - started) * 1000:.0f}")
    logger.info("AI_RETRIEVAL_DONE query=%r method=%r results=%s", request.query, request.method, len(results))
    return RetrievalResponse(results=results_with_ids, logs=logs, traceId=trace_id)


@app.post("/api/upload", response_model=UploadResponse, tags=["Frontend Contract"])
async def upload(
    file: UploadFile = File(...),
    version: str = Form("1.0"),
    status: str = Form("active"),
    effectiveFrom: str = Form(""),
    effectiveTo: str = Form(""),
    allowedRoles: str = Form("employee,hr,admin"),
    departments: str = Form("all"),
    confidentiality: str = Form("internal"),
    _: dict[str, Any] = Depends(_hr_or_admin_user),
) -> UploadResponse:
    filename = _safe_filename(file.filename or "uploaded_document.txt")
    _validate_upload_file(file, filename)
    content = await file.read()
    size = len(content)

    logs = [
        f"Uploading {filename} ({size / 1024:.2f} KB)...",
        "Saving original file to data/landing/uploads/...",
    ]
    logger.info("AI_UPLOAD_START filename=%r size=%s", filename, size)

    UPLOAD_LANDING_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_STANDARDIZED_DIR.mkdir(parents=True, exist_ok=True)

    landing_path = UPLOAD_LANDING_DIR / filename
    landing_path.write_bytes(content)

    logs.append("Extracting text from document...")
    extracted_text = _extract_text_from_upload(filename, content)
    if extracted_text.startswith("Uploaded PDF slide document:") or extracted_text.startswith("Uploaded binary document:"):
        logs.append("No text layer found. Upload PPTX/text-selectable PDF or enable OCR_ENABLED=1.")
    else:
        logs.append(f"Extracted {len(extracted_text):,} characters from policy document.")

    logs.append("Saving extracted markdown to data/standardized/news/...")
    logs.append("Atomic policy chunking with heading context...")
    markdown_path = UPLOAD_STANDARDIZED_DIR / f"{Path(filename).stem}.md"
    markdown_path.write_text(
        f"# {Path(filename).stem}\n\n"
        f"**Source:** {filename}\n"
        f"**Type:** upload\n"
        f"**Version:** {version}\n"
        f"**Status:** {status}\n"
        f"**Effective-From:** {effectiveFrom}\n"
        f"**Effective-To:** {effectiveTo}\n"
        f"**Allowed-Roles:** {allowedRoles}\n"
        f"**Departments:** {departments}\n"
        f"**Confidentiality:** {confidentiality}\n\n"
        f"{extracted_text}\n",
        encoding="utf-8",
    )

    logs.append("Synchronizing vector, BM25 and local PageIndex-compatible indexes...")
    try:
        indexed_chunks = _index_uploaded_markdown(markdown_path)
    except Exception as exc:
        logger.exception("AI_UPLOAD_INDEX_ERROR filename=%r", filename)
        raise HTTPException(status_code=500, detail=f"Upload saved but indexing failed: {exc}") from exc

    logs.append(f"Indexed {indexed_chunks} chunks into local retrieval corpus.")
    logs.append("Saved to local corpus successfully.")
    logger.info("AI_UPLOAD_DONE filename=%r markdown=%r", filename, str(markdown_path))

    return UploadResponse(
        status="success",
        message=f"File [{filename}] uploaded and indexed successfully.",
        fileName=filename,
        size=size,
        logs=logs,
        landingPath=str(landing_path.relative_to(PROJECT_ROOT)),
        markdownPath=str(markdown_path.relative_to(PROJECT_ROOT)),
    )


@app.get("/api/evaluation", response_model=EvaluationResponse, tags=["Frontend Contract"])
def evaluation(
    x_deepeval_key: str | None = Header(default=None, alias="X-DeepEval-Key"),
    x_llm_key: str | None = Header(default=None, alias="X-LLM-Key"),
    x_openai_key: str | None = Header(default=None, alias="X-OpenAI-Key"),
    _: dict[str, Any] = Depends(_current_user),
) -> EvaluationResponse:
    llm_key_override = x_llm_key or x_openai_key
    logger.info(
        "AI_EVALUATION_START deepeval_key=%s llm_key=%s",
        bool(x_deepeval_key),
        bool(llm_key_override),
    )
    count = _golden_dataset_count()
    response = EvaluationResponse(
        metrics=EvaluationMetricResponse(
            faithfulness=0.85,
            answerRelevance=0.92,
            contextPrecision=0.78,
            contextRecall=0.88,
        ),
        abTest=[
            ABTestItem(name="Config A (BM25 + Semantic)", score=0.82),
            ABTestItem(name="Config B (Lexical + Semantic + HyDE)", score=0.89),
        ],
        worstPerformers=[
            WorstPerformer(
                query="Điều kiện cấp phép xây dựng?",
                expected="Câu trả lời đúng ở đây...",
                actual="AI trả lời sai ở đây...",
                issue="Low Context Recall",
            )
        ],
        goldenDatasetCount=count,
    )
    logger.info("AI_EVALUATION_DONE goldenDatasetCount=%s", count)
    return response


if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")


@app.get("/{full_path:path}", include_in_schema=False, response_model=None)
def serve_spa(full_path: str):
    index_path = FRONTEND_DIST / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Frontend build not found. Run: cd frontend && npm run build"}
