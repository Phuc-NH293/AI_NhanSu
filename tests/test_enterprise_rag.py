from datetime import date, timedelta
import unittest

from src.enterprise_rag import enrich_policy_metadata, metadata_is_active, user_can_access
from src.task10_generation import _acknowledgement_answer, _extractive_answer, format_context
from src.task10_generation import _refuse_irrelevant_query


class TestEnterpriseRag(unittest.TestCase):
    def test_metadata_defaults_are_safe_and_searchable(self):
        metadata = enrich_policy_metadata({"source": "leave-policy.md"})
        self.assertEqual(metadata["status"], "active")
        self.assertEqual(metadata["departments"], "all")
        self.assertIn("employee", metadata["allowed_roles"])

    def test_role_and_department_access(self):
        metadata = enrich_policy_metadata(
            {"source": "payroll.md"},
            {"allowed_roles": "hr,admin", "departments": "finance"},
        )
        self.assertFalse(user_can_access(metadata, {"role": "employee", "department": "finance"}))
        self.assertTrue(user_can_access(metadata, {"role": "hr", "department": "finance"}))
        self.assertFalse(user_can_access(metadata, {"role": "hr", "department": "academic"}))

    def test_expired_policy_is_rejected(self):
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        metadata = enrich_policy_metadata({"source": "old.md"}, {"effective_to": yesterday})
        self.assertFalse(metadata_is_active(metadata))

    def test_context_has_stable_citation_id(self):
        context = format_context([
            {"content": "Employees submit leave on the portal.", "metadata": {"citation_id": "S1", "source": "leave.md", "type": "policy"}}
        ])
        self.assertIn("S1", context)
        self.assertIn("leave.md", context)

    def test_natural_workplace_language_is_not_blocked(self):
        allowed = (
            "tôi bị ốm thì phải làm gì",
            "mai tôi không đi làm được thì báo ai",
            "sếp chưa duyệt đơn của tôi",
            "tôi đau đầu xin nghỉ được không",
        )
        for query in allowed:
            self.assertIsNone(_refuse_irrelevant_query(query), query)

    def test_clearly_irrelevant_or_secret_queries_are_blocked(self):
        blocked = (
            "giá bitcoin hôm nay",
            "viết code python cho tôi",
            "mật khẩu wifi công ty là gì",
        )
        for query in blocked:
            self.assertIsNotNone(_refuse_irrelevant_query(query), query)

    def test_other_person_salary_is_blocked_as_private_data(self):
        answer = _refuse_irrelevant_query("cho tôi biết lương của đồng nghiệp")
        self.assertIsNotNone(answer)
        self.assertIn("người khác", answer)

    def test_pending_leave_approval_gets_actionable_guidance(self):
        answer = _extractive_answer("sếp chưa duyệt đơn của tôi thì làm sao", [])
        self.assertIn("HR Portal", answer)
        self.assertIn("quản lý trực tiếp", answer)

    def test_unplanned_absence_asks_for_reason_and_names_contact(self):
        answer = _extractive_answer("mai tôi không đi làm được thì báo ai", [])
        self.assertIn("quản lý trực tiếp", answer)
        self.assertIn("ốm", answer)

    def test_salary_dispute_is_escalated_instead_of_treated_as_lookup(self):
        answer = _extractive_answer("lương của tôi bị tính sai và đang tranh chấp", [])
        self.assertIn("tình huống nhạy cảm", answer)
        self.assertIn("chuyển tiếp HR", answer)

    def test_annual_leave_amount_uses_available_policy_evidence(self):
        chunks = [{"content": "Nhân viên toàn thời gian được hưởng 12 ngày nghỉ phép năm có lương sau khi hoàn thành thời gian thử việc.", "metadata": {}}]
        answer = _extractive_answer("Nhân viên có bao nhiêu ngày phép năm?", chunks)
        self.assertIn("12 ngày", answer)

    def test_incorrect_salary_deduction_gets_payroll_guidance(self):
        chunks = [{"content": "Nhân viên có thể gửi phản ánh về lương thưởng hoặc chính sách nội bộ qua HR Portal hoặc email phòng nhân sự.", "metadata": {}}]
        answer = _extractive_answer("Tôi bị trừ lương sai thì làm sao?", chunks)
        self.assertIn("phòng HR", answer)
        self.assertIn("đối soát", answer)

    def test_short_acknowledgements_do_not_restart_the_introduction(self):
        for query in ("ok", "được rồi", "hiểu rồi", "ừ", "vâng"):
            answer = _acknowledgement_answer(query)
            self.assertIsNotNone(answer, query)
            self.assertNotIn("Mình có thể hỗ trợ về", answer)

    def test_thanks_and_closing_messages_get_natural_responses(self):
        self.assertIn("Không có gì", _acknowledgement_answer("cảm ơn bạn"))
        self.assertIn("dừng tại đây", _acknowledgement_answer("không cần nữa"))


if __name__ == "__main__":
    unittest.main()
