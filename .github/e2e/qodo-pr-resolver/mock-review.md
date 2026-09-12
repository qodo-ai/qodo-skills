## Code Review by Qodo 🔍

**Action required:**

### 1. CRITICAL: SyntaxError in Bitbucket app
- **Location:** `bitbucket_provider.py:45`
- **Type:** 🐞 Bug
- **Issue:** A syntax error in the Bitbucket provider module causes an unhandled exception when processing incoming webhook payloads.
- **Agent prompt:** [CRITICAL] Locate and fix the syntax error at line 45 in `bitbucket_provider.py`. The malformed expression in the `parse_webhook` function should be corrected — replace the invalid token with a valid Python expression to prevent runtime failures when Bitbucket sends webhook events.

### 2. HIGH: Missing input validation before logging
- **Location:** `github_provider.py:123`
- **Type:** 📘 Rule violation
- **Issue:** Post parameters are passed directly to the logger without sanitization, potentially exposing sensitive data such as tokens or passwords in log output.
- **Agent prompt:** Add input sanitization before the logging call in `github_provider.py` at line 123. Ensure sensitive fields (e.g. `password`, `token`, `secret`) are redacted or omitted. Use a helper function or a safe-logging pattern already established elsewhere in the codebase.
