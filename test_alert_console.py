import json
import os
import re
import tempfile
import threading
import urllib.error
import urllib.request
from pathlib import Path

# Tests must never touch the real history file.
TEST_DIR = tempfile.mkdtemp(prefix="alert_console_test_")
os.environ["VIGIL_DATA_DIR"] = TEST_DIR
os.environ["ALERT_CONSOLE_DB"] = str(Path(TEST_DIR) / "history.db")

import alert_console as app


def sample_alert():
    return json.dumps({
        "_index": "wazuh-alerts",
        "_id": "abc",
        "_source": {
            "agent": {"name": "APP-SERVER-01", "ip": "10.20.30.186"},
            "manager": {"name": "siem-manager"},
            "rule": {"id": "100402", "level": 12},
            "data": {"srcuser": "alice", "email": "alice@example.co.th"},
            "full_log": "Nov 3 edge-fw waflog: dvchost=FW-EDGE-01 deviceExternalId=A1B2C3D4E5F60718 HOST=203.0.113.50 DST=10.20.30.254:80 URL=http://198.51.100.7%2FphpMyAdmin%2Fscripts%2Fsetup.php password=SuperSecret123 C:\\Users\\alice\\app.exe"
        }
    })


def test_mask_and_restore():
    prepared, extra = app.prepare_alert(sample_alert())
    masker = app.Masker(app.load_terms() + extra)
    masked = masker.mask(prepared)
    for secret in ["APP-SERVER-01", "10.20.30.186", "siem-manager", "alice", "example.co.th", "FW-EDGE-01", "A1B2C3D4E5F60718", "203.0.113.50", "10.20.30.254", "198.51.100.7", "SuperSecret123"]:
        assert secret.casefold() not in masked.casefold(), secret
    assert "_index" not in masked
    assert "phpMyAdmin" in masked and "100402" in masked
    token = next(token for token, value in masker.token_to_value.items() if value == "10.20.30.254")
    assert masker.restore(f"เป้าหมายคือ {token}") == "เป้าหมายคือ 10.20.30.254"
    assert masker.residual(masked) == []
    assert masker.residual("10.20.30.254")


def test_stable_tokens_and_escaped_json():
    masker = app.Masker([("LEGACY-SVR1", "WIN2008R2_SERVER")])
    masked = masker.mask("LEGACY-SVR1 legacy-svr1")
    assert masked == "[WIN2008R2_SERVER_1] [WIN2008R2_SERVER_1]"
    masked = masker.mask(json.dumps({"targetUserName": 'bob"x', "full_log": "ok"}, ensure_ascii=False))
    assert "bob" not in masked and json.loads(masked)["full_log"] == "ok"


def test_value_reused_across_fields():
    prepared, extra = app.prepare_alert(json.dumps({
        "data": {"srcuser": "alice", "email": "alice@example.co.th"},
        "full_log": "login failed for alice from workstation"
    }))
    masker = app.Masker(app.load_terms() + extra)
    masked = masker.mask(prepared)
    assert "alice" not in masked.casefold() and "example" not in masked.casefold()
    later = masker.mask("Local AI says alice@example.co.th and alice are involved")
    assert "alice" not in later.casefold() and "example" not in later.casefold()


def test_instructions_hold_no_masked_values():
    for value, _kind in app.load_terms():
        assert value.casefold() not in app.SYSTEM_CLAUDE.casefold(), value
    assert not app.IPV4_RE.search(app.SYSTEM_CLAUDE)
    for field in ("source:", "defense:", "result:", "impact_data:", "severity_reason:", "business_risk:", "timeline:", "unknown:"):
        assert app.SYSTEM_CLAUDE.count(field) == 2 and app.SYSTEM_LOCAL_REPORT.count(field) == 2, field


def test_private_settings_stay_outside_the_code():
    assert app.DATA_DIR == Path(TEST_DIR)
    assert "{{ENVIRONMENT}}" not in app.claude_system()
    assert app.DEFAULT_ENVIRONMENT in app.claude_system()
    app.ENVIRONMENT_FILE.write_text("- Lab network only", encoding="utf-8")
    try:
        assert "- Lab network only" in app.claude_system() and app.DEFAULT_ENVIRONMENT not in app.claude_system()
    finally:
        app.ENVIRONMENT_FILE.unlink()
    assert app.company_logo() is None


