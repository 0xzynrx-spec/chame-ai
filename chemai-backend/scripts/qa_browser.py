"""QA — 学生端页面浏览器冒烟测试（Playwright + 本机 Chromium）

后端 127.0.0.1:8000、前端 127.0.0.1:5173 已在运行。脚本用真实浏览器：
1. 逐页加载，采集控制台错误/页面异常/CDN 加载失败
2. 无 token 空态渲染
3. 注入学生 token 后鉴权态渲染（列表应 200 且空态正常）
输出截图到 chemai-backend/.gstack/qa-reports/screenshots/。
"""

from __future__ import annotations

import json
import os
import sys

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5173"
BACKEND = "http://127.0.0.1:8000"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   ".gstack", "qa-reports", "screenshots")
PAGES = ["index.html", "practice.html", "wrong.html", "review.html"]


def token() -> str:
    # 优先读环境变量（Windows 下 /tmp 与 bash 的 /tmp 不一致，避免路径错位）
    env = os.environ.get("CHEMAI_STUDENT_TOKEN", "").strip()
    if env:
        return env
    p = "/tmp/chemai_student_token.txt"
    if os.path.exists(p):
        return open(p, encoding="utf-8").read().strip()
    return ""


def run():
    os.makedirs(OUT, exist_ok=True)
    results = []

    with sync_playwright() as p:
        # 本机 Playwright 内置 chromium 版本与 Python 包不匹配，改用系统 Chrome
        try:
            browser = p.chromium.launch(channel="chrome", headless=True)
        except Exception:
            browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 430, "height": 900})
        page = ctx.new_page()

        console_errs: list[str] = []
        page_errors: list[str] = []
        failed_reqs: list[str] = []
        page.on("console", lambda m: console_errs.append(f"[{m.type}] {m.text}") if m.type in ("error",) else None)
        page.on("pageerror", lambda e: page_errors.append(str(e)))
        page.on("requestfailed", lambda r: failed_reqs.append(f"{r.url} :: {r.failure}"))

        # ── 逐页：无 token 空态 ──
        for name in PAGES:
            console_errs.clear(); page_errors.clear(); failed_reqs.clear()
            try:
                resp = page.goto(f"{BASE}/{name}", wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2500)
            except Exception as e:  # noqa: BLE001
                results.append({"page": name, "ok": False, "err": str(e)})
                continue

            state = page.evaluate(
                "() => ({vue: !!window.Vue, tailwind: !!window.tailwind, katex: !!window.renderMathInElement, "
                "appChildren: (document.querySelector('#app')||{children:[]}).children.length, "
                "title: document.title, text: (document.body.innerText||'').slice(0,200)})"
            )
            page.screenshot(path=os.path.join(OUT, f"{name}.png"), full_page=False)
            results.append({
                "page": name,
                "ok": True,
                "status": resp.status if resp else None,
                **state,
                "console_errors": list(console_errs),
                "page_errors": list(page_errors),
                "failed_requests": list(failed_reqs),
            })

        # ── 注入学生 token 后的鉴权态 ──
        t = token()
        if t:
            for name in ["practice.html", "wrong.html", "review.html"]:
                console_errs.clear(); page_errors.clear()
                page.goto(f"{BASE}/{name}", wait_until="domcontentloaded", timeout=30000)
                page.evaluate("t => localStorage.setItem('chemai_token', t)", t)
                page.reload(wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(2500)
                state = page.evaluate(
                    "() => ({appChildren: (document.querySelector('#app')||{children:[]}).children.length, "
                    "text: (document.body.innerText||'').slice(0,400)})"
                )
                page.screenshot(path=os.path.join(OUT, f"{name}.authed.png"), full_page=False)
                results.append({
                    "page": f"{name} (authed)",
                    "ok": True,
                    **state,
                    "console_errors": list(console_errs),
                    "page_errors": list(page_errors),
                })

        browser.close()

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    run()
