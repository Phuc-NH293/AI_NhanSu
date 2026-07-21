# BÁO CÁO KỸ THUẬT & QUY TRÌNH ĐIỀU PHỐI AGENT

Dự án **University Admin - HR Helpdesk** giải quyết bài toán hỏi đáp chính sách nhân sự tự động sử dụng kiến trúc RAG nâng cao kết hợp Guardrails an toàn thông tin doanh nghiệp.

## 1. Các Kỹ thuật cốt lõi (Core Techniques) & Phân tích Pros/Cons

### Kỹ thuật 1: LangGraph Orchestration (Điều phối Luồng bằng Đồ thị Trạng thái)
*   **Mô tả:** Thay vì sử dụng luồng tuần tự (Sequential Chain) thông thường, chatbot sử dụng đồ thị trạng thái LangGraph để đi qua các Node: `screen_request` -> `retrieve` -> `filter_context` -> `prepare` -> `generate` -> `finalize`.
*   **Pros (Ưu điểm):**
    *   Kiểm soát chặt chẽ đường đi của dữ liệu.
    *   Dễ dàng rẽ nhánh: Nếu phát hiện câu hỏi ngoài phạm vi ở bước `screen_request`, hệ thống nhảy thẳng đến `finalize` để từ chối mà không tốn chi phí gọi Retrieval hay sinh văn bản.
    *   Theo dõi vết (Tracing/Logs) từng bước chạy trực quan.
*   **Cons (Nhược điểm):** Độ phức tạp mã nguồn tăng lên, khó debug hơn đối với người mới tiếp cận so với LangChain chain truyền thống.

### Kỹ thuật 2: Hybrid Search (Lexical BM25 + Semantic Vector Search)
*   **Mô tả:** Kết hợp tìm kiếm từ khóa chính xác (BM25) và tìm kiếm ngữ nghĩa (Embedding).
*   **Pros:** Đảm bảo không bỏ sót các thuật ngữ chuyên ngành HR viết tắt (như "OT", "BHXH", "KPI") đồng thời vẫn hiểu được các câu hỏi diễn đạt tự nhiên có cùng ý nghĩa.
*   **Cons:** Yêu cầu tài nguyên tính toán gấp đôi và cần thuật toán chuẩn hóa/Reranking (như Cross-Encoder) để chấm điểm và hợp nhất kết quả của hai phương pháp.

### Kỹ thuật 3: Input/Output Guardrails (Lớp phòng vệ nội dung) kết hợp Trả lời Thân thiện
*   **Mô tả:** Bộ lọc phân loại câu hỏi (classifier) tại Node đầu vào và kiểm tra đối chiếu bằng chứng chứng cứ (evidence checking) trước khi trả về câu trả lời. Nếu LLM trả lời mà không tìm thấy văn bản trích dẫn nguồn cụ thể trong Context, hệ thống sẽ tự động chuyển sang chế độ từ chối hoặc chuyển tiếp HR.
*   **Pros:** Triệt tiêu hoàn toàn hiện tượng ảo giác (Hallucination) - lỗi chí mạng của AI trong môi trường doanh nghiệp pháp lý/nhân sự.
*   **Cons ban đầu:** Dễ làm AI trở nên quá "cứng nhắc" và lạnh lùng, từ chối cả những câu hỏi vô hại hoặc thông dụng nếu tài liệu nạp vào chưa phong phú.
*   **Giải pháp Thân thiện hóa (Friendly Fallback):** Khi kích hoạt Guardrail từ chối (do thiếu evidence), thay vì trả về một câu từ chối máy móc cụ thể ("Tôi không thể trả lời"), AI sẽ chuyển sang đóng vai trò một người hỗ trợ tận tâm: 
    *   Xác nhận rõ ràng chủ đề người dùng đang hỏi (ví dụ: "Mình hiểu bạn đang hỏi về thủ tục xin nghỉ việc").
    *   Định hướng chi tiết những thông tin/giấy tờ cần chuẩn bị (ví dụ: "Thông thường bạn sẽ cần chuẩn bị đơn bàn giao công việc trước 30-45 ngày tùy loại hợp đồng").
    *   Chủ động đề xuất các bước liên hệ nhân sự phụ trách hoặc đính kèm form liên quan để giải quyết nhanh nhất, giúp trải nghiệm người dùng luôn mượt mà và cảm thấy được lắng nghe.

---

## 2. Quy trình Điều phối & Kiểm soát Coding Agent

Là kỹ sư giám sát và điều phối, em áp dụng các nguyên tắc sau để kiểm soát Coding Agent (như Gemini/Cursor/GitHub Copilot):

1. **Nguyên tắc Chia nhỏ tác vụ (Task Isolation):** Không bao giờ để Agent viết cả file API nghìn dòng một lúc. Em yêu cầu viết riêng biệt các module:
    *   Module kết nối LLM: `src/llm_provider.py`
    *   Module xử lý Graph: `src/hr_policy_graph.py`
    *   Tách biệt API Routing: `backend/main.py`
2. **Review qua Lớp kiểm thử (TDD - Test Driven Development):** Agent chỉ được coi là hoàn thành khi các test case trong thư mục `tests` chạy thành công.
3. **Kiểm soát Prompting và Context Boundary:** Giới hạn tầm nhìn của Agent vào đúng file cần sửa, tránh tình trạng Agent tự ý sửa đổi code của các file khác gây lỗi dây chuyền (Cascade errors).