def test_documentation_addresses_count_as_public():
    masker = app.Masker([])
    assert masker.mask("203.0.113.50 10.20.30.1") == "[PUBLIC_IP_1] [INTERNAL_IP_1]"


def test_common_word_user_does_not_block_sending():
    masker = app.Masker([])
    masked = masker.mask(json.dumps({"srcuser": "root", "decoder": "rootcheck"}))
    assert "rootcheck" in masked and "root\"" not in masked
    assert masker.residual(masked) == []
    assert masker.residual(masked + " root")


def test_history_survives_restart():
    answer_token = "[INTERNAL_IP_1]"
    preview = app.build_preview(sample_alert(), "Local saw 10.20.30.254", True)
    case_id = preview["session"]
    assert preview["saved"] is True
    app.SESSIONS.remove(case_id)  # Same state as a fresh start of the app.

    masker = app.find_masker(case_id)
    assert masker is not None
    assert app.Masker.from_map([], masker.token_to_value).restore(answer_token) == masker.token_to_value[answer_token]

    answer = "````markdown\n```summary\nseverity: high\nverdict: พบการสแกน\n```\n## 1. สรุป\nข้อความ\n````"
    app.HISTORY.save_answer(case_id, answer)
    app.HISTORY.save_checks(case_id, [0, 2])
    item = app.HISTORY.get(case_id)
    assert item["severity"] == "High" and item["verdict"] == "พบการสแกน"
    assert item["answer"] == answer and item["checks_done"] == [0, 2]
    assert "mask_map" not in item
    assert app.HISTORY.list()["cases"][0]["answered"] is True
    assert [row["id"] for row in app.HISTORY.list("203.0.113.50")["cases"]] == [case_id]
    assert app.HISTORY.list("100%_ไม่มี")["cases"] == []

    again = app.build_preview(sample_alert(), "Local saw 10.20.30.254", False, case_id)
    assert again["session"] == case_id
    assert app.HISTORY.get(case_id)["include_local"] is False
    assert app.HISTORY.get(case_id)["answer"] == answer

    app.HISTORY.delete(case_id)
    assert app.HISTORY.get(case_id) is None
    assert b"203.0.113.50" not in Path(app.HISTORY_DB).read_bytes()


def test_failed_save_does_not_stop_analysis():
    real, app.HISTORY = app.HISTORY, app.History(Path(TEST_DIR) / "missing" / "history.db")
    try:
        preview = app.build_preview(sample_alert(), "", True)
        assert preview["saved"] is False and "10.20.30.254" not in preview["preview"]
    finally:
        app.HISTORY = real


LOCAL_TEXT = """1. สรุป:
WAF บล็อกคำขอจาก 203.0.113.50 ไปยัง 10.20.30.254

4. ระดับความสำคัญ:
ระดับความสำคัญ: Medium

5. ควรตรวจอะไรต่อ:
1. ตรวจ Web Log
2. ตรวจ PHP

6. วิธีแก้ที่เป็นไปได้:
- ปิดพอร์ตที่ไม่จำเป็น"""


def test_local_report_uses_alert_facts_over_model():
    alert = json.dumps({"timestamp": "2026-11-02T08:51:03.241+0000", "data": {"waf_action": "Block"},
                        "rule": {"description": "WAF LFI"}, "full_log": "x"})
    generated = """Here is the report:
```summary
severity: high
action: Allow
event_time: 2026-11-02 22:51
verdict: พบการสแกน
```
```flow
blocked | WAF | ถูกบล็อก
```
```report-th
title: พบการสแกน
summary: ทดสอบ
```
```report-en
title: Scan found
summary: Test
```
"""
    answer = app.build_local_report(alert, LOCAL_TEXT, generated)
    assert "source: local" in answer and "event_time: 2026-11-02 15:51" in answer
    assert "22:51" not in answer and "action: Block" in answer and "severity: High" in answer
    assert "## 1. สรุป" in answer and "## 2. ระดับความสำคัญ" in answer and "## 4. วิธีแก้ที่เป็นไปได้" in answer
    assert "\n1. ตรวจ Web Log" in answer and "Here is the report" not in answer
    assert app.read_summary(answer) == ("High", "พบการสแกน")


