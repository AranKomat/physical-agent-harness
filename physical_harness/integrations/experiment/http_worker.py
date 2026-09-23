"""One-shot HTTP worker. Parent kills local worker at a wall deadline; no retries."""
from __future__ import annotations

import sys
import urllib.error
import urllib.request

from physical_harness.integrations.experiment.validation import dumps, loads


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Redirects are disabled")


def main():
    request = loads(sys.stdin.buffer.read(40_000_001))
    body = dumps(request["payload"])
    opener = urllib.request.build_opener(NoRedirect(), urllib.request.ProxyHandler({}))
    wire = urllib.request.Request(request["url"], data=body, method="POST",
                                  headers=request["headers"])
    try:
        with opener.open(wire, timeout=request["timeout_s"]) as response:
            content = response.read(request["max_response_bytes"] + 1)
            if len(content) > request["max_response_bytes"]:
                raise ValueError("Response exceeds transport bound")
            result = {"status": response.status, "body": loads(content),
                      "request_id": response.headers.get("x-request-id")}
    except urllib.error.HTTPError as exc:
        # Never echo provider error bodies; they can include user data or secrets.
        result = {"error": "http_error", "status": exc.code}
    except Exception as exc:
        result = {"error": type(exc).__name__}
    sys.stdout.buffer.write(dumps(result))
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()
