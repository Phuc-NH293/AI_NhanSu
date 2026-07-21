"""LangGraph orchestration for the HR policy RAG assistant."""

from __future__ import annotations

from typing import Any, TypedDict

from .enterprise_rag import user_can_access
from .llm_provider import generate_text, get_llm_api_key
from .task9_retrieval_pipeline import retrieve
from .task10_generation import (
    SYSTEM_PROMPT,
    TEMPERATURE,
    TOP_P,
    _answer_has_no_evidence,
    _ascii_fold,
    _clarification_answer,
    _cited_chunks,
    _extractive_answer,
    _needs_more_information,
    _refuse_irrelevant_query,
    format_context,
    reorder_for_llm,
)


class HRPolicyGraphState(TypedDict, total=False):
    query: str
    top_k: int
    score_threshold: float
    use_reranking: bool
    user_context: dict[str, Any]
    api_key_override: str | None
    chunks: list[dict[str, Any]]
    reordered_chunks: list[dict[str, Any]]
    context: str
    retrieval_source: str
    answer: str
    sources: list[dict[str, Any]]
    graph_steps: list[str]


QUERY_SCREEN_PROMPT = """Bạn đang làm nhiệm vụ phân loại yêu cầu cho cổng HR nội bộ.

Chỉ cho phép các yêu cầu liên quan đến:
- chính sách nhân sự nội bộ
- nghỉ phép, nghỉ ốm, chấm công, OT
- lương thưởng, bảo hiểm, hợp đồng
- onboarding, đào tạo, phúc lợi
- phản ánh nhân sự, ứng xử, hiệu suất, công tác
- cách nói đời thường về công việc như "sếp chưa duyệt", "tôi không khỏe", "mai tôi không đi làm được", "đơn của tôi bị trả lại"

Nguyên tắc phân loại:
- Hiểu ý định thay vì đòi người dùng phải nói đúng từ khóa HR.
- Nếu câu hỏi vừa có yếu tố đời sống/sức khỏe vừa hỏi cách xử lý với công ty, quản lý, nghỉ làm hoặc giấy tờ thì vẫn là HR.
- CLARIFY thay vì BLOCK khi có khả năng liên quan công việc nhưng câu hỏi chưa đủ rõ.

Chặn các yêu cầu linh tinh hoặc ngoài phạm vi như:
- thời tiết, thể thao, tin tức, tài chính, crypto
- hỏi vui, tán gẫu, chuyện sinh hoạt cá nhân không liên quan HR
- hỏi mật khẩu, secret, token, API key
- tư vấn y tế, pháp lý ngoài phạm vi HR
- hỏi kỹ thuật, lập trình, nội dung không liên quan nhân sự

Trả lời đúng 1 từ duy nhất:
- ALLOW: câu hỏi đủ rõ và thuộc phạm vi HR
- CLARIFY: thuộc phạm vi HR nhưng thiếu dữ kiện quan trọng để trả lời an toàn
- BLOCK: ngoài phạm vi HR hoặc yêu cầu dữ liệu/hướng dẫn bị cấm"""

TOPIC_ALIASES: dict[str, tuple[str, ...]] = {
    "leave": ("nghi phep", "xin nghi", "ngay phep", "phep nam"),
    "sick_leave": (
        "nghi om", "om dau", "bi om", "dang om", "bi benh", "khong khoe",
        "giay xac nhan y te", "bao hiem xa hoi",
    ),
    "attendance": ("cham cong", "quen cham cong", "gio lam", "di muon", "tan ca"),
    "overtime": ("lam them", "ot", "overtime", "ngoai gio"),
    "payroll": ("luong", "thuong", "kpi", "luong thuong", "thu nhap"),
    "insurance": ("bao hiem", "bhxh", "bhyt", "bhtn"),
    "probation": ("thu viec", "nhan vien moi", "moi vao", "onboarding", "hoi nhap"),
    "benefits": ("phuc loi", "kham suc khoe", "hoc phi", "gui xe", "an trua", "phu cap"),
    "training": ("dao tao", "khoa hoc", "nang luc", "noi bo"),
    "support": ("phan anh", "ho tro", "khieu nai", "moi truong lam viec", "quan he lao dong"),
    "business_trip": ("cong tac", "di cong tac", "quyet toan", "chi phi"),
    "conduct": ("ung xu", "quy tac", "dao duc", "chuan muc"),
    "performance": ("hieu suat", "danh gia", "muc tieu cong viec"),
    "culture": ("van hoa", "gia tri cot loi", "tin tam tri toc tinh nhan"),
    "privacy": ("du lieu ca nhan", "bao ve du lieu", "thong tin ca nhan"),
    "vingroup": ("vingroup", "vin group", "vin "),
}


