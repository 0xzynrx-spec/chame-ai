"""QA — 班级学情面板浏览器冒烟测试（Playwright + 本机 Chrome）

不依赖后端：用路由拦截模拟后端不可达，验证前端两条确定性路径：
1. 无 token → 登录屏可见
2. 注入 token + 拦截 API 失败 → 演示模式渲染（徽标 + KPI + 三图表 + 学生横条）
3. 点击学生 → 抽屉打开/关闭
输出截图到 chemai-backend/.gstack/qa-reports/screenshots/。
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

PANEL_HTML = Path(__file__).resolve().parents[2] / "frontend" / "pages" / "panel.html"
OUT = Path(__file__).resolve().parents[1] / ".gstack" / "qa-reports" / "screenshots"


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    url = PANEL_HTML.as_uri()
    results: list[dict] = []

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:
            browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1280, "height": 900})
        page = ctx.new_page()

        console_errs: list[str] = []
        page_errors: list[str] = []
        page.on("console", lambda m: console_errs.append(f"[{m.type}] {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: page_errors.append(str(e)))

        # 1. 无 token → 登录屏
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1500)
        login_visible = page.evaluate("!document.querySelector('#login-screen').classList.contains('hidden')")
        panel_hidden = page.evaluate("document.querySelector('#panel').classList.contains('hidden')")
        page.screenshot(path=os.path.join(OUT, "panel.login.png"))
        results.append({"case": "login-screen", "ok": login_visible and panel_hidden,
                        "login_visible": login_visible, "panel_hidden": panel_hidden})

        # 2. 注入 token + 拦截 API → 演示模式
        page.route("**/api/**", lambda route: route.abort())
        page.evaluate("() => localStorage.setItem('chemai_token', 'smoke-token')")
        page.reload(wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

        state = page.evaluate(
            "() => ({"
            " badge: !document.querySelector('#demo-badge').classList.contains('hidden'),"
            " kpiCount: document.querySelector('#kpi-row').children.length,"
            " donutHasSvg: !!document.querySelector('#donut svg'),"
            " barText: document.querySelector('#bar-chart').innerText,"
            " lineHasSvg: !!document.querySelector('#line-chart svg'),"
            " students: document.querySelectorAll('#students-list button').length"
            "})"
        )
        page.screenshot(path=os.path.join(OUT, "panel.demo.png"))
        results.append({"case": "demo-mode", "ok": state["badge"] and state["kpiCount"] == 4
                        and state["donutHasSvg"] and state["lineHasSvg"] and state["students"] > 0,
                        **state})

        # 3. 点击学生 → 抽屉打开/关闭
        page.click("#students-list button")
        page.wait_for_timeout(800)
        mask_visible = page.evaluate("!document.querySelector('#drawer-mask').classList.contains('hidden')")
        page.click("#drawer-mask")
        page.wait_for_timeout(300)
        mask_hidden = page.evaluate("document.querySelector('#drawer-mask').classList.contains('hidden')")
        results.append({"case": "drawer", "ok": mask_visible and mask_hidden,
                        "opened": mask_visible, "closed": mask_hidden})

        results.append({"case": "errors", "ok": not page_errors,
                        "console_errors": console_errs, "page_errors": page_errors})

        browser.close()

    ok_all = all(r.get("ok") for r in results)
    print(json.dumps({"ok": ok_all, "results": results}, ensure_ascii=False, indent=2))
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(run())
