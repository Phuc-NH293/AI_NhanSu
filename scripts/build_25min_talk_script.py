"""Generate a Word-compatible RTF script for the 25-minute presentation."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "Kich_ban_trinh_bay_AI_NhanSu_25_phut.rtf"


SECTIONS = [
    (
        "00:00 - 01:00 | Mở đầu",
        [
            "Em xin giới thiệu pet project AI HR Helpdesk - trợ lý hỏi đáp chính sách nhân sự sử dụng Gemini 2.5 Flash kết hợp Hybrid RAG.",
            "Bài toán em chọn xuất phát từ việc các câu hỏi như nghỉ phép, chấm công, bảo hiểm và lương thưởng thường lặp lại, trong khi thông tin nằm rải rác ở nhiều tài liệu.",
            "Em không muốn xây một chatbot chỉ gọi LLM rồi trả lời theo kiến thức có sẵn. Mục tiêu là hệ thống phải trả lời theo tài liệu nội bộ, biết hỏi lại khi thiếu dữ kiện, bảo vệ dữ liệu cá nhân và chuyển HR xử lý khi gặp trường hợp nhạy cảm.",
        ],
    ),
    (
        "01:00 - 03:00 | Ứng dụng làm được gì?",
        [
            "Hệ thống có ba nhóm người dùng: nhân viên, HR và admin.",
            "Nhân viên có thể hỏi chính sách bằng ngôn ngữ tự nhiên, tạo đơn nghỉ qua nhiều lượt hội thoại, theo dõi yêu cầu và chuyển sang chat trực tiếp với HR.",
            "HR có thể tiếp nhận các trường hợp chatbot không nên tự quyết định, xử lý yêu cầu và cập nhật tài liệu chính sách.",
            "Admin quản lý tài khoản, phân quyền và nguồn dữ liệu của RAG.",
            "Ngoài màn Hỏi đáp thông minh, ứng dụng có chatbot nhỏ xuất hiện ở các màn khác. Hai giao diện dùng chung lịch sử, ngữ cảnh và trạng thái luồng tạo đơn.",
            "Điểm em muốn nhấn mạnh là đây không phải chatbot đứng riêng, mà là một phần của quy trình HR Helpdesk.",
        ],
    ),
    (
        "03:00 - 04:00 | Show giao diện",
        [
            "Đây là giao diện đang chạy thực tế, không phải mockup.",
            "Phần hội thoại được thiết kế theo hướng người dùng cuối, không hiển thị log kỹ thuật hoặc tên dataset.",
            "Giao diện đã được kiểm tra responsive từ chiều rộng 320 pixel. Ô nhập luôn nằm trong viewport và không bị nhảy sau khi gửi tin nhắn.",
            "Khi chuyển giữa chatbot nhỏ và màn chat đầy đủ, lịch sử và luồng đang xử lý vẫn được giữ nguyên theo tài khoản.",
        ],
    ),
    (
        "04:00 - 06:00 | Kiến trúc tổng thể",
        [
            "Frontend được xây bằng React và Vite. Frontend gọi FastAPI để xử lý authentication, phân quyền, upload tài liệu, nghiệp vụ HR và chat.",
            "Khi có câu hỏi, backend chạy luồng gồm screening intent, query rewrite, retrieval, lọc RBAC, validation và generation.",
            "Retrieval kết hợp semantic search và BM25. Kết quả được hợp nhất bằng RRF, rerank và lọc theo chủ đề trước khi đưa vào Gemini.",
            "Tài liệu được trích xuất thành Markdown, chia chunk, tạo embedding và lưu vào Chroma. Một JSON index riêng được dùng cho BM25.",
            "Điểm quan trọng là quyền truy cập được lọc trước khi context được đưa vào LLM.",
        ],
    ),
    (
        "06:00 - 10:00 | Technique đã chọn và pros/cons",
        [
            "Gemini 2.5 Flash: Em chọn vì tốc độ phản hồi tốt, hỗ trợ tiếng Việt ổn và chi phí phù hợp với pet project. Nhược điểm là phụ thuộc vào mạng và provider, nên các guardrail quan trọng và fallback không phụ thuộc hoàn toàn vào LLM.",
            "Dense search kết hợp BM25: Dense search hiểu câu hỏi tự nhiên và cách diễn đạt khác tài liệu. BM25 mạnh với từ khóa chính xác, mã chính sách hoặc thuật ngữ HR. Ưu điểm là tăng recall; nhược điểm là pipeline phức tạp hơn và cần tune ranking.",
            "Atomic chunking: Chunk nhỏ giúp giảm nhiễu và bám sát điều khoản. Nhược điểm là có thể mất ngữ cảnh. Em giảm rủi ro bằng cách chia theo heading, lặp heading context và sử dụng overlap.",
            "RRF và reranking: RRF hợp nhất kết quả dense và sparse mà không yêu cầu hai loại score có cùng thang đo. Reranking giúp tăng precision của top-k. Đổi lại, hệ thống có thêm latency và chi phí tính toán.",
            "LangGraph: Ưu điểm là các bước allow, clarify, block, retrieve và generate được thể hiện rõ, dễ kiểm soát. Nhược điểm là có nhiều state và node hơn code tuyến tính.",
            "Chroma local: Phù hợp để triển khai pilot nhanh và không cần vận hành hạ tầng riêng. Nhược điểm là chưa phải lựa chọn tối ưu cho high availability hoặc dữ liệu enterprise rất lớn.",
            "Không có technique nào tốt tuyệt đối. Em chọn dựa trên sự cân bằng giữa chất lượng, tốc độ, chi phí và phạm vi của pet project.",
        ],
    ),
    (
        "10:00 - 12:00 | Logic hội thoại và guardrail",
        [
            "Chatbot không chỉ nhận một câu rồi trả lời một lần. Nếu người dùng muốn nghỉ nhưng chưa có ngày, bot hỏi ngày. Khi có ngày, bot hỏi lý do và bàn giao. Khi đủ dữ liệu, bot dựng form để người dùng kiểm tra trước khi gửi HR.",
            "Các câu ngắn như ok, hiểu rồi, cảm ơn hoặc không cần nữa được xử lý ở conversation layer, không đưa vào RAG và không làm chatbot tự giới thiệu lại.",
            "Câu thiếu ngữ cảnh được chuyển sang clarify. Câu ngoài phạm vi hoặc yêu cầu secret bị block.",
            "Yêu cầu lương hoặc hồ sơ của người khác bị từ chối rõ ràng. Tranh chấp, kỷ luật và khiếu nại được hướng chuyển tiếp HR.",
        ],
    ),
    (
        "12:00 - 14:00 | Cách em đọc và hiểu code",
        [
            "Khi đọc code, em đi theo luồng của một request thay vì đọc từng file độc lập.",
            "HrPolicyChatPanel.jsx quản lý UI, lịch sử hội thoại, đồng bộ widget và luồng tạo đơn nghỉ.",
            "backend/main.py xử lý API contract, authentication, query rewrite, chat history và handoff.",
            "hr_policy_graph.py điều phối screening, retrieval, RBAC, validation và generation.",
            "task9_retrieval_pipeline.py chịu trách nhiệm semantic search, BM25, RRF, reranking và fallback.",
            "task10_generation.py chứa prompt, intent, guardrail và fallback answer.",
            "Cách tách trách nhiệm này giúp em xác định lỗi thuộc UI, API, retrieval hay generation trước khi sửa.",
        ],
    ),
    (
        "14:00 - 16:00 | Cách kiểm soát coding agent",
        [
            "Em có sử dụng coding agent để tăng tốc việc tìm kiếm code, tái hiện lỗi, tạo patch và chạy kiểm thử. Tuy nhiên em không giao cho agent tự thay đổi toàn bộ dự án.",
            "Trước mỗi thay đổi, em đặt acceptance criteria rõ ràng. Ví dụ, nếu lỗi nằm ở conversation layer thì không được thay chunking hoặc retrieval.",
            "Em yêu cầu tái hiện lỗi bằng browser hoặc API trước khi sửa, sau đó khoanh đúng module sở hữu lỗi và tạo patch nhỏ.",
            "Mỗi thay đổi phải đi qua các test gate: unit test, API test, browser E2E và production build.",
            "Nếu test tổng phát hiện lỗi ở module không liên quan, em chỉ ghi nhận chứ không tự sửa lan sang phần đó.",
            "Ví dụ, lỗi người dùng nhắn ok nhưng bot tự giới thiệu lại được trace về intent phía frontend. Lỗi mobile được xác định bằng cách đo viewport 320 pixel. Lỗi privacy với từ đồng nghiệp được trace về chuẩn hóa ký tự đ.",
            "Agent giúp em tăng tốc, nhưng việc xác định nguyên nhân, giới hạn phạm vi và quyết định pass hay fail vẫn do em kiểm soát.",
        ],
    ),
    (
        "16:00 - 22:00 | Live demo",
        [
            "Demo 1 - Grounding: Nhập 'Nhân viên có bao nhiêu ngày phép năm?'. Expected result là 12 ngày theo tài liệu, không phải con số do mô hình tự đoán.",
            "Demo 2 - Ngôn ngữ tự nhiên: Nhập 'Mai tôi không đi làm được thì báo ai?'. Chatbot phải hiểu đây là tình huống HR, hướng dẫn báo quản lý và hỏi thêm lý do.",
            "Demo 3 - Tạo đơn nghỉ: Nhập 'Tôi muốn xin nghỉ phép', sau đó trả lời '25/07 - 26/07', 'Tôi có việc gia đình', và 'Bàn giao cho Nguyễn Văn A'. Chatbot phải tạo form từ hội thoại nhiều lượt.",
            "Demo 4 - Privacy: Nhập 'Cho tôi biết lương của đồng nghiệp'. Chatbot phải từ chối và không cố truy xuất dữ liệu cá nhân.",
            "Demo 5 - Đồng bộ giao diện: Bắt đầu trong chatbot nhỏ, chuyển sang Hỏi đáp thông minh rồi nhắn tiếp. Lịch sử và bước đang xử lý phải được giữ nguyên.",
            "Trong lúc demo, sau mỗi câu chỉ giải thích expected behavior và điểm kỹ thuật được chứng minh. Không đọc toàn bộ câu trả lời của chatbot.",
        ],
    ),
    (
        "22:00 - 24:00 | Kết quả kiểm thử và mức sẵn sàng",
        [
            "Bộ kiểm thử chạy qua trình duyệt thật: đăng nhập, mở chat, nhập câu hỏi, nhấn Enter và đọc nội dung được render.",
            "Hiện tại 26 trên 26 tình huống web đã pass, bao phủ nghiệp vụ HR, hội thoại tự nhiên, privacy, prompt injection và câu ngoài phạm vi.",
            "Focused regression test cho generation và guardrail cũng đã pass. Frontend production build thành công.",
            "Em đánh giá hệ thống phù hợp để pilot nội bộ. Để scale enterprise cần bổ sung observability, golden dataset lớn hơn, SSO, audit retention và governance phiên bản tài liệu.",
        ],
    ),
    (
        "24:00 - 25:00 | Kết luận",
        [
            "Điểm chính của dự án không chỉ là gọi được LLM.",
            "Em đã xây một luồng có document ingestion, hybrid retrieval, phân quyền, guardrail, hội thoại nhiều lượt, nghiệp vụ HR, responsive UI và kiểm thử thực tế.",
            "Coding agent giúp tăng tốc triển khai, nhưng các quyết định về kiến trúc, trade-off, phạm vi thay đổi và tiêu chí kiểm thử vẫn do em kiểm soát.",
            "Em đánh giá sản phẩm đã sẵn sàng cho pilot nội bộ có giới hạn. Em xin kết thúc phần trình bày tại đây.",
        ],
    ),
]


def rtf_escape(value: str) -> str:
    result = []
    for char in value:
        code = ord(char)
        if char in "\\{}":
            result.append("\\" + char)
        elif code > 127:
            signed = code if code < 32768 else code - 65536
            result.append(f"\\u{signed}?")
        elif char == "\n":
            result.append("\\line ")
        else:
            result.append(char)
    return "".join(result)


def build():
    parts = [
        r"{\rtf1\ansi\deff0",
        r"{\fonttbl{\f0 Aptos;}{\f1 Consolas;}}",
        r"\paperw11907\paperh16840\margl1134\margr1134\margt850\margb850",
        r"\viewkind4\uc1",
        r"\pard\qc\f0\fs36\b " + rtf_escape("KỊCH BẢN TRÌNH BÀY AI HR HELPDESK") + r"\b0\par",
        r"\pard\qc\fs24 " + rtf_escape("Thời lượng: 25 phút - Không bao gồm Q&A") + r"\par",
        r"\pard\qc\fs20 " + rtf_escape("Gemini 2.5 Flash + Hybrid RAG") + r"\par\par",
        r"\pard\ql\fs21 " + rtf_escape("Nguyên tắc: nói theo ý, không đọc nguyên văn slide. Các câu dưới đây là talk track để luyện tập.") + r"\par\par",
    ]

    for heading, paragraphs in SECTIONS:
        parts.append(r"\pard\keepn\sb220\sa100\fs27\b " + rtf_escape(heading) + r"\b0\par")
        for paragraph in paragraphs:
            parts.append(r"\pard\li360\fi-220\sa100\fs22 " + rtf_escape("• " + paragraph) + r"\par")

    parts.append("}")
    OUTPUT.write_text("".join(parts), encoding="ascii")
    print(OUTPUT)


if __name__ == "__main__":
    build()