def _append_step(state: HRPolicyGraphState, step: str) -> list[str]:
    return [*state.get("graph_steps", []), step]


def _detect_topics(query: str) -> list[str]:
    folded = _ascii_fold(query)
    return [
        topic
        for topic, aliases in TOPIC_ALIASES.items()
        if any(alias in folded for alias in aliases)
    ]


def _chunk_search_text(chunk: dict[str, Any]) -> str:
    meta = chunk.get("metadata", {}) or {}
    fields = [
        chunk.get("content", ""),
        str(meta.get("source", "")),
        str(meta.get("declared_source", "")),
        str(meta.get("type", "")),
    ]
    return _ascii_fold("\n".join(fields))


def _chunk_matches_topic(chunk: dict[str, Any], topic: str) -> bool:
    text = _chunk_search_text(chunk)
    return any(alias in text for alias in TOPIC_ALIASES[topic])


def filter_relevant_policy_context(state: HRPolicyGraphState) -> HRPolicyGraphState:
    """Keep only chunks that match the user's concrete topic."""
    chunks = state.get("chunks", [])
    topics = _detect_topics(state["query"])
    if not chunks or not topics:
        return {
            "graph_steps": _append_step(state, "filter_relevant_policy_context:all"),
        }

    filtered = chunks
    if "vingroup" in topics:
        org_filtered = [chunk for chunk in filtered if _chunk_matches_topic(chunk, "vingroup")]
        if org_filtered:
            filtered = org_filtered

    concrete_topics = [topic for topic in topics if topic != "vingroup"]
    if concrete_topics:
        topic_filtered = [
            chunk
            for chunk in filtered
            if any(_chunk_matches_topic(chunk, topic) for topic in concrete_topics)
        ]
        if topic_filtered:
            filtered = topic_filtered
            if "vingroup" not in topics:
                internal_filtered = [
                    chunk
                    for chunk in filtered
                    if "public_hr_policy" not in _chunk_search_text(chunk)
                    and "vingroup" not in _chunk_search_text(chunk)
                ]
                if internal_filtered:
                    filtered = internal_filtered

    if len(filtered) == len(chunks):
        step = f"filter_relevant_policy_context:all topics={','.join(topics)}"
    else:
        step = f"filter_relevant_policy_context:{len(chunks)}->{len(filtered)} topics={','.join(topics)}"

    retrieval_source = filtered[0].get("source", "hybrid") if filtered else state.get("retrieval_source", "none")
    return {
        "chunks": filtered,
        "retrieval_source": retrieval_source,
        "graph_steps": _append_step(state, step),
    }


def retrieve_policy_context(state: HRPolicyGraphState) -> HRPolicyGraphState:
    """Retrieve candidate policy chunks."""
    top_k = int(state.get("top_k") or 5)
    chunks = retrieve(
        state["query"],
        top_k=min(20, top_k * 3),
        score_threshold=float(state.get("score_threshold", 0.3)),
        use_reranking=bool(state.get("use_reranking", True)),
    )
    retrieval_source = chunks[0].get("source", "hybrid") if chunks else "none"
    return {
        "chunks": chunks,
        "retrieval_source": retrieval_source,
        "graph_steps": _append_step(state, f"retrieve_policy_context:{len(chunks)}"),
    }


