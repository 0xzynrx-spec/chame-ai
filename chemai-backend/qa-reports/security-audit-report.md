# Security Audit Report — v1.0.0-rc.1

**Date:** 2026-08-30
**Branch:** phase-7/ship
**Auditor:** Claude Code

---

## Executive Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| High | 1 |
| Medium | 2 |
| Low | 0 |

---

## Findings

### HIGH-001: Missing .gitignore

**Status:** FIXED
**Description:** Project root lacked `.gitignore`, risking accidental commit of secrets (`.env` with API keys).
**Fix:** Created `.gitignore` with exclusions for `.env`, `__pycache__`, `.pytest_cache`, intermediate eval results, etc.

---

### MEDIUM-001: CORS allows `null` origin

**File:** `app/config.py`
**Description:** `cors_origins` includes `"null"`, which allows requests from `file://` origins and certain sandboxed contexts. This is a security risk in production.
**Recommendation:** Remove `"null"` from `cors_origins` in production config. Keep only trusted domains.

---

### MEDIUM-002: JWT secret has default value

**File:** `app/config.py`
**Description:** `jwt_secret` defaults to `"change-me-in-production-use-env-var"`. If deployed without setting `CHEMAI_JWT_SECRET`, tokens are trivially forgeable.
**Recommendation:** Set `CHEMAI_JWT_SECRET` environment variable in production. Consider failing fast if default is detected at startup.

---

## Positive Findings

- ✅ No hardcoded API keys in source code (`.env` not tracked)
- ✅ JWT authentication enforced on all API endpoints (whitelist only for public paths)
- ✅ PII masking implemented in chat responses
- ✅ Content safety filtering (dangerous content detection)
- ✅ Tool guard system with approval checkpoints for destructive operations
- ✅ SQL injection mitigated via SQLAlchemy ORM
- ✅ Input validation on all API endpoints

---

## Recommendations for Production

1. Set `CHEMAI_JWT_SECRET` to a strong random value (≥32 bytes)
2. Remove `"null"` from CORS origins
3. Enable HTTPS
4. Set up rate limiting
5. Configure proper logging and monitoring

---

**Conclusion:** No critical vulnerabilities. High issue (missing .gitignore) has been fixed. Medium issues should be addressed before production deployment.
