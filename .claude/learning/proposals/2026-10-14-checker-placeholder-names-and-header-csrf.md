---
id: 2026-10-14-checker-placeholder-names-and-header-csrf
status: applied
applied: 2026-10-14
target: .claude/agents/checker.md
metric: tokens:checker
revises: 2026-10-14-checker-placeholder-default-and-zsh-names
---
Evidence: 2026-10-14 "Housekeeping" step 2: two failed pytest collections for missing CSRF and MINIO settings although placeholder settings are the default (the rule does not name them). Step 4: checker 61.2k tokens (others in this task 21k-29k) from smoke-script bugs: CSRF token taken from the wrong place (write routes read it from the `X-CSRF-Token` header; the login recipe only covers the form field), wrong table name, empty credentials. Earlier cost pattern: 2026-10-13 "Hyperscript out" step 1 (52k) and "Security" step 1 (44k).
Change:
```diff
--- a/.claude/agents/checker.md
+++ b/.claude/agents/checker.md
@@ line 12 (smoke step)
-use placeholder settings (throwaway values, scratch database)
+use placeholder settings (throwaway values, scratch database) for every key in `.env.example` that is not commented out (DATABASE_URL, AUTH_SECRET, MINIO_URL, MINIO_ACCESS_KEY, MINIO_SECRET_KEY, MINIO_BUCKET, MINIO_SECURE, CSRF_SECRET_KEY, COOKIE_SAMESITE, COOKIE_SECURE; AUTH_SECRET must not be the example placeholder, the app rejects it)
@@ after the login recipe
+For a write route (PUT, POST, DELETE from htmx) send the token in the `X-CSRF-Token` header and the cookie jar; take table names from `app/models/`, not from memory; use the same email and password for the superuser and the login.
```
Why: names the settings and the header form once, so the checker stops rediscovering them by failure.
