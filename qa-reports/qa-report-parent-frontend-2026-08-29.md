# QA Report — 家长端前端

**Date:** 2026-08-29
**Branch:** feature/student-practice-review
**Mode:** Diff-aware (parent frontend changes)
**Tier:** Standard

---

## Summary

| Metric | Value |
|--------|-------|
| Pages tested | 2 (parent-login.html, parent.html) |
| API endpoints tested | 10 |
| Issues found | 2 (both fixed) |
| Critical | 1 → 0 |
| Medium | 1 → 0 |

**Health Score:** 72/100 → 95/100 (after fixing ISSUE-001 and ISSUE-002)

---

## API Verification Results

| # | Endpoint | Status |
|---|----------|--------|
| 1 | GET /api/parent/children | PASS |
| 2 | GET /api/parent/overview | PASS |
| 3 | GET /api/parent/learning-report | PASS |
| 4 | GET /api/parent/notifications | PASS |
| 5 | POST /api/parent/bind (duplicate) | PASS (correctly rejected) |
| 6 | POST /api/parent/bind (invalid) | PASS (correctly rejected) |
| 7 | PUT /api/parent/notifications/read-all | PASS |
| 8 | POST /api/parent/weekly-report/generate | PASS |
| 9 | Auth: no token | PASS (401) |
| 10 | Auth: invalid token | PASS (401) |

---

## Issues

### ISSUE-001: AI Chat SSE Endpoint Missing (Critical) — FIXED

**Category:** Functional
**Severity:** Critical
**File:** `frontend/pages/parent/parent.html:549`
**Fixed in:** `f11ccee` — `app/api/chat.py`
**Status:** Verified

**Description:** The floating AI button triggers `sendAiMessage()` which calls `ChemUI.createSSEClient({ url: '/api/chat/langgraph/stream', ... })`. This endpoint did not exist in the backend.

**Fix:** Implemented `POST /api/chat/langgraph/stream` with DashScope streaming, parent-role system prompt, and student context injection.

---

### ISSUE-002: Weekly Report Field Name Mismatch (Medium) — FIXED

**Category:** Functional
**Severity:** Medium
**File:** `frontend/pages/parent/parent.html:175-198`
**Fixed in:** `59505e1`
**Status:** Verified

**Description:** Backend returned Chinese keys (`综合评价`/`具体表现`/`家庭建议`) but frontend accessed English keys (`summary`/`detail`/`advice`).

**Fix:** Template now checks both formats: `weeklyReport['综合评价'] || weeklyReport.summary`.

---

## Fix Status

- ISSUE-001: **Verified** — implemented in `f11ccee`, SSE streaming with DashScope, student context injection
- ISSUE-002: **Verified** — fixed in `59505e1`, now supports both Chinese and English key formats
