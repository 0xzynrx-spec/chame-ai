"""QA — 答题卡 OCR 判卷浏览器联通测试（Playwright + mock OCR 后端）

依赖：后端以 mock OCR 运行在 :8000（见 run_mock_ocr_server.py），
      且已播种演示考试（见 seed_ocr_demo.py）。
覆盖真实登录 + 真实 API 渲染路径：
1. 无 token → 登录屏
2. teacher_wang / 123456 登录 → 主面板可见
3. 考试选择器加载出「OCR 演示考试」并选中
4. 上传一张 mock 答题卡 → 队列出现，轮询到「待复核」
5. 打开复核抽屉 → 逐题三态（正确/错误）渲染
6. 确认入库 → 状态转「已入库」，toast 提示 written/skipped
7. 采集 console error / pageerror
输出截图到 chemai-backend/.gstack/qa-reports/screenshots/。
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

OCR_HTML = Path(__file__).resolve().parents[2] / "frontend" / "pages" / "ocr.html"
OUT = Path(__file__).resolve().parents[1] / ".gstack" / "qa-reports" / "screenshots"


def run() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    url = OCR_HTML.as_uri()
    results: list[dict] = []

    # 生成一张 mock 答题卡文件（mock OCR 忽略内容，仅校验扩展名与大小）
    fd, img_path = tempfile.mkstemp(suffix=".jpg")
    os.write(fd, b"mock-answer-sheet")
    os.close(fd)

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:
            browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 1000})
        page = ctx.new_page()

        console_errs: list[str] = []
        page_errors: list[str] = []
        page.on(
            "console",
            lambda m: console_errs.append(f"[{m.type}] {m.text}") if m.type == "error" else None,
        )
        page.on("pageerror", lambda e: page_errors.append(str(e)))

        # 1. 无 token → 登录屏
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1200)
        login_visible = page.evaluate(
            "!document.querySelector('#login-screen').classList.contains('hidden')"
        )
        results.append({"case": "login-screen", "ok": login_visible})
        page.screenshot(path=os.path.join(OUT, "ocr.login.png"))

        # 2. 登录
        page.fill("#login-username", "teacher_wang")
        page.fill("#login-password", "123456")
        page.click("#login-btn")
        try:
            page.wait_for_function(
                "!document.querySelector('#panel').classList.contains('hidden')",
                timeout=15000,
            )
            login_ok = True
        except Exception:
            login_ok = False
        page.wait_for_timeout(1500)
        results.append({"case": "login", "ok": login_ok})

        # 3. 考试选择器
        exam_options = page.evaluate(
            "[...document.querySelectorAll('#exam-select option')].map(o => ({v:o.value, t:o.textContent}))"
        )
        demo = next((o for o in exam_options if "OCR 演示考试" in o["t"]), None)
        results.append({
            "case": "exam-list",
            "ok": demo is not None,
            "options": exam_options,
        })
        if demo:
            page.select_option("#exam-select", demo["v"])

        # 4. 上传 → 轮询到「待复核 / 已入库」
        page.set_input_files("#file-input", img_path)
        try:
            page.wait_for_function(
                "(() => { const t = document.querySelector('#queue').innerText; "
                "return t.includes('待复核') || t.includes('已入库'); })()",
                timeout=30000,
            )
            upload_ok = True
        except Exception:
            upload_ok = False
        queue_text = page.evaluate("document.querySelector('#queue').innerText")
        results.append({"case": "upload-grade", "ok": upload_ok, "queue": queue_text})
        page.screenshot(path=os.path.join(OUT, "ocr.queue.png"), full_page=True)

        # 5. 复核抽屉
        try:
            page.locator("#queue button", has_text="复核").first.click()
            page.wait_for_function(
                "document.querySelector('#drawer-body').innerText.includes('学生作答')",
                timeout=10000,
            )
            drawer_ok = True
        except Exception:
            drawer_ok = False
        drawer_text = page.evaluate("document.querySelector('#drawer-body').innerText")
        drawer_summary = page.evaluate("document.querySelector('#drawer-summary').innerText")
        has_correct = "正确" in drawer_text
        has_incorrect = "错误" in drawer_text
        results.append({
            "case": "review-drawer",
            "ok": drawer_ok and has_correct and has_incorrect,
            "drawer_summary": drawer_summary,
            "drawer_text": drawer_text,
        })
        page.screenshot(path=os.path.join(OUT, "ocr.drawer.png"), full_page=True)

        # 6. 确认入库
        try:
            page.click("#confirm-btn")
            page.wait_for_function(
                "document.querySelector('#toast').innerText.includes('确认成功')",
                timeout=10000,
            )
            confirm_ok = True
        except Exception:
            confirm_ok = False
        page.wait_for_timeout(800)
        queue_after = page.evaluate("document.querySelector('#queue').innerText")
        toast_text = page.evaluate("document.querySelector('#toast').innerText")
        done_shown = "已入库" in queue_after
        results.append({
            "case": "confirm",
            "ok": confirm_ok and done_shown,
            "toast": toast_text,
            "queue_after": queue_after,
        })
        page.screenshot(path=os.path.join(OUT, "ocr.confirm.png"), full_page=True)

        # 7. 错误采集
        results.append({
            "case": "errors",
            "ok": not page_errors and not console_errs,
            "console_errors": console_errs,
            "page_errors": page_errors,
        })

        browser.close()

    os.unlink(img_path)
    ok_all = all(r.get("ok") for r in results)
    print(json.dumps({"ok": ok_all, "results": results}, ensure_ascii=False, indent=2))
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(run())
