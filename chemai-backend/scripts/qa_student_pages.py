"""QA — 学生端页面完整浏览器测试（Playwright）

测试范围：login.html, index.html, practice.html, wrong.html, review.html, my.html
后端 127.0.0.1:8000、前端 127.0.0.1:8888 已在运行。
"""

from __future__ import annotations

import json
import os
import sys
import time

from playwright.sync_api import sync_playwright

FRONTEND = "http://localhost:8888"
BACKEND = "http://localhost:8000"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "qa_screenshots")
TOKEN_FILE = "/tmp/chemai_student_token.txt"


def get_token() -> str:
    env = os.environ.get("CHEMAI_STUDENT_TOKEN", "").strip()
    if env:
        return env
    if os.path.exists(TOKEN_FILE):
        return open(TOKEN_FILE, encoding="utf-8").read().strip()
    return ""


def run():
    os.makedirs(OUT, exist_ok=True)
    token = get_token()
    results = []

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:
            browser = p.chromium.launch(headless=True)

        ctx = browser.new_context(viewport={"width": 430, "height": 900})
        page = ctx.new_page()

        console_errs = []
        page_errors = []

        def on_console(msg):
            if msg.type in ("error", "warning"):
                console_errs.append(f"[{msg.type}] {msg.text}")

        def on_page_error(err):
            page_errors.append(str(err))

        page.on("console", on_console)
        page.on("pageerror", on_page_error)

        # ── Test 1: Login page ─────────────────────────
        print("\n=== Test 1: Login page ===")
        console_errs.clear()
        page_errors.clear()

        page.goto(f"{FRONTEND}/login.html")
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        page.screenshot(path=os.path.join(OUT, "01-login-page.png"), full_page=True)

        # Check login form elements
        username_input = page.query_selector('input[placeholder*="学号"]')
        password_input = page.query_selector('input[placeholder*="密码"]')
        login_btn = page.query_selector('button:has-text("登 录")')

        assert username_input, "Username input not found"
        assert password_input, "Password input not found"
        assert login_btn, "Login button not found"
        print("  [PASS] Login form elements present")

        # Test empty submission
        login_btn.click()
        time.sleep(0.5)
        page.screenshot(path=os.path.join(OUT, "02-login-empty-submit.png"), full_page=True)
        error_msg = page.query_selector('.text-error-red')
        if error_msg and error_msg.is_visible():
            print("  [PASS] Empty form shows error message")
        else:
            print("  [FAIL] No error message on empty form submission")

        # Test successful login
        username_input.fill("student_zhang")
        password_input.fill("123456")
        login_btn.click()
        time.sleep(2)
        page.screenshot(path=os.path.join(OUT, "03-login-success.png"), full_page=True)

        # Should redirect to index.html
        current_url = page.url
        if "index.html" in current_url:
            print("  [PASS] Login redirects to index.html")
        else:
            print(f"  [FAIL] Login did not redirect. Current URL: {current_url}")

        results.append(("Login page", "PASS" if "index.html" in current_url else "FAIL"))

        # ── Test 2: Index page (AI 助教) ──────────────
        print("\n=== Test 2: Index page (AI 助教) ===")
        console_errs.clear()
        page_errors.clear()

        page.goto(f"{FRONTEND}/index.html")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        page.screenshot(path=os.path.join(OUT, "04-index-page.png"), full_page=True)

        # Check header
        header = page.query_selector('h1:has-text("AI 助教")')
        assert header, "AI 助教 header not found"
        print("  [PASS] AI 助教 header present")

        # Check welcome message
        welcome = page.query_selector('h2:has-text("ChemAI 助教")')
        if welcome:
            print("  [PASS] Welcome message present")
        else:
            print("  [FAIL] Welcome message not found")

        # Check quick chips
        chips = page.query_selector_all('.chip')
        if len(chips) > 0:
            print(f"  [PASS] {len(chips)} quick chips present")
        else:
            print("  [FAIL] No quick chips found")

        # Check bottom nav
        nav_items = page.query_selector_all('.nav-item')
        if len(nav_items) >= 4:
            print(f"  [PASS] Bottom nav with {len(nav_items)} items")
        else:
            print(f"  [FAIL] Bottom nav has {len(nav_items)} items (expected >= 4)")

        # Check console errors
        if console_errs:
            print(f"  [WARN] Console errors: {console_errs}")
        else:
            print("  [PASS] No console errors")

        results.append(("Index page", "PASS" if not console_errs else "WARN"))

        # ── Test 3: Practice page ──────────────────────
        print("\n=== Test 3: Practice page ===")
        console_errs.clear()
        page_errors.clear()

        page.goto(f"{FRONTEND}/practice.html")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        page.screenshot(path=os.path.join(OUT, "05-practice-page.png"), full_page=True)

        # Check header
        header = page.query_selector('h1:has-text("练习")')
        assert header, "Practice header not found"
        print("  [PASS] Practice header present")

        # Check stats cards
        stat_cards = page.query_selector_all('.card-animate')
        if len(stat_cards) >= 2:
            print(f"  [PASS] {len(stat_cards)} stat cards present")
        else:
            print(f"  [FAIL] Only {len(stat_cards)} stat cards")

        # Check empty state or task list
        empty_state = page.query_selector('text=暂无练习任务')
        task_list = page.query_selector_all('.bg-white.rounded-lg.p-4.border')
        if empty_state:
            print("  [PASS] Empty state shown (no tasks)")
        elif len(task_list) > 0:
            print(f"  [PASS] {len(task_list)} practice tasks listed")
        else:
            print("  [FAIL] No tasks and no empty state")

        # Check bottom nav
        nav_items = page.query_selector_all('.nav-item')
        if len(nav_items) >= 4:
            print(f"  [PASS] Bottom nav with {len(nav_items)} items")

        if console_errs:
            print(f"  [WARN] Console errors: {console_errs}")
        else:
            print("  [PASS] No console errors")

        results.append(("Practice page", "PASS" if not console_errs else "WARN"))

        # ── Test 4: Wrong answers page ─────────────────
        print("\n=== Test 4: Wrong answers page ===")
        console_errs.clear()
        page_errors.clear()

        page.goto(f"{FRONTEND}/wrong.html")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        page.screenshot(path=os.path.join(OUT, "06-wrong-page.png"), full_page=True)

        # Check header
        header = page.query_selector('h1:has-text("错题本")')
        assert header, "Wrong answers header not found"
        print("  [PASS] Wrong answers header present")

        # Check review entry
        review_entry = page.query_selector('a[href="review.html"]')
        if review_entry:
            print("  [PASS] Review entry link present")
        else:
            print("  [FAIL] Review entry link not found")

        # Check empty state
        empty_state = page.query_selector('text=暂无错题')
        if empty_state:
            print("  [PASS] Empty state shown (no wrong answers)")
        else:
            print("  [INFO] Wrong answers list present")

        # Check bottom nav
        nav_items = page.query_selector_all('.nav-item')
        if len(nav_items) >= 4:
            print(f"  [PASS] Bottom nav with {len(nav_items)} items")

        if console_errs:
            print(f"  [WARN] Console errors: {console_errs}")
        else:
            print("  [PASS] No console errors")

        results.append(("Wrong page", "PASS" if not console_errs else "WARN"))

        # ── Test 5: Review page ────────────────────────
        print("\n=== Test 5: Review page ===")
        console_errs.clear()
        page_errors.clear()

        page.goto(f"{FRONTEND}/review.html")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        page.screenshot(path=os.path.join(OUT, "07-review-page.png"), full_page=True)

        # Check header
        header = page.query_selector('h1:has-text("复习中心")')
        assert header, "Review header not found"
        print("  [PASS] Review header present")

        # Check stats
        due_stat = page.query_selector('text=今日待复习')
        overdue_stat = page.query_selector('text=已超期')
        if due_stat and overdue_stat:
            print("  [PASS] Review stats present")
        else:
            print("  [FAIL] Review stats not found")

        # Check empty state
        empty_state = page.query_selector('text=今日没有待复习的任务')
        if empty_state:
            print("  [PASS] Empty state shown (no review tasks)")
        else:
            print("  [INFO] Review tasks present")

        if console_errs:
            print(f"  [WARN] Console errors: {console_errs}")
        else:
            print("  [PASS] No console errors")

        results.append(("Review page", "PASS" if not console_errs else "WARN"))

        # ── Test 6: My page ───────────────────────────
        print("\n=== Test 6: My page ===")
        console_errs.clear()
        page_errors.clear()

        page.goto(f"{FRONTEND}/my.html")
        page.wait_for_load_state("networkidle")
        time.sleep(2)
        page.screenshot(path=os.path.join(OUT, "08-my-page.png"), full_page=True)

        # Check header
        header = page.query_selector('h1:has-text("我的")')
        assert header, "My page header not found"
        print("  [PASS] My page header present")

        # Check profile card
        profile_card = page.query_selector('.bg-white.rounded-xl.p-5')
        if profile_card:
            print("  [PASS] Profile card present")
        else:
            print("  [FAIL] Profile card not found")

        # Check stats
        stat_cards = page.query_selector_all('.bg-white.rounded-lg.p-3')
        if len(stat_cards) >= 3:
            print(f"  [PASS] {len(stat_cards)} stat cards present")
        else:
            print(f"  [FAIL] Only {len(stat_cards)} stat cards")

        # Check menu items
        menu_items = page.query_selector_all('.cursor-pointer')
        if len(menu_items) >= 4:
            print(f"  [PASS] {len(menu_items)} menu items present")
        else:
            print(f"  [FAIL] Only {len(menu_items)} menu items")

        # Check bottom nav
        nav_items = page.query_selector_all('.nav-item')
        if len(nav_items) >= 4:
            print(f"  [PASS] Bottom nav with {len(nav_items)} items")

        if console_errs:
            print(f"  [WARN] Console errors: {console_errs}")
        else:
            print("  [PASS] No console errors")

        results.append(("My page", "PASS" if not console_errs else "WARN"))

        # ── Test 7: Navigation test ────────────────────
        print("\n=== Test 7: Navigation test ===")
        console_errs.clear()
        page_errors.clear()

        # Test bottom nav links
        nav_links = [
            ("index.html", "AI助教"),
            ("practice.html", "练习"),
            ("wrong.html", "错题"),
            ("my.html", "我的"),
        ]

        for href, label in nav_links:
            nav_item = page.query_selector(f'.nav-item[href="{href}"]')
            if nav_item:
                nav_item.click()
                time.sleep(1)
                current = page.url
                if href in current:
                    print(f"  [PASS] Nav to {label} works")
                else:
                    print(f"  [FAIL] Nav to {label} failed. URL: {current}")
            else:
                print(f"  [FAIL] Nav item for {label} not found")

        results.append(("Navigation", "PASS" if not page_errors else "FAIL"))

        # ── Test 8: Responsive test ────────────────────
        print("\n=== Test 8: Responsive test ===")

        # Test mobile viewport
        page.set_viewport_size({"width": 375, "height": 812})
        page.goto(f"{FRONTEND}/index.html")
        page.wait_for_load_state("networkidle")
        time.sleep(1)
        page.screenshot(path=os.path.join(OUT, "09-mobile-index.png"), full_page=True)

        # Check if content fits
        body_width = page.evaluate("document.body.scrollWidth")
        if body_width <= 375:
            print("  [PASS] Content fits mobile viewport")
        else:
            print(f"  [FAIL] Content overflows mobile viewport ({body_width}px)")

        # Reset viewport
        page.set_viewport_size({"width": 430, "height": 900})

        results.append(("Responsive", "PASS" if body_width <= 375 else "FAIL"))

        # ── Summary ────────────────────────────────────
        print("\n" + "=" * 50)
        print("QA Summary")
        print("=" * 50)
        for name, status in results:
            icon = "[PASS]" if status == "PASS" else "[FAIL]" if status == "FAIL" else "[WARN]"
            print(f"  {icon} {name}: {status}")

        passed = sum(1 for _, s in results if s == "PASS")
        failed = sum(1 for _, s in results if s == "FAIL")
        warned = sum(1 for _, s in results if s == "WARN")
        print(f"\nTotal: {passed} passed, {failed} failed, {warned} warnings")

        browser.close()

    return failed == 0


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
