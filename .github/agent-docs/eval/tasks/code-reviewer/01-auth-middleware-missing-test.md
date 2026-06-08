---
agent: code-reviewer
difficulty: medium
expected-verdict: changes-requested
---

# Task: Auth middleware — missing test for new behaviour

## Input (give this diff to the subagent)

```diff
diff --git a/src/middleware/auth.py b/src/middleware/auth.py
index a1b2c3d..e4f5a6b 100644
--- a/src/middleware/auth.py
+++ b/src/middleware/auth.py
@@ -12,6 +12,14 @@ class AuthMiddleware(BaseHTTPMiddleware):
     async def dispatch(self, request: Request, call_next):
         token = request.headers.get("Authorization", "").removeprefix("Bearer ")
         if not token:
+            # Allow health endpoint without auth
+            if request.url.path == "/health":
+                return await call_next(request)
             return JSONResponse({"detail": "Unauthorized"}, status_code=401)
         try:
             payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
```

No test file changed.

## Expected findings (blocking)

- **Missing test**: The new `/health` bypass has no test asserting that unauthenticated
  requests to `/health` succeed AND that unauthenticated requests to other routes still
  return 401. This is a behaviour change with no test coverage — blocking.

## Expected findings (should-fix or nit)

- The `removeprefix("Bearer ")` silently accepts a raw token (no `Bearer ` prefix) — may
  or may not be intentional; worth flagging as should-fix or nit.

## Pass criteria

The subagent must:
1. Return `verdict: changes-requested`
2. Cite a `blocking` finding about the missing test
3. Reference the specific lines changed (middleware dispatch method)
