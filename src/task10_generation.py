"""Generation layer for the HR policy helpdesk assistant."""

from __future__ import annotations

import re
import unicodedata

from dotenv import load_dotenv

load_dotenv()

TOP_K = 5
TOP_P = 0.85
TEMPERATURE = 0.2

_STOPWORDS = {
    "ai", "anh", "ban", "bi", "cac", "can", "cho", "co", "cua", "duoc", "em",
    "di", "gia", "gi", "hoi", "khong", "la", "lam", "ly", "minh", "moi", "muon",
    "nao", "nay", "neu", "ngay", "nhan", "nhu", "nhung", "nua", "phai", "sao",
    "phep", "tai", "tao", "tham", "the", "thi", "thoi", "toi", "trong", "va",
    "ve", "vien", "voi", "xu",
}

_SUPPORTED_HR_TOPIC_ALIASES = (
    "nghi phep", "xin nghi", "phep nam", "ngay phep",
    "nghi om", "om dau", "bi om", "dang om", "bi benh", "khong khoe",
    "giay xac nhan y te", "bao hiem xa hoi",
    "nghi viec", "thoi viec", "cham dut hop dong", "resign", "resignation",
    "cham cong", "quen cham cong", "gio lam", "di muon", "tan ca",
    "lam them", "ot", "overtime", "ngoai gio",
    "luong", "thuong", "kpi", "luong thuong",
    "bao hiem", "bhxh", "bhyt", "bhtn",
    "thu viec", "nhan vien moi", "onboarding", "hoi nhap",
    "phuc loi", "kham suc khoe", "hoc phi", "gui xe", "an trua", "phu cap",
    "dao tao", "khoa hoc", "nang luc",
    "phan anh", "ho tro", "khieu nai", "moi truong lam viec", "quan he lao dong",
    "cong tac", "quyet toan", "chi phi",
    "ung xu", "quy tac", "dao duc", "chuan muc",
    "hieu suat", "danh gia", "muc tieu cong viec",
    "van hoa", "gia tri cot loi", "tin tam tri toc tinh nhan",
    "du lieu ca nhan", "bao ve du lieu",
    "vingroup", "vin group",
    "chinh sach", "quy trinh", "noi quy", "hr portal", "phong hr", "nhan su",
)

SYSTEM_PROMPT = """Bạn là trợ lý HR nội bộ, giao tiếp tự nhiên như một nhân sự hỗ trợ nhân viên hằng ngày.
Luôn trả lời bằng tiếng Việt có dấu, rõ ràng, ấm áp và dễ hiểu.

Nhiệm vụ của bạn:
- Trả lời câu hỏi về chính sách nhân sự, quy trình nội bộ, nghỉ phép, lương thưởng, bảo hiểm, hợp đồng, phúc lợi, công tác phí và biểu mẫu.
- Hướng dẫn thủ tục từng bước khi tài liệu nguồn có đủ căn cứ.
- Cá nhân hóa theo bối cảnh người dùng nếu họ cung cấp thông tin cần thiết.
- Giảm tải câu hỏi lặp lại cho phòng HR, nhưng không thay HR ra quyết định cuối cùng.
- Hiểu cách nói đời thường, câu thiếu chủ ngữ và lỗi chính tả nhẹ; phản hồi như một nhân sự đang trò chuyện, không bắt người dùng dùng đúng thuật ngữ chính sách.
- Khi ý người dùng có thể hiểu theo nhiều hướng, hỏi một câu ngắn để làm rõ thay vì từ chối ngay.

Guardrail bắt buộc:
- Chỉ khẳng định nội dung chính sách hoặc quy trình khi có căn cứ trong Context.
- Không nêu tên file, tên dataset, loại nguồn kỹ thuật, cấu hình hệ thống, API key, token hoặc chi tiết vận hành ẩn trong phần trả lời cho người dùng.
- Không mở đầu theo kiểu kỹ thuật như "Theo tài liệu đã nạp", "Context", "Prompt", "Source" hoặc các câu giống log hệ thống.
- Nếu Context chưa đủ căn cứ, nói rõ rằng hiện chưa tìm thấy thông tin đủ rõ trong tài liệu HR hiện có và hướng dẫn người dùng nên kiểm tra thêm gì.
- Không tiết lộ dữ liệu cá nhân, hồ sơ HR hoặc thông tin riêng của người khác.
- Không tư vấn pháp lý, y tế, tài chính cá nhân hoặc quyết định nhân sự ngoài phạm vi chính sách nội bộ.
- Nếu câu hỏi mơ hồ hoặc thiếu dữ kiện, hãy hỏi lại ngắn gọn để lấy thêm thông tin trước khi kết luận.
- Mỗi khẳng định lấy từ Context phải kết thúc bằng citation đúng dạng [S1], [S2] tương ứng. Không tạo citation không tồn tại.
- Nếu các nguồn mâu thuẫn, ưu tiên phiên bản đang hiệu lực mới nhất; nếu chưa xác định được thì nêu rõ mâu thuẫn và chuyển HR xác minh.
- Với ca nhạy cảm như tranh chấp lương, kỷ luật, chấm dứt hợp đồng, khiếu nại, quấy rối, sức khỏe cá nhân hoặc tình huống cần xác minh hồ sơ, hãy đề xuất chuyển tiếp phòng HR.

Cấu trúc trả lời ưu tiên:
1. Trả lời trực tiếp, ngắn gọn, tự nhiên.
2. Tóm tắt các ý chính hoặc các bước cần làm.
3. Nếu cần, nêu mục người dùng nên kiểm tra thêm hoặc nên liên hệ HR.
4. Chỉ dùng giọng văn hỗ trợ người dùng cuối, không dùng giọng văn mô tả hệ thống."""