def test_local_report_survives_bad_model_output():
    alert = "Nov 2 waflog TIME=2026-11-02 15:50:24 ACTION=Block"
    answer = app.build_local_report(alert, LOCAL_TEXT, "โมเดลตอบไม่เป็นรูปแบบ")
    assert "severity: Medium" in answer and "event_time: 2026-11-02 15:50" in answer
    assert "action: Block" in answer and "```report-th" in answer and "```flow" not in answer
    data_alert = json.dumps({"data": {"srcip": "203.0.113.50", "dstip": "10.20.30.254:80", "waf_action": "Block"}})
    filled = app.build_local_report(data_alert, LOCAL_TEXT, "")
    assert "source: IP 203.0.113.50" in filled and "defense:" in filled and "target: 10.20.30.254:80" in filled
    plain = app.build_local_report(alert, "ข้อความไม่มีหัวข้อ", "")
    assert "## ผลวิเคราะห์ Local AI" in plain


def test_english_changes_the_prompts_and_keeps_thai_as_is():
    thai = re.compile("[\u0e00-\u0e7f]")
    english = app.claude_system("en") + app.prompt_for(app.SYSTEM_LOCAL_REPORT, "en")
    assert not thai.search(english) and "Reply in English." in english
    assert "in Thai" not in english.replace("report-th in Thai", "").replace("report-th in\n  Thai", "")
    assert app.claude_system("th") == app.claude_system() and "Reply in Thai." in app.claude_system()
    assert app.prompt_for(app.SYSTEM_LOCAL_REPORT, "th") == app.SYSTEM_LOCAL_REPORT


def test_local_ai_language():
    seen = []
    real, app.chat_ollama = app.chat_ollama, lambda messages: seen.append(messages) or "ok"
    try:
        app.call_ollama("alert text")
        app.call_ollama("alert text", "en")
    finally:
        app.chat_ollama = real
    assert seen[0] == [{"role": "user", "content": "alert text"}]
    assert len(seen[1]) == 1 and seen[1][0]["role"] == "user" and "reply in English" in seen[1][0]["content"]


def test_english_local_report():
    alert = json.dumps({"_source": {"data": {"srcip": "203.0.113.50", "action": "Block"}, "rule": {"description": "Scan"}}})
    text = "1. Summary:\nThe WAF blocked a scan.\n\n4. Severity:\nSeverity: High\n\n5. What to Check Next:\n1. Check the web log\n\n6. Possible fixes:\n- Close the port"
    answer = app.build_local_report(alert, text, "not a report", "en")
    assert "## 1. Summary" in answer and "## 4. Possible fixes" in answer and app.read_summary(answer)[0] == "High"
    assert "```report-en" in answer and "```report-th" not in answer and "The real person is unknown" in answer
    plain = app.build_local_report(alert, "No headings here", "", "en")
    assert "## Local AI Analysis" in plain


