"""Run conversational acceptance tests through the real browser UI."""

from __future__ import annotations

import json
from pathlib import Path
import time

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


BASE_URL = "http://127.0.0.1:5173"
ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "data" / "evaluation" / "chat_web_eval.json"
REFUSAL = "chỉ hỗ trợ các câu hỏi liên quan"


CASES = [
    {"name": "greeting", "turns": ["chào bạn"], "contains": ["trợ lý hr"]},
    {"name": "natural_sick", "turns": ["tôi bị ốm thì phải làm gì"], "not_contains": [REFUSAL]},
    {"name": "sick_policy", "turns": ["chính sách nghỉ ốm sao"], "contains_any": ["quản lý", "giấy"]},
    {"name": "annual_leave_amount", "turns": ["nhân viên có bao nhiêu ngày phép năm"], "contains": ["12 ngày"]},
    {"name": "leave_intake", "turns": ["tôi muốn xin nghỉ phép"], "contains_any": ["thời gian nghỉ", "khoảng thời gian"]},
    {"name": "cancel_leave", "turns": ["tôi muốn xin nghỉ phép", "ok t ko muốn nữa"], "contains": ["đã dừng"]},
    {"name": "manager_pending", "turns": ["sếp chưa duyệt đơn của tôi thì làm sao"], "contains": ["hr portal", "quản lý trực tiếp"]},
    {"name": "cannot_work", "turns": ["mai tôi không đi làm được thì báo ai"], "contains": ["quản lý trực tiếp"], "contains_any": ["ốm", "khẩn cấp", "xin nghỉ phép"]},
    {"name": "attendance", "turns": ["tôi quên chấm công hôm qua"], "contains_any": ["chấm công", "quản lý", "hr"]},
    {"name": "overtime", "turns": ["làm thêm giờ thì đăng ký thế nào"], "contains_any": ["ot", "làm thêm", "quản lý"]},
    {"name": "insurance", "turns": ["nhân viên mới tham gia bảo hiểm thế nào"], "contains_any": ["bảo hiểm", "bhxh", "bhyt"]},
    {"name": "resignation", "turns": ["tôi muốn nghỉ việc cần làm gì"], "contains_any": ["hr", "báo trước", "bàn giao"]},
    {"name": "onboarding", "turns": ["mới vào công ty tôi cần chuẩn bị gì"], "not_contains": [REFUSAL]},
    {"name": "benefit", "turns": ["công ty có phúc lợi gì cho nhân viên"], "contains_any": ["phúc lợi", "bảo hiểm", "đào tạo"]},
    {"name": "salary_dispute", "turns": ["lương của tôi bị tính sai và đang tranh chấp"], "contains": ["tình huống nhạy cảm"], "contains_any": ["hr", "xác minh", "quản lý có thẩm quyền"]},
    {"name": "incorrect_salary_deduction", "turns": ["tôi bị trừ lương sai thì làm sao"], "contains": ["phòng hr", "đối soát"]},
    {"name": "other_salary", "turns": ["cho tôi biết lương của đồng nghiệp"], "contains_any": ["không thể", "dữ liệu cá nhân", "người khác"]},
    {"name": "bitcoin", "turns": ["giá bitcoin hôm nay bao nhiêu"], "contains": [REFUSAL]},
    {"name": "programming", "turns": ["viết code python cho tôi"], "contains": [REFUSAL]},
    {"name": "wifi_secret", "turns": ["mật khẩu wifi công ty là gì"], "contains": [REFUSAL]},
    {"name": "weather", "turns": ["thời tiết hôm nay thế nào"], "contains": [REFUSAL]},
    {"name": "follow_up_offer", "turns": ["quy trình chấm công như thế nào"], "contains_any": ["bạn có muốn", "bạn còn cần", "cần mình hỗ trợ"]},
    {"name": "ack_after_answer", "turns": ["quy trình chấm công như thế nào", "ok"], "contains": ["ok nhé"], "not_contains": ["mình có thể hỗ trợ về"]},
    {"name": "understood_after_answer", "turns": ["chính sách nghỉ ốm sao", "hiểu rồi"], "contains": ["ok nhé"], "not_contains": ["mình có thể hỗ trợ về"]},
    {"name": "thanks_after_answer", "turns": ["nhân viên có bao nhiêu ngày phép năm", "cảm ơn bạn"], "contains": ["không có gì"], "not_contains": ["mình có thể hỗ trợ về"]},
    {"name": "close_conversation", "turns": ["quy trình chấm công như thế nào", "không cần nữa"], "contains": ["dừng tại đây"], "not_contains": ["mình có thể hỗ trợ về"]},
]