_NO_EVIDENCE_MESSAGE = "Hiện mình chưa tìm thấy căn cứ đủ rõ trong tài liệu HR hiện có để trả lời chính xác câu hỏi này."

_OVERVIEW_TOPIC_ALIASES = {
    "leave": ("nghi phep", "xin nghi", "ngay phep", "phep nam"),
    "sick_leave": ("nghi om", "om dau", "giay xac nhan y te"),
    "attendance": ("cham cong", "quen cham cong", "gio lam"),
    "overtime": ("lam them", "ot", "overtime"),
    "payroll": ("luong", "thuong", "kpi", "luong thuong"),
    "insurance": ("bao hiem", "bhxh", "bhyt", "bhtn"),
    "probation": ("thu viec", "nhan vien moi", "moi vao", "onboarding"),
    "benefits": ("phuc loi", "kham suc khoe", "phu cap"),
    "training": ("dao tao", "khoa hoc"),
    "support": ("phan anh", "ho tro", "khieu nai"),
    "business_trip": ("cong tac", "quyet toan", "chi phi"),
    "conduct": ("ung xu", "quy tac", "dao duc"),
    "performance": ("hieu suat", "danh gia"),
    "culture": ("van hoa", "gia tri cot loi"),
    "privacy": ("du lieu ca nhan", "bao ve du lieu"),
}


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Put strong evidence at the beginning and end of the context window."""
    if len(chunks) <= 2:
        return list(chunks)
    evens = chunks[0::2]
    odds = chunks[1::2]
    return evens + odds[::-1]


def format_context(chunks: list[dict]) -> str:
    """Format chunks with source labels so the model can cite them."""
    parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {}) or {}
        source = meta.get("source", f"Source {i}")
        doc_type = meta.get("type", "unknown")
        citation_id = str(meta.get("citation_id") or f"S{i}")
        parts.append(f"[{citation_id} | source: {source} | type: {doc_type}]\n{chunk['content']}\n")
    return "\n---\n".join(parts)


def _ascii_fold(text: str) -> str:
    folded = "".join(
        char
        for char in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(char) != "Mn"
    )
    return folded.replace("đ", "d")


def _citation(chunk: dict | None) -> str:
    meta = (chunk or {}).get("metadata", {}) or {}
    return f"[{meta.get('source', 'unknown')}, {meta.get('type', 'unknown')}]"


def _cited_chunks(answer: str, chunks: list[dict]) -> list[dict]:
    cited = []
    seen = set()
    for chunk in chunks:
        meta = chunk.get("metadata", {}) or {}
        citation_id = str(meta.get("citation_id") or "")
        citation = f"[{citation_id}]" if citation_id else _citation(chunk)
        key = (meta.get("source", ""), meta.get("type", ""), meta.get("chunk_index", ""))
        if citation in answer and key not in seen:
            cited.append(chunk)
            seen.add(key)
    return cited


def _answer_has_no_evidence(answer: str) -> bool:
    return _NO_EVIDENCE_MESSAGE in answer


def _no_evidence_answer(query: str, guidance: str) -> str:
    return "\n".join([_NO_EVIDENCE_MESSAGE, "", guidance])


def _is_external_general_query(query: str) -> bool:
    folded = _ascii_fold(query)
    return any(
        term in folded
        for term in (
            "bitcoin", "crypto", "gia vang", "chung khoan", "thoi tiet",
            "bong da", "ty gia", "du bao", "mua co phieu", "ket qua xo so",
            "nau an", "cong thuc mon", "phim gi", "nhac gi", "game nao",
            "viet code", "lap trinh", "debug code", "javascript", "python code",
        )
    )


def _is_secret_or_access_query(query: str) -> bool:
    folded = _ascii_fold(query)
    return any(
        term in folded
        for term in (
            "mat khau wifi", "password wifi", "wifi cong ty", "wifi la gi",
            "ma otp", "token", "api key", "secret key",
        )
    )


def _is_medical_advice_query(query: str) -> bool:
    folded = _ascii_fold(query)
    asks_medical_treatment = any(
        term in folded
        for term in ("uong thuoc", "thuoc gi", "dau bung", "dau dau", "kham benh", "chan doan", "don thuoc")
    )
    has_hr_context = any(
        term in folded
        for term in (
            "nghi", "xin phep", "di lam", "cong ty", "quan ly", "sep", "hr",
            "nhan su", "giay to", "bao hiem", "bhxh",
        )
    )
    return asks_medical_treatment and not has_hr_context


def _is_casual_personal_activity_query(query: str) -> bool:
    folded = _ascii_fold(query)
    return any(
        term in folded
        for term in (
            "buon ia", "mac ia", "muon ia", "di ia", "di i", "di cau", "di ngoai",
            "di dai tien", "di dai", "di tieu", "di te", "buon di ve sinh",
            "mac di ve sinh", "di ve sinh", "di toilet", "di wc", "vao wc",
            "nha ve sinh", "restroom",
        )
    )


def _is_greeting_query(query: str) -> bool:
    folded = re.sub(r"\s+", " ", _ascii_fold(query)).strip()
    patterns = (
        r"^(xin chao|chao ban|chao bot|chao|hello|hi|hey|alo)(\b|[!?.\s])",
        r"^(good morning|good afternoon|good evening)(\b|[!?.\s])",
        r"^(cam on|thanks|thank you)(\b|[!?.\s])",
    )
    return any(re.search(pattern, folded) for pattern in patterns)


def _greeting_answer(query: str) -> str:
    folded = _ascii_fold(query)
    if "cam on" in folded or "thanks" in folded or "thank you" in folded:
        return "Mình luôn sẵn sàng hỗ trợ. Nếu bạn cần, cứ hỏi tiếp về nghỉ phép, bảo hiểm, lương thưởng, phúc lợi hoặc các thủ tục HR nhé."
    return (
        "Chào bạn, mình là trợ lý HR. "
        "Mình có thể hỗ trợ các câu hỏi về nghỉ phép, nghỉ việc, bảo hiểm, lương thưởng, phúc lợi, biểu mẫu và quy trình nội bộ. "
        "Bạn cứ hỏi tự nhiên như đang chat với HR nhé."
    )


def _acknowledgement_answer(query: str) -> str | None:
    folded = re.sub(r"[^a-z0-9\s]", " ", _ascii_fold(query))
    folded = re.sub(r"\s+", " ", folded).strip()

    if re.fullmatch(r"(cam on|cam on ban|thanks|thank you|thank you ban|tks|thank)", folded):
        return "Không có gì nhé. Khi nào cần hỏi thêm, bạn cứ nhắn mình."
    if re.fullmatch(r"(khong can|khong can nua|ko can|ko can nua|k can|k can nua|thoi duoc roi)", folded):
        return "Ok, mình dừng tại đây nhé. Khi nào cần hỗ trợ thêm, bạn cứ nhắn mình."
    if re.fullmatch(
        r"(ok|oke|okay|okela|duoc|duoc roi|hieu roi|biet roi|ro roi|toi hieu roi|"
        r"minh hieu roi|tam on|on roi|uh|u|um|vang|da|yes|yep)",
        folded,
    ):
        return "Ok nhé. Nếu cần làm rõ thêm phần vừa trao đổi, bạn cứ nhắn tiếp mình."
    return None


def _is_light_conversation_query(query: str) -> bool:
    folded = re.sub(r"\s+", " ", _ascii_fold(query)).strip()
    patterns = (
        r"^(ban la ai|ai day|ban ten gi|gioi thieu ve ban)(\b|[!?.\s])",
        r"^(ban ho tro gi|ban giup duoc gi|ban lam duoc gi|co the giup gi|giup toi voi|minh muon hoi chut)(\b|[!?.\s])",
        r"^(ban khoe khong|hom nay the nao|noi chuyen chut)(\b|[!?.\s])",
    )
    return any(re.search(pattern, folded) for pattern in patterns)


def _light_conversation_answer(query: str) -> str:
    folded = _ascii_fold(query)
    if re.search(r"(ban la ai|ai day|ban ten gi|gioi thieu ve ban)", folded):
        return (
            "Mình là trợ lý HR nội bộ. Mình hỗ trợ giải đáp chính sách, thủ tục nhân sự, "
            "hướng dẫn xin nghỉ và giúp bạn chuẩn bị thông tin trước khi làm việc với HR."
        )
    if re.search(r"(ban khoe khong|hom nay the nao|noi chuyen chut)", folded):
        return (
            "Mình vẫn sẵn sàng hỗ trợ đây. Nếu bạn có câu hỏi về HR, "
            "cứ nói tự nhiên như đang nhắn với nhân sự nhé."
        )
    return (
        "Mình có thể hỗ trợ về nghỉ phép, nghỉ việc, bảo hiểm, lương thưởng, phúc lợi, "
        "hồ sơ nhân sự và các thủ tục nội bộ. Bạn muốn bắt đầu từ nội dung nào?"
    )


def _is_resignation_query(query: str) -> bool:
    folded = _ascii_fold(query)
    return any(
        term in folded
        for term in (
            "nghi viec", "thoi viec", "xin nghi viec", "nghi han",
            "cham dut hop dong", "ket thuc hop dong", "ban giao nghi viec",
            "resign", "resignation",
        )
    )


def _has_supported_hr_topic(query: str) -> bool:
    folded = _ascii_fold(query)
    return any(re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", folded) for alias in _SUPPORTED_HR_TOPIC_ALIASES)


def _is_sensitive_decision_query(query: str) -> bool:
    folded = _ascii_fold(query)
    return any(
        term in folded
        for term in (
            "duoi viec", "sa thai", "cham dut hop dong", "ky luat", "mang thai",
            "quay roi", "khieu nai", "tranh chap", "kien", "boi thuong",
            "phap ly", "luat lao dong",
        )
    )


def _is_personal_record_query(query: str) -> bool:
    folded = _ascii_fold(query)
    return any(
        term in folded
        for term in (
            "luong cua", "thu nhap cua", "ngay phep con lai cua", "ho so cua",
            "so dien thoai cua", "dia chi cua", "cccd cua", "cmnd cua",
        )
    )


def _is_pending_leave_approval_query(query: str) -> bool:
    folded = _ascii_fold(query)
    approval_terms = ("chua duyet", "cho duyet", "dang duyet", "pending", "khong duyet")
    request_terms = ("don", "xin nghi", "nghi phep")
    return any(term in folded for term in approval_terms) and any(term in folded for term in request_terms)


def _is_unplanned_absence_query(query: str) -> bool:
    folded = _ascii_fold(query)
    return any(
        term in folded
        for term in (
            "khong di lam duoc", "khong the di lam", "khong den cong ty duoc",
            "khong den lam duoc", "vang lam dot xuat",
        )
    )


def _is_prompt_or_internal_query(query: str) -> bool:
    folded = _ascii_fold(query)
    return any(
        term in folded
        for term in (
            "prompt he thong", "system prompt", "prompt system", "prompt an",
            "huong dan an", "huong dan noi bo", "chi dan noi bo", "internal prompt",
            "developer message", "system instruction", "chain of thought", "cot",
            "suy nghi tung buoc", "cau hinh he thong", "noi dung noi bo",
            "loi nhac he thong", "quy tac an",
        )
    )


def _is_other_personal_data_query(query: str) -> bool:
    folded = _ascii_fold(query)
    sensitive_fields = (
        "du lieu ca nhan", "thong tin ca nhan", "luong", "thu nhap", "ngay phep con lai",
        "ho so", "so dien thoai", "dia chi", "cccd", "cmnd", "email",
        "ma nhan vien", "hop dong", "bao hiem", "suc khoe",
    )
    other_people_terms = (
        "nguoi khac", "dong nghiep", "nhan vien khac", "user khac", "nhan vien do",
        "nhan vien nay", "anh ay", "chi ay", "nguoi do", "nguoi nay",
    )
    return any(field in folded for field in sensitive_fields) and any(marker in folded for marker in other_people_terms)


def _needs_more_information(query: str) -> bool:
    if _is_unplanned_absence_query(query):
        return True

    folded = re.sub(r"\s+", " ", _ascii_fold(query)).strip()
    tokens = re.findall(r"\w+", folded)
    references_missing_context = bool(
        re.search(
            r"\b(truong hop nay|truong hop do|truong hop tren|viec nay|cai nay|cai do|van de nay|nhu vay|nhu the|the nay|the do|case nay)\b",
            folded,
        )
    )
    asks_decision = bool(
        re.search(
            r"\b(co can|can khong|co phai|phai khong|nen|xu ly|chuyen tiep|bao ai|hoi ai|duoc khong|co duoc)\b",
            folded,
        )
    )
    has_concrete_detail = bool(
        re.search(
            r"\b(nghi phep|nghi om|bao hiem|bhxh|bhyt|cham cong|di muon|ot|lam them|luong|thuong|hop dong|thu viec|cong tac|dao tao|ky luat|khieu nai|phuc loi|ngay|tu ngay|\d{1,2}[\/.-]\d{1,2}|\d+\s*(ngay|gio|thang))\b",
            folded,
        )
    )
    short_hr_query = len(tokens) <= 3 and _has_supported_hr_topic(query)
    return (references_missing_context and asks_decision and not has_concrete_detail) or short_hr_query


def _clarification_answer(query: str) -> str:
    folded = _ascii_fold(query)

    if _is_unplanned_absence_query(query):
        return "Bạn hãy báo cho quản lý trực tiếp sớm nhất có thể, tốt nhất trước giờ làm việc. Cho mình biết bạn vắng do ốm, việc khẩn cấp hay muốn xin nghỉ phép để mình hướng dẫn đúng thủ tục và giấy tờ cần bổ sung nhé."
    if any(term in folded for term in ("nghi phep", "xin nghi", "phep nam")):
        return "Mình hỗ trợ được nhé. Bạn muốn kiểm tra quyền lợi/ngày phép còn lại, hỏi thủ tục, hay tạo đơn nghỉ? Nếu muốn nghỉ, cho mình biết ngày bắt đầu và số ngày dự kiến nhé."
    if any(term in folded for term in ("nghi om", "om dau", "bi om", "dang om", "bi benh", "khong khoe")):
        return "Bạn dự kiến nghỉ ốm từ ngày nào, trong bao lâu và hiện có giấy khám hoặc giấy nghỉ hưởng BHXH chưa?"
    if any(term in folded for term in ("cham cong", "di muon", "tan ca")):
        return "Vấn đề chấm công xảy ra ngày/ca nào và bạn đang cần điều chỉnh thiếu công, quên chấm hay sai giờ vào-ra?"
    if any(term in folded for term in ("lam them", "overtime", " ot ")):
        return "Bạn đang hỏi cách đăng ký hay cách tính OT? Cho mình thêm ngày làm, số giờ và trạng thái đã được quản lý duyệt chưa nhé."
    if any(term in folded for term in ("luong", "thuong", "kpi")):
        return "Bạn đang cần kiểm tra kỳ lương nào và khoản nào: lương cơ bản, phụ cấp, khấu trừ, OT hay thưởng? Bạn không cần gửi số tài khoản hoặc dữ liệu nhạy cảm."
    if any(term in folded for term in ("bao hiem", "bhxh", "bhyt", "bhtn")):
        return "Bạn muốn hỏi về đăng ký mới, mức hưởng, hồ sơ hay tình trạng tham gia bảo hiểm? Cho mình biết thêm bạn là nhân viên mới hay đang xử lý một chế độ cụ thể nhé."
    if any(term in folded for term in ("nghi viec", "thoi viec", "cham dut hop dong")):
        return "Bạn đang muốn tìm hiểu thời hạn báo trước, quy trình bàn giao hay quyền lợi khi nghỉ việc? Cho mình biết loại hợp đồng và ngày làm việc cuối dự kiến nếu đã có nhé."

    return "Mình chưa đủ ngữ cảnh để trả lời chính xác. Bạn cho mình biết tình huống HR cụ thể đang xảy ra và điều bạn muốn xác định: quyền lợi, thủ tục cần làm hay người cần phê duyệt nhé."


def _refuse_irrelevant_query(query: str) -> str | None:
    acknowledgement = _acknowledgement_answer(query)
    if acknowledgement:
        return acknowledgement
    if _is_greeting_query(query):
        return _greeting_answer(query)
    if _is_light_conversation_query(query):
        return _light_conversation_answer(query)
    if _is_prompt_or_internal_query(query):
        return "Mình không thể chia sẻ prompt hệ thống, hướng dẫn nội bộ, cấu hình ẩn hoặc thông tin vận hành của hệ thống."
    if _is_other_personal_data_query(query):
        return "Mình không thể tiết lộ dữ liệu cá nhân hoặc hồ sơ nhân sự của người khác. Nếu bạn có thẩm quyền xử lý, vui lòng dùng kênh HR chính thức."
    if (
        _is_external_general_query(query)
        or _is_secret_or_access_query(query)
        or _is_medical_advice_query(query)
        or _is_casual_personal_activity_query(query)
    ):
        return "Mình hiện chỉ hỗ trợ các câu hỏi liên quan đến chính sách, thủ tục và nghiệp vụ HR nội bộ. Bạn thử hỏi lại theo hướng nhân sự nhé."
    return None


def _is_vingroup_query(query: str) -> bool:
    folded = _ascii_fold(query)
    return any(term in folded for term in ("vingroup", "vin group", "vin "))


def _is_vingroup_chunk(chunk: dict) -> bool:
    meta = chunk.get("metadata", {}) or {}
    source = _ascii_fold(str(meta.get("source", "")))
    content = _ascii_fold(chunk.get("content", ""))
    return "vingroup" in source or "vingroup" in content


def _chunk_with(chunks: list[dict], *needles: str) -> dict | None:
    folded_needles = [_ascii_fold(needle) for needle in needles]
    for chunk in chunks:
        folded_content = _ascii_fold(chunk.get("content", ""))
        if any(needle in folded_content for needle in folded_needles):
            return chunk
    return chunks[0] if chunks else None


def _query_terms(query: str) -> set[str]:
    folded = _ascii_fold(query)
    return {
        token
        for token in re.findall(r"\w+", folded)
        if (token.isdigit() or len(token) >= 2) and token not in _STOPWORDS
    }


def _evidence_units(chunks: list[dict]) -> list[tuple[str, dict]]:
    units: list[tuple[str, dict]] = []
    for chunk in chunks:
        parts = []
        for line in chunk.get("content", "").splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith(("##", "#", "**Source:**", "**Type:**", "HR Policy Dataset")):
                continue
            if line.startswith("Category:"):
                continue
            line = re.sub(r"\s+(Bước\s+\d+:)", r"\n\1", line)
            for segment in line.splitlines():
                segment = segment.strip()
                if not segment:
                    continue
                if segment.startswith("Bước "):
                    parts.append(segment)
                else:
                    parts.extend(re.split(r"(?<=[.!?])\s+", segment))
        for part in parts:
            part = part.strip(" -")
            if len(part) >= 24:
                units.append((part, chunk))
    return units


def _score_unit(unit: str, query_terms: set[str]) -> float:
    folded = _ascii_fold(unit)
    unit_tokens = set(re.findall(r"\w+", folded))
    overlap = query_terms & unit_tokens
    if len(query_terms) >= 2 and len(overlap) < 2:
        return 0.0
    score = float(len(overlap) * 3)
    for term in query_terms:
        if term in folded:
            score += 0.5
    if folded.startswith("buoc"):
        score += 1.0
    if re.search(r"\b\d+\b", folded) and any(term.isdigit() for term in query_terms):
        score += 2.0
    return score


def _policy_heading_items(chunks: list[dict]) -> list[tuple[str, str, str, dict]]:
    items: list[tuple[str, str, str, dict]] = []
    seen = set()
    for chunk in chunks:
        lines = chunk.get("content", "").splitlines()
        for index, line in enumerate(lines):
            match = re.match(r"^(?:#{1,6}\s*)?((?:HR|VIN)\d{3})\s*[-–]\s*(.+?)\s*$", line.strip())
            if not match:
                continue
            code, title = match.groups()
            category = ""
            if index + 1 < len(lines):
                category_match = re.match(r"^Category:\s*(.+?)\s*$", lines[index + 1].strip())
                if category_match:
                    category = category_match.group(1)
            key = (code, title)
            if key in seen:
                continue
            seen.add(key)
            items.append((code, title, category, chunk))
    return items


def _is_policy_overview_query(query: str) -> bool:
    folded = _ascii_fold(query)
    return any(
        pattern in folded
        for pattern in (
            "co chinh sach gi",
            "co nhung chinh sach",
            "cac chinh sach",
            "danh sach chinh sach",
            "nhung quy dinh",
            "tai lieu gi",
            "policy nao",
        )
    )


def _overview_topics(query: str) -> list[str]:
    folded = _ascii_fold(query)
    return [
        topic
        for topic, aliases in _OVERVIEW_TOPIC_ALIASES.items()
        if any(alias in folded for alias in aliases)
    ]


def _overview_item_matches_topic(code: str, title: str, category: str, topics: list[str]) -> bool:
    folded = _ascii_fold(f"{code} {title} {category}")
    return any(
        alias in folded
        for topic in topics
        for alias in _OVERVIEW_TOPIC_ALIASES[topic]
    )


def _is_new_employee_query(query: str) -> bool:
    folded = _ascii_fold(query)
    return any(
        term in folded
        for term in ("nhan vien moi", "moi vao", "nguoi moi", "onboarding", "hoi nhap", "huong dan", "can biet gi")
    )


def _generic_policy_answer(query: str, chunks: list[dict]) -> str:
    if _is_vingroup_query(query) and any(_is_vingroup_chunk(chunk) for chunk in chunks):
        chunks = [chunk for chunk in chunks if _is_vingroup_chunk(chunk)]

    query_terms = _query_terms(query)
    ranked = []
    seen = set()
    for unit, chunk in _evidence_units(chunks):
        normalized = _ascii_fold(unit)
        if normalized in seen:
            continue
        seen.add(normalized)
        score = _score_unit(unit, query_terms)
        if score > 0:
            ranked.append((score, unit.strip(), chunk))

    ranked.sort(key=lambda item: item[0], reverse=True)
    selected = []
    if ranked:
        best_score = ranked[0][0]
        min_score = max(2.0, best_score * 0.75)
        selected = [item for item in ranked if item[0] >= min_score][:3]

    if not selected:
        if _is_resignation_query(query):
            return _no_evidence_answer(
                query,
                "Mình hiểu bạn đang cần tìm hiểu về việc nghỉ việc hoặc chấm dứt hợp đồng, nhưng hiện tại hệ thống chưa cập nhật tài liệu chính sách chi tiết cho phần này. Bạn vui lòng trao đổi trực tiếp với nhân sự phụ trách để được hướng dẫn chính xác về thời hạn báo trước, bàn giao công việc và tính toán phép năm còn lại nhé. Mình có thể giúp kết nối bạn với HR ngay tại mục 'Hỗ trợ trực tiếp' nha!",
            )
        return _no_evidence_answer(
            query,
            "Mình chưa tìm thấy quy định cụ thể nào trong tài liệu hiện có để trả lời trực tiếp ý này cho bạn. Tình huống này thường sẽ phụ thuộc nhiều vào thông tin hồ sơ cá nhân hoặc phê duyệt từ quản lý trực tiếp. Bạn có cần mình hỗ trợ liên hệ với các anh chị HR để làm rõ thêm không?",
        )

    lines = ["Mình đã rà trong chính sách hiện có và thấy các ý liên quan nhất như sau:"]
    for _, unit, _ in selected:
        lines.append(f"- {unit.rstrip(' .')}.")
    lines.extend(
        [
            "",
            "Nếu bạn muốn, mình có thể diễn giải lại thành quy trình từng bước hoặc checklist ngắn theo đúng trường hợp của bạn.",
        ]
    )
    return "\n".join(lines)


def _policy_overview_answer(query: str, chunks: list[dict]) -> str | None:
    if not _is_policy_overview_query(query):
        return None

    relevant_chunks = chunks
    if _is_vingroup_query(query) and any(_is_vingroup_chunk(chunk) for chunk in chunks):
        relevant_chunks = [chunk for chunk in chunks if _is_vingroup_chunk(chunk)]

    items = _policy_heading_items(relevant_chunks)
    topics = _overview_topics(query)
    if topics:
        items = [
            item
            for item in items
            if _overview_item_matches_topic(item[0], item[1], item[2], topics)
        ]
    if not items:
        return None

    lines = ["Hiện hệ thống đang có các nhóm chính sách liên quan như sau:"]
    for code, title, category, _ in items[:12]:
        detail = f" ({category})" if category else ""
        lines.append(f"- {code}: {title}{detail}.")
    lines.extend(
        [
            "",
            "Bạn có thể hỏi cụ thể hơn về từng nhóm, ví dụ nghỉ phép, nghỉ ốm, bảo hiểm, chấm công, đào tạo, lương thưởng hoặc nghỉ việc.",
        ]
    )
    return "\n".join(lines)


def _new_employee_answer(query: str, chunks: list[dict]) -> str | None:
    if not _is_new_employee_query(query):
        return None

    if _is_vingroup_query(query) and any(_is_vingroup_chunk(chunk) for chunk in chunks):
        return "\n".join(
            [
                "Nếu bạn đang tham khảo theo nguồn công khai của Vingroup, các ý nên nắm trước gồm:",
                "- Định hướng con người và văn hóa làm việc là phần được nhấn mạnh khá rõ.",
                "- Doanh nghiệp chú trọng đào tạo, nâng cao nghiệp vụ và phát triển năng lực nhân sự.",
                "- Nên đọc kỹ phần giá trị cốt lõi, môi trường làm việc và lưu ý về dữ liệu cá nhân.",
                "",
                "Phần nguồn công khai hiện chưa thay thế được sổ tay nhân viên nội bộ, nên các nội dung như onboarding chi tiết, lương thưởng, nghỉ phép hoặc quy trình phê duyệt vẫn nên xác nhận thêm với HR.",
            ]
        )

    policy = _chunk_with(chunks, "HR006", "Chính sách thử việc")
    insurance = _chunk_with(chunks, "HR007", "Chính sách bảo hiểm")
    benefits = _chunk_with(chunks, "HR008", "Quy trình đăng ký phúc lợi")
    training = _chunk_with(chunks, "HR009", "Chính sách đào tạo")
    support = _chunk_with(chunks, "HR010", "Quy trình phản ánh vấn đề nhân sự")
    if not any((policy, insurance, benefits, training, support)):
        return None

    return "\n".join(
        [
            "Với nhân viên mới, bạn nên ưu tiên kiểm tra các nội dung sau:",
            "- Thời gian thử việc, tiêu chí đánh giá và thời điểm thông báo kết quả.",
            "- Mốc tham gia BHXH, BHYT, BHTN và các giấy tờ cần nộp.",
            "- Điều kiện đăng ký phúc lợi như khám sức khỏe, hỗ trợ học phí, gửi xe hoặc ăn trưa nếu có áp dụng.",
            "- Các khóa đào tạo nội bộ bắt buộc theo vị trí.",
            "- Kênh liên hệ HR khi cần hỗ trợ hoặc phản ánh vấn đề phát sinh.",
            "",
            "Nếu bạn muốn, mình có thể tách riêng thành checklist hồ sơ cần chuẩn bị cho ngày nhận việc.",
        ]
    )


def _leave_policy_answer(query: str, chunks: list[dict]) -> str | None:
    if _is_vingroup_query(query):
        return None

    folded_query = _ascii_fold(query)
    folded_context = _ascii_fold("\n".join(chunk.get("content", "") for chunk in chunks))
    if "nghi phep" not in folded_query and "xin nghi" not in folded_query:
        return None
    if "nghi phep" not in folded_context and "xin nghi phep" not in folded_context:
        return None

    return "\n".join(
        [
            "Bạn có thể xin nghỉ phép theo các bước sau:",
            "- Đăng nhập HR Portal.",
            "- Chọn mục đơn từ và tạo đơn xin nghỉ phép.",
            "- Điền ngày nghỉ, lý do nghỉ và thông tin bàn giao công việc.",
            "- Gửi đơn để quản lý phê duyệt, sau đó HR sẽ xác nhận.",
            "",
            "Lưu ý: bạn nên kiểm tra thêm số ngày phép còn lại và quy định riêng của đơn vị hoặc quản lý trực tiếp trước khi gửi đơn.",
        ]
    )


def _sick_leave_answer(query: str, chunks: list[dict]) -> str | None:
    if _is_vingroup_query(query):
        return None

    folded_query = _ascii_fold(query)
    folded_context = _ascii_fold("\n".join(chunk.get("content", "") for chunk in chunks))
    sick_terms = (
        "nghi om", "om dau", "bi om", "dang om", "bi benh", "khong khoe",
        "giay to", "giay xac nhan y te", "bao hiem xa hoi",
    )
    if not any(term in folded_query for term in sick_terms):
        return None
    if "nghi om" not in folded_context and "om dau" not in folded_context:
        return None

    natural_illness_query = any(term in folded_query for term in ("bi om", "dang om", "bi benh", "khong khoe"))
    opening = (
        "Nếu bạn đang bị ốm, trước hết hãy ưu tiên sức khỏe; nếu triệu chứng nặng hoặc bất thường, bạn nên liên hệ cơ sở y tế. Về phía công việc, bạn có thể xử lý như sau:"
        if natural_illness_query
        else "Nếu nghỉ ốm từ 2 ngày liên tiếp trở lên, bạn cần chuẩn bị giấy xác nhận y tế hoặc giấy nghỉ hưởng bảo hiểm xã hội."
    )

    return "\n".join(
        [
            opening,
            "",
            "Các bước nên làm:",
            "- Báo cho quản lý trực tiếp sớm nhất có thể.",
            "- Chuẩn bị giấy tờ y tế nếu thời gian nghỉ từ 2 ngày liên tiếp trở lên.",
            "- Bổ sung hồ sơ cho HR hoặc theo quy trình nội bộ để được ghi nhận đúng chính sách.",
        ]
    )


def _resignation_policy_answer(query: str, chunks: list[dict]) -> str | None:
    if not _is_resignation_query(query):
        return None

    folded_context = _ascii_fold("\n".join(chunk.get("content", "") for chunk in chunks))
    if any(term in folded_context for term in ("nghi viec", "thoi viec", "cham dut hop dong")):
        return _generic_policy_answer(query, chunks)

    return _no_evidence_answer(
        query,
        "Hiện tài liệu HR đang có chưa mô tả đủ chính sách nghỉ việc hoặc chấm dứt hợp đồng. Để xử lý đúng, bạn nên xác nhận với HR các mục: thời hạn báo trước, quy trình bàn giao, phép năm còn lại, quyết toán lương/phụ cấp, hồ sơ BHXH/BHYT và ngày làm việc cuối cùng.",
    )


def _guardrail_answer(query: str) -> str | None:
    if _is_external_general_query(query):
        return _no_evidence_answer(
            query,
            "Câu hỏi này nằm ngoài phạm vi chính sách nhân sự nội bộ. Bạn nên dùng nguồn chuyên môn phù hợp hơn thay vì trợ lý HR.",
        )
    if _is_secret_or_access_query(query):
        return _no_evidence_answer(
            query,
            "Thông tin truy cập hoặc bảo mật không nên được suy đoán hay chia sẻ qua trợ lý HR. Bạn vui lòng liên hệ IT hoặc kênh hỗ trợ chính thức.",
        )
    if _is_medical_advice_query(query):
        return _no_evidence_answer(
            query,
            "Trợ lý HR không thay thế tư vấn y tế. Nếu bạn đang hỏi để xin nghỉ ốm, mình có thể hỗ trợ theo hướng thủ tục và giấy tờ HR.",
        )
    if _is_casual_personal_activity_query(query):
        return _no_evidence_answer(
            query,
            "Tài liệu HR hiện có không quy định chi tiết cho các tình huống sinh hoạt cá nhân ngắn. Nếu đơn vị có nội quy riêng, bạn nên hỏi quản lý trực tiếp hoặc HR.",
        )
    if _is_sensitive_decision_query(query) and not _is_resignation_query(query):
        return _no_evidence_answer(
            query,
            "Đây là tình huống nhạy cảm và cần xác minh hồ sơ cụ thể. Trợ lý không thay HR ra quyết định, nên bạn vui lòng chuyển tiếp HR hoặc quản lý có thẩm quyền.",
        )
    if _is_personal_record_query(query):
        return _no_evidence_answer(
            query,
            "Đây là thông tin nhân sự riêng của từng cá nhân. Bạn nên xem trên HR Portal hoặc liên hệ HR qua kênh chính thức.",
        )
    return None


def _pending_leave_approval_answer(query: str) -> str | None:
    if not _is_pending_leave_approval_query(query):
        return None
    return "\n".join(
        [
            "Bạn nên kiểm tra trạng thái đơn trên HR Portal trước.",
            "- Nếu đơn vẫn đang chờ duyệt, hãy nhắc quản lý trực tiếp và gửi lại thời gian nghỉ dự kiến.",
            "- Nếu sắp đến ngày nghỉ hoặc đơn bị treo bất thường, liên hệ HR để kiểm tra luồng phê duyệt.",
            "- Không nên tự nghỉ khi chưa có xác nhận, trừ tình huống khẩn cấp; khi đó cần báo quản lý ngay.",
            "",
            "Bạn muốn mình hướng dẫn cách nhắn quản lý hay kiểm tra trạng thái đơn?",
        ]
    )


def _leave_entitlement_answer(query: str, chunks: list[dict]) -> str | None:
    folded = _ascii_fold(query)
    asks_amount = any(term in folded for term in ("bao nhieu ngay", "may ngay", "so ngay phep"))
    if not asks_amount or not any(term in folded for term in ("phep nam", "ngay phep", "nghi phep")):
        return None

    for unit, _ in _evidence_units(chunks):
        folded_unit = _ascii_fold(unit)
        if "ngay nghi phep nam" in folded_unit and re.search(r"\b\d+\s+ngay\b", folded_unit):
            return "\n".join(
                [
                    unit.rstrip(" .") + ".",
                    "",
                    "Bạn muốn mình hướng dẫn thêm cách kiểm tra số ngày phép còn lại hay cách tạo đơn nghỉ?",
                ]
            )
    return None


def _payroll_issue_answer(query: str, chunks: list[dict]) -> str | None:
    folded = _ascii_fold(query)
    issue_terms = ("tinh sai", "tru sai", "tru luong", "thieu luong", "sai luong", "khau tru")
    if "luong" not in folded or not any(term in folded for term in issue_terms):
        return None

    has_policy = False
    for chunk in chunks:
        content = _ascii_fold(chunk.get("content", ""))
        if "thac mac lien quan den luong thuong" in content or "phan anh qua phong hr" in content:
            has_policy = True
            break
        if "phan anh" in content and "luong thuong" in content and any(
            channel in content for channel in ("hr portal", "phong nhan su", "quan ly truc tiep")
        ):
            has_policy = True
            break
    if not has_policy:
        return None

    return "\n".join(
        [
            "Nếu lương bị tính hoặc khấu trừ sai, bạn nên phản ánh qua phòng HR hoặc quản lý trực tiếp để được đối soát.",
            "- Ghi rõ kỳ lương và khoản đang sai: lương cơ bản, phụ cấp, OT, thuế hoặc khoản khấu trừ.",
            "- Chuẩn bị bảng lương và dữ liệu chấm công liên quan; không gửi số tài khoản hoặc thông tin nhạy cảm qua chat.",
            "- Nếu chưa được xử lý, yêu cầu HR xác nhận tình trạng và thời gian phản hồi qua kênh chính thức.",
            "",
            "Bạn đang bị sai ở khoản nào để mình giúp bạn lập checklist đối soát?",
        ]
    )


def _extractive_answer(query: str, chunks: list[dict]) -> str:
    """Fallback answer when the LLM layer is unavailable or skipped."""
    refusal = _refuse_irrelevant_query(query)
    if refusal:
        return refusal

    if _needs_more_information(query):
        return _clarification_answer(query)

    guardrail = _guardrail_answer(query)
    if guardrail:
        return guardrail

    pending_approval = _pending_leave_approval_answer(query)
    if pending_approval:
        return pending_approval

    if not chunks:
        if _is_resignation_query(query):
            return _no_evidence_answer(
                query,
                "Mình hiểu bạn đang quan tâm đến thủ tục nghỉ việc hoặc chấm dứt hợp đồng. Hiện tại trong tài liệu chính sách của mình chưa có chi tiết cụ thể cho phần này. Để đảm bảo quyền lợi tốt nhất, bạn giúp mình xác nhận trực tiếp với bộ phận HR hoặc Quản lý trực tiếp về các thông tin như: thời hạn báo trước (30 hay 45 ngày), quy trình bàn giao công việc, cách tính số ngày phép năm còn lại để được thanh toán, và các hồ sơ chốt sổ BHXH/BHYT nhé. Mình có thể hỗ trợ kết nối bạn với HR nếu bạn cần nha!",
            )
        return _no_evidence_answer(
            query,
            "Mình hiện chưa tìm thấy tài liệu chính sách phù hợp để giải đáp chính xác câu hỏi này của bạn. Thông thường, các trường hợp này sẽ cần kiểm tra trực tiếp dựa trên hồ sơ cá nhân hoặc quy chế riêng của từng phòng ban. Bạn có muốn mình tạo một yêu cầu hỗ trợ gửi đến bộ phận HR để các anh chị liên hệ giải quyết trực tiếp cho bạn không?",
        )

    domain_answer = (
        _leave_entitlement_answer(query, chunks)
        or _payroll_issue_answer(query, chunks)
        or _new_employee_answer(query, chunks)
        or _policy_overview_answer(query, chunks)
        or _sick_leave_answer(query, chunks)
        or _leave_policy_answer(query, chunks)
        or _resignation_policy_answer(query, chunks)
    )
    if domain_answer:
        return domain_answer

    return _generic_policy_answer(query, chunks)


def generate_with_citation(
    query: str,
    top_k: int = TOP_K,
    api_key_override: str | None = None,
    score_threshold: float = 0.3,
    use_reranking: bool = True,
    user_context: dict | None = None,
) -> dict:
    """Run the HR policy graph workflow and return the API response shape."""
    from .hr_policy_graph import run_hr_policy_graph

    result = run_hr_policy_graph(
        query,
        top_k=top_k,
        api_key_override=api_key_override,
        score_threshold=score_threshold,
        use_reranking=use_reranking,
        user_context=user_context,
    )
    return {
        "answer": result.get("answer", ""),
        "sources": result.get("sources", []),
        "retrieval_source": result.get("retrieval_source", "none"),
        "context": result.get("context"),
        "graph_steps": result.get("graph_steps", []),
    }


if __name__ == "__main__":
    sample = "Tôi muốn xin nghỉ phép 2 ngày thì cần làm thủ tục gì?"
    result = generate_with_citation(sample)
    print(result["answer"])
    print(f"\n[Sources: {len(result['sources'])} chunks | via {result['retrieval_source']}]")
