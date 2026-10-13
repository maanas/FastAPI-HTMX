"""Security headers on every response, static files, redirects and errors included.

Pure ASGI, so a streaming download is passed through chunk by chunk, never buffered.
"""

# One entry per directive; everything is own origin only.
CSP_DIRECTIVES = {
    "default-src": "'self'",
    "script-src": "'self'",
    "style-src": "'self'",
    # data: is the form-control icons (select arrow, checkbox tick) in the built CSS
    "img-src": "'self' data:",
    "font-src": "'self'",
    "connect-src": "'self'",
    "object-src": "'none'",
    "base-uri": "'self'",
    "form-action": "'self'",
    "frame-ancestors": "'none'",
}
CONTENT_SECURITY_POLICY = "; ".join(f"{k} {v}" for k, v in CSP_DIRECTIVES.items())

SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}
HSTS = ("Strict-Transport-Security", "max-age=31536000; includeSubDomains")


class SecurityHeadersMiddleware:
    def __init__(self, app, hsts: bool = False):
        self.app = app
        headers = dict(SECURITY_HEADERS)
        if hsts:
            headers[HSTS[0]] = HSTS[1]
        self.headers = [(k.lower().encode(), v.encode()) for k, v in headers.items()]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                present = {name.lower() for name, _ in headers}
                message["headers"] = headers + [
                    pair for pair in self.headers if pair[0] not in present
                ]
            await send(message)

        await self.app(scope, receive, send_with_headers)