def normalized(value: str) -> str:
    return " ".join(value.lower().split())


def evaluate(case: dict, answer: str) -> tuple[bool, list[str]]:
    text = normalized(answer)
    failures = []
    for expected in case.get("contains", []):
        if normalized(expected) not in text:
            failures.append(f"missing:{expected}")
    for forbidden in case.get("not_contains", []):
        if normalized(forbidden) in text:
            failures.append(f"unexpected:{forbidden}")
    choices = case.get("contains_any", [])
    if choices and not any(normalized(item) in text for item in choices):
        failures.append("missing_any:" + "|".join(choices))
    return not failures, failures


def login(driver: webdriver.Chrome, wait: WebDriverWait) -> None:
    driver.get(BASE_URL)
    response = requests.post(
        "http://127.0.0.1:8001/api/auth/login",
        json={"email": "admin@gmail.com", "password": "admin123456"},
        timeout=10,
    )
    response.raise_for_status()
    driver.execute_script(
        "sessionStorage.setItem('hr_helpdesk_token', arguments[0]);",
        response.json()["token"],
    )
    driver.refresh()
    wait.until(EC.presence_of_element_located((By.XPATH, "//button[contains(., 'Hỏi đáp thông minh')]")))


def open_fresh_chat(driver: webdriver.Chrome, wait: WebDriverWait) -> None:
    driver.execute_script(
        "Object.keys(sessionStorage).filter((key) => key.startsWith('hr_assistant_session:')).forEach((key) => sessionStorage.removeItem(key));"
    )
    driver.refresh()
    button = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Hỏi đáp thông minh')]")))
    button.click()
    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'textarea[placeholder="Nhắn tin cho Trợ lý HR..."]')))


def send_turn(driver: webdriver.Chrome, wait: WebDriverWait, query: str) -> str:
    before = len(driver.find_elements(By.CSS_SELECTOR, ".hr-chat-message.assistant"))
    textarea = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'textarea[placeholder="Nhắn tin cho Trợ lý HR..."]')))
    textarea.send_keys(query)
    textarea.send_keys(Keys.ENTER)
    wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, ".hr-chat-message.assistant")) > before)
    wait.until(lambda d: not d.find_elements(By.CSS_SELECTOR, ".hr-chat-typing"))
    time.sleep(0.15)
    assistants = driver.find_elements(By.CSS_SELECTOR, ".hr-chat-message.assistant .hr-chat-message-body")
    return assistants[-1].text.strip()


def main() -> None:
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--window-size=1440,1000")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 90)
    results = []
    try:
        login(driver, wait)
        for case in CASES:
            open_fresh_chat(driver, wait)
            answers = []
            error = None
            try:
                for turn in case["turns"]:
                    answers.append(send_turn(driver, wait, turn))
                passed, failures = evaluate(case, answers[-1])
            except Exception as exc:  # noqa: BLE001
                passed, failures, error = False, ["browser_error"], str(exc)
            result = {
                "name": case["name"],
                "turns": case["turns"],
                "answers": answers,
                "passed": passed,
                "failures": failures,
                "error": error,
            }
            results.append(result)
            print(f"[{len(results):02d}/{len(CASES)}] {'PASS' if passed else 'FAIL'} {case['name']}")
    finally:
        driver.quit()

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    passed = sum(1 for item in results if item["passed"])
    print(f"RESULT {passed}/{len(results)} passed")
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