def test_server_flow():
    app.call_ollama = lambda alert, lang="th": "Local saw 10.20.30.254 on APP-SERVER-01"
    seen = {}

    def fake_claude(content, lang="th"):
        seen["content"] = content
        token = app.SESSIONS.items[next(reversed(app.SESSIONS.items))].value_to_token["10.20.30.254"]
        return f"ตรวจ {token}", {"input_tokens": 10, "output_tokens": 5}

    app.call_claude = fake_claude
    app.PORT = 8799
    server = app.ThreadingHTTPServer(("127.0.0.1", 8799), app.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        def call(path, body, token=app.APP_TOKEN):
            request = urllib.request.Request(
                f"http://127.0.0.1:8799{path}", data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json", "X-App-Token": token}, method="POST"
            )
            with urllib.request.urlopen(request) as response:
                return json.load(response)

        page = urllib.request.urlopen("http://127.0.0.1:8799/").read().decode()
        assert "Vigil" in page and "innerHTML" not in page
        local = call("/api/local", {"alert": sample_alert()})
        preview = call("/api/mask", {"alert": sample_alert(), "local": local["answer"], "include_local": True})
        assert "10.20.30.254" not in preview["preview"] and "APP-SERVER-01" not in preview["preview"]
        answer = call("/api/claude", {"session": preview["session"], "preview": preview["preview"]})
        assert answer["answer"] == "ตรวจ 10.20.30.254"
        assert "10.20.30.254" not in seen["content"]
        prompt = call("/api/prompt", {"session": preview["session"], "preview": preview["preview"]})
        assert "<alert>" in prompt["prompt"] and "10.20.30.254" not in prompt["prompt"]
        assert "10.20.30.254" not in app.HISTORY.get(preview["session"])["preview"]
        masker = app.SESSIONS.get(preview["session"])
        token = masker.value_to_token["10.20.30.254"]
        restored = call("/api/restore", {"session": preview["session"], "answer": f"ตรวจ {token}"})
        assert restored["answer"] == "ตรวจ 10.20.30.254"
        app.call_ollama_report = lambda alert, local, lang="th": "```summary\nseverity: low\nverdict: ทดสอบ\n```"
        made = call("/api/local-report", {"session": preview["session"], "alert": sample_alert(), "local": LOCAL_TEXT})
        assert "source: local" in made["answer"] and made["saved"] is True
        restored = call("/api/restore", {"session": preview["session"], "answer": f"ตรวจ {token}"})
        listed = call("/api/history/list", {})["cases"]
        assert listed[0]["id"] == preview["session"] and listed[0]["answered"] is True
        opened = call("/api/history/get", {"id": preview["session"]})["case"]
        assert opened["answer"] == "ตรวจ 10.20.30.254" and "mask_map" not in opened
        call("/api/history/checks", {"id": preview["session"], "done": [1]})
        assert call("/api/history/get", {"id": preview["session"]})["case"]["checks_done"] == [1]
        try:
            call("/api/history/get", {"id": preview["session"]}, "bad")
            raise AssertionError("history was readable without the app token")
        except urllib.error.HTTPError as error:
            assert error.code == 403
        try:
            call("/api/prompt", {"session": preview["session"], "preview": preview["preview"] + " 10.20.30.254"})
            raise AssertionError("residual value was not blocked on copy")
        except urllib.error.HTTPError as error:
            assert error.code == 400
        try:
            call("/api/claude", {"session": preview["session"], "preview": preview["preview"] + " 10.20.30.254"})
            raise AssertionError("residual value was not blocked")
        except urllib.error.HTTPError as error:
            assert error.code == 400
        try:
            call("/api/local", {"alert": "x"}, "bad")
            raise AssertionError("bad token was not blocked")
        except urllib.error.HTTPError as error:
            assert error.code == 403
        try:
            call("/api/quit", {"confirm": True})
            raise AssertionError("quit must be off when the app has a console")
        except urllib.error.HTTPError as error:
            assert error.code == 404
        english = urllib.request.Request(
            "http://127.0.0.1:8799/api/prompt-file",
            data=json.dumps({"session": preview["session"], "preview": preview["preview"]}).encode(),
            headers={"Content-Type": "application/json", "X-App-Token": app.APP_TOKEN, "X-App-Lang": "en"},
            method="POST",
        )
        with urllib.request.urlopen(english) as response:
            content = json.load(response)["content"]
        assert "How to use this file" in content and "Reply in English." in content
        english.full_url = "http://127.0.0.1:8799/api/history/get"
        english.data = json.dumps({"id": "missing"}).encode()
        english.remove_header("Content-length")
        try:
            urllib.request.urlopen(english)
            raise AssertionError("a missing case was found")
        except urllib.error.HTTPError as error:
            assert json.load(error)["error"] == "Case not found. It may have been deleted."
        call("/api/history/delete", {"id": preview["session"]})
        try:
            call("/api/history/get", {"id": preview["session"]})
            raise AssertionError("deleted case was still readable")
        except urllib.error.HTTPError as error:
            assert error.code == 404
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    test_mask_and_restore()
    test_stable_tokens_and_escaped_json()
    test_value_reused_across_fields()
    test_instructions_hold_no_masked_values()
    test_common_word_user_does_not_block_sending()
    test_private_settings_stay_outside_the_code()
    test_documentation_addresses_count_as_public()
    test_history_survives_restart()
    test_failed_save_does_not_stop_analysis()
    test_local_report_uses_alert_facts_over_model()
    test_local_report_survives_bad_model_output()
    test_english_changes_the_prompts_and_keeps_thai_as_is()
    test_local_ai_language()
    test_english_local_report()
    test_server_flow()
    print("all tests passed")