def filter_accessible_context(state: HRPolicyGraphState) -> HRPolicyGraphState:
    """Apply document lifecycle and RBAC filters before policy relevance filtering."""
    chunks = state.get("chunks", [])
    user = state.get("user_context", {})
    filtered = [chunk for chunk in chunks if user_can_access(chunk.get("metadata", {}) or {}, user)]
    top_k = int(state.get("top_k") or 5)
    return {
        "chunks": filtered[:top_k],
        "graph_steps": _append_step(state, f"filter_accessible_context:{len(chunks)}->{len(filtered[:top_k])}"),
    }


def screen_request(state: HRPolicyGraphState) -> HRPolicyGraphState:
    """Block irrelevant questions before retrieval. Prefer LLM screening when available."""
    query = state["query"].strip()
    local_refusal = _refuse_irrelevant_query(query)
    if local_refusal:
        return {
            "answer": local_refusal,
            "sources": [],
            "retrieval_source": "blocked",
            "graph_steps": _append_step(state, "screen_request:blocked_local"),
        }

    if _needs_more_information(query):
        return {
            "answer": _clarification_answer(query),
            "sources": [],
            "retrieval_source": "clarify",
            "graph_steps": _append_step(state, "screen_request:clarify_local"),
        }

    api_key = get_llm_api_key(override=state.get("api_key_override"))
    if not api_key:
        return {
            "graph_steps": _append_step(state, "screen_request:allow_no_key"),
        }

    try:
        decision = generate_text(
            system_prompt=QUERY_SCREEN_PROMPT,
            user_message=query,
            temperature=0,
            top_p=1,
            api_key_override=state.get("api_key_override"),
        ).strip().upper()
        if decision.startswith("BLOCK"):
            return {
                "answer": (
                    "Xin lỗi, mình chỉ hỗ trợ các câu hỏi liên quan đến chính sách, "
                    "quy trình và nghiệp vụ nhân sự nội bộ. Bạn vui lòng hỏi lại đúng chủ đề HR."
                ),
                "sources": [],
                "retrieval_source": "blocked",
                "graph_steps": _append_step(state, "screen_request:blocked_llm"),
            }
        if decision.startswith("CLARIFY"):
            return {
                "answer": _clarification_answer(query),
                "sources": [],
                "retrieval_source": "clarify",
                "graph_steps": _append_step(state, "screen_request:clarify_llm"),
            }
        return {
            "graph_steps": _append_step(state, "screen_request:allow_llm"),
        }
    except Exception:
        return {
            "graph_steps": _append_step(state, "screen_request:allow_on_classifier_error"),
        }


def prepare_context(state: HRPolicyGraphState) -> HRPolicyGraphState:
    """Order evidence and format it for the answer node."""
    chunks = state.get("chunks", [])
    reordered = []
    for index, chunk in enumerate(reorder_for_llm(chunks), 1):
        item = {**chunk, "metadata": {**(chunk.get("metadata", {}) or {}), "citation_id": f"S{index}"}}
        reordered.append(item)
    return {
        "reordered_chunks": reordered,
        "context": format_context(reordered),
        "graph_steps": _append_step(state, "prepare_context"),
    }


def validate_context(state: HRPolicyGraphState) -> HRPolicyGraphState:
    """Stop generation when retrieval produced no authorized evidence."""
    chunks = state.get("reordered_chunks", [])
    if chunks:
        return {"graph_steps": _append_step(state, "validate_context:passed")}
    return {
        "answer": (
            "Hiện mình chưa tìm thấy căn cứ đủ rõ trong tài liệu HR đang có và bạn được phép truy cập "
            "để trả lời chính xác câu hỏi này. Bạn vui lòng bổ sung tình huống cụ thể hoặc liên hệ HR để xác minh."
        ),
        "sources": [],
        "retrieval_source": "no_authorized_context",
        "graph_steps": _append_step(state, "validate_context:failed"),
    }


