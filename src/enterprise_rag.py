"""Enterprise controls shared by ingestion and retrieval."""

from __future__ import annotations

from datetime import date
import re
from typing import Any


PUBLIC_ROLES = ("employee", "hr", "admin")


def csv_values(value: str | list[str] | None, default: tuple[str, ...] = ()) -> list[str]:
    if isinstance(value, list):
        values = value
    else:
        values = re.split(r"[,;]", value or "")
    cleaned = [str(item).strip().lower() for item in values if str(item).strip()]
    return list(dict.fromkeys(cleaned)) or list(default)


def enrich_policy_metadata(metadata: dict[str, Any], overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    values = {**metadata, **(overrides or {})}
    return {
        **values,
        "document_id": str(values.get("document_id") or values.get("source") or "unknown"),
        "version": str(values.get("version") or "1.0"),
        "status": str(values.get("status") or "active").strip().lower(),
        "effective_from": str(values.get("effective_from") or ""),
        "effective_to": str(values.get("effective_to") or ""),
        "allowed_roles": ",".join(csv_values(values.get("allowed_roles"), PUBLIC_ROLES)),
        "departments": ",".join(csv_values(values.get("departments"), ("all",))),
        "confidentiality": str(values.get("confidentiality") or "internal").strip().lower(),
    }


def metadata_is_active(metadata: dict[str, Any], today: date | None = None) -> bool:
    today = today or date.today()
    if str(metadata.get("status", "active")).lower() != "active":
        return False
    try:
        start = date.fromisoformat(str(metadata.get("effective_from") or ""))
        if today < start:
            return False
    except ValueError:
        pass
    try:
        end = date.fromisoformat(str(metadata.get("effective_to") or ""))
        if today > end:
            return False
    except ValueError:
        pass
    return True


def user_can_access(metadata: dict[str, Any], user: dict[str, Any]) -> bool:
    if not metadata_is_active(metadata):
        return False
    role = str(user.get("role") or "employee").lower()
    roles = csv_values(metadata.get("allowed_roles"), PUBLIC_ROLES)
    if role not in roles:
        return False
    allowed_departments = csv_values(metadata.get("departments"), ("all",))
    department = str(user.get("department") or "").strip().lower()
    return "all" in allowed_departments or bool(department and department in allowed_departments)


def is_sensitive_hr_case(query: str) -> bool:
    folded = query.lower()
    return any(
        term in folded
        for term in (
            "quấy rối", "quay roi", "khiếu nại", "khieu nai", "tranh chấp lương",
            "tranh chap luong", "kỷ luật", "ky luat", "sa thải", "sa thai",
            "phân biệt đối xử", "phan biet doi xu", "tố cáo", "to cao",
        )
    )
