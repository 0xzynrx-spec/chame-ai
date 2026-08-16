"""QA — 班级学情面板真实数据路径浏览器测试（Playwright + 本机 Chrome）

依赖后端：后端需在 :8000 运行且已播种面板数据（见 qa_seed_panel.py）。
覆盖真实登录 + 真实 API 渲染路径（区别于 qa_panel_browser.py 的演示模式）：
1. 无 token → 登录屏
2. 填 teacher_wang / 123456 登录 → 面板可见
3. 班级选择器、KPI 4 卡、柱状图、环形图、折线图、学生横条均从真实 API 渲染
4. 点击学生 → 抽屉展示障碍分布/主导障碍/薄弱知识点/作答历史
5. 采集 console error / pageerror
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
        ctx = browser.new_context(viewport={"width": 1280, "height": 1000})
        page = ctx.new_page()

        console_errs: list[str] = []
        page_errors: list[str] = []
        page.on("console", lambda m: console_errs.append(f"[{m.type}] {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: page_errors.append(str(e)))

        # 1. 无 token → 登录屏
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1200)
        login_visible = page.evaluate("!document.querySelector('#login-screen').classList.contains('hidden')")
        page.screenshot(path=os.path.join(OUT, "panel-real.login.png"))
        results.append({"case": "login-screen", "ok": login_visible, "login_visible": login_visible})

        # 2. 填真实账号登录
        page.fill("#login-username", "teacher_wang")
        page.fill("#login-password", "123456")
        page.click("#login-btn")
        # 等待 KPI 卡渲染完成（4 卡）
        try:
            page.wait_for_function(
                "document.querySelector('#kpi-row').children.length === 4",
                timeout=15000,
            )
        except Exception:
            pass
        page.wait_for_timeout(1500)

        panel_visible = page.evaluate("!document.querySelector('#panel').classList.contains('hidden')")
        login_hidden = page.evaluate("document.querySelector('#login-screen').classList.contains('hidden')")

        # 3. 采集各区块真实渲染状态
        state = page.evaluate(
            "() => {"
            "  const kpiTexts = [...document.querySelectorAll('#kpi-row > div')].map(d => d.innerText);"
            "  return {"
            "    classOptions: [...document.querySelectorAll('#class-select option')].map(o => ({v:o.value, t:o.textContent})),"
            "    selectValue: document.querySelector('#class-select').value,"
            "    kpiCount: document.querySelector('#kpi-row').children.length,"
            "    kpiTexts,"
            "    barBars: document.querySelectorAll('#bar-chart .bg-teal-accent').length,"
            "    barText: document.querySelector('#bar-chart').innerText,"
            "    donutSegments: document.querySelectorAll('#donut circle').length,"
            "    donutText: document.querySelector('#donut').innerText,"
            "    linePolyline: !!document.querySelector('#line-chart polyline'),"
            "    lineDots: document.querySelectorAll('#line-chart circle').length,"
            "    students: [...document.querySelectorAll('#students-list button')].map(b => b.innerText),"
            "    demoBadgeHidden: document.querySelector('#demo-badge').classList.contains('hidden'),"
            "  };"
            "}"
        )
        page.screenshot(path=os.path.join(OUT, "panel-real.panel.png"), full_page=True)

        kpi_ok = (state["kpiCount"] == 4 and "考试次数" in state["kpiTexts"][0]
                  and "需关注学生" in state["kpiTexts"][1])
        results.append({
            "case": "panel-render",
            "ok": panel_visible and login_hidden and kpi_ok
                  and len(state["classOptions"]) == 1
                  and state["selectValue"] == state["classOptions"][0]["v"]
                  and state["barBars"] >= 1
                  and state["donutSegments"] >= 1
                  and state["linePolyline"] and state["lineDots"] >= 2
                  and len(state["students"]) == 2
                  and state["demoBadgeHidden"],
            "panel_visible": panel_visible, "login_hidden": login_hidden, **state,
        })

        # 4. 点击首个学生 → 抽屉
        page.click("#students-list button")
        page.wait_for_timeout(1500)
        drawer_state = page.evaluate(
            "() => ({"
            "  maskVisible: !document.querySelector('#drawer-mask').classList.contains('hidden'),"
            "  title: document.querySelector('#drawer-title').innerText,"
            "  body: document.querySelector('#drawer-body').innerText,"
            "})"
        )
        page.screenshot(path=os.path.join(OUT, "panel-real.drawer.png"), full_page=True)
        drawer_ok = (drawer_state["maskVisible"] and drawer_state["title"]
                     and "主导障碍" in drawer_state["body"] and "薄弱知识点" in drawer_state["body"])
        results.append({"case": "drawer", "ok": drawer_ok, **drawer_state})

        # 5. 错误采集
        results.append({"case": "errors", "ok": not page_errors and not console_errs,
                        "console_errors": console_errs, "page_errors": page_errors})

        browser.close()

    ok_all = all(r.get("ok") for r in results)
    print(json.dumps({"ok": ok_all, "results": results}, ensure_ascii=False, indent=2))
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(run())