def generate_answer(state: HRPolicyGraphState) -> HRPolicyGraphState:
    """Call the configured LLM or deterministic fallback."""
    chunks = state.get("reordered_chunks", state.get("chunks", []))
    api_key = get_llm_api_key(override=state.get("api_key_override"))
    if not api_key:
        answer = _extractive_answer(state["query"], chunks)
        return {
            "answer": answer,
            "graph_steps": _append_step(state, "generate_answer:fallback_no_key"),
        }

    try:
        user_message = f"Context:\n{state.get('context', '')}\n\n---\n\nEmployee/HR request:\n{state['query']}"
        answer = generate_text(
            system_prompt=SYSTEM_PROMPT,
            user_message=user_message,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            api_key_override=state.get("api_key_override"),
        )
        step = "generate_answer:llm"
    except Exception:
        answer = _extractive_answer(state["query"], chunks)
        step = "generate_answer:fallback_llm_error"

    return {"answer": answer, "graph_steps": _append_step(state, step)}


def finalize_response(state: HRPolicyGraphState) -> HRPolicyGraphState:
    """Choose source chunks that should be returned to the API."""
    chunks = state.get("reordered_chunks", state.get("chunks", []))
    answer = state.get("answer", "")
    sources = [] if _answer_has_no_evidence(answer) else _cited_chunks(answer, chunks)
    if not sources and answer and not _answer_has_no_evidence(answer):
        sources = chunks
    return {
        "sources": sources,
        "graph_steps": _append_step(state, f"finalize_response:{len(sources)}"),
    }


def build_hr_policy_graph():
    """Build the LangGraph StateGraph used by the HR assistant."""
    from langgraph.graph import END, START, StateGraph

    def route_after_screen(state: HRPolicyGraphState) -> str:
        return "blocked" if state.get("answer") else "retrieve"

    graph = StateGraph(HRPolicyGraphState)
    graph.add_node("screen_request", screen_request)
    graph.add_node("retrieve_policy_context", retrieve_policy_context)
    graph.add_node("filter_accessible_context", filter_accessible_context)
    graph.add_node("filter_relevant_policy_context", filter_relevant_policy_context)
    graph.add_node("prepare_context", prepare_context)
    graph.add_node("validate_context", validate_context)
    graph.add_node("generate_answer", generate_answer)
    graph.add_node("finalize_response", finalize_response)

    graph.add_edge(START, "screen_request")
    graph.add_conditional_edges(
        "screen_request",
        route_after_screen,
        {
            "blocked": "finalize_response",
            "retrieve": "retrieve_policy_context",
        },
    )
    graph.add_edge("retrieve_policy_context", "filter_accessible_context")
    graph.add_edge("filter_accessible_context", "filter_relevant_policy_context")
    graph.add_edge("filter_relevant_policy_context", "prepare_context")
    graph.add_edge("prepare_context", "validate_context")
    graph.add_conditional_edges(
        "validate_context",
        lambda state: "stop" if state.get("answer") else "generate",
        {"stop": "finalize_response", "generate": "generate_answer"},
    )
    graph.add_edge("generate_answer", "finalize_response")
    graph.add_edge("finalize_response", END)
    return graph.compile()


_COMPILED_GRAPH = None


def get_hr_policy_graph():
    """Return a cached compiled LangGraph graph."""
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = build_hr_policy_graph()
    return _COMPILED_GRAPH


def run_hr_policy_graph(
    query: str,
    top_k: int = 5,
    api_key_override: str | None = None,
    score_threshold: float = 0.3,
    use_reranking: bool = True,
    user_context: dict[str, Any] | None = None,
) -> HRPolicyGraphState:
    """Invoke the HR policy LangGraph workflow."""
    graph = get_hr_policy_graph()
    return graph.invoke(
        {
            "query": query,
            "top_k": top_k,
            "score_threshold": score_threshold,
            "use_reranking": use_reranking,
            "user_context": user_context or {"role": "employee", "department": ""},
            "api_key_override": api_key_override,
            "graph_steps": [],
        }
    )
