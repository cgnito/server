# Improvements & Findings

This document tracks all audit findings and the planned implementation roadmap.
Each finding has a status so progress can be tracked over time.

Status labels: `[ ]` open · `[x]` done · `[-]` deferred · `[~]` in progress

---

## Findings

### A. TCP and Connection Handling

---

**A1 — Single connection, then exit**
- **Status:** `[x]`
- **Finding:** `accept()` is called once with no loop. The server exits after handling one request.
- **Evidence:** `server.py:18`
- **Impact:** Only one HTTP request is ever served per run.
- **Category:** Correctness bug
- **Priority:** High
- **Recommendation:** Wrap `accept()` and the connection handler in a `while True:` loop.
- **Learning value:** Connection accept loops; per-connection state isolation.
- **Dependencies:** None. Do this before adding a timeout (A4).

---

**A2 — Missing `SO_REUSEADDR`**
- **Status:** `[x]`
- **Finding:** The server socket is created and bound without setting socket options.
- **Evidence:** `server.py:7–14`
- **Impact:** Restarting within ~60 seconds of a crash raises `OSError: Address already in use` due to TCP `TIME_WAIT`.
- **Category:** Robustness issue
- **Priority:** High
- **Recommendation:** Add `server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)` before `bind()`.
- **Learning value:** TCP `TIME_WAIT` state; what `SO_REUSEADDR` does and does not bypass.
- **Dependencies:** None.

---

**A3 — `sendall` not guarded against a broken connection**
- **Status:** `[x]`
- **Finding:** `connection.sendall(response)` has no error handling.
- **Evidence:** `server.py:46`
- **Impact:** If the client disconnects before the response is sent, `BrokenPipeError` propagates unhandled. In a loop (A1) this would kill the server.
- **Category:** Robustness issue
- **Priority:** High (grows to critical once A1 is fixed)
- **Recommendation:** Wrap `sendall` in `try/except OSError` and log the failure.
- **Learning value:** Why write errors on sockets are normal; difference between `send` and `sendall`.
- **Dependencies:** A1.

---

**A4 — No timeout on socket reads**
- **Status:** `[x]`
- **Finding:** `receive_headers` and `read_request_body` can block indefinitely on `recv`.
- **Evidence:** `http_parser.py:68`, `http_parser.py:89`
- **Impact:** A client that stalls after connecting holds the server (and eventually all connections) forever.
- **Category:** Robustness issue
- **Priority:** High (after A1)
- **Recommendation:** Call `connection.settimeout(30)` after `accept()`. Catch `socket.timeout` and respond with `408 Request Timeout`.
- **Learning value:** Why network servers always need read deadlines; what `socket.timeout` signals.
- **Dependencies:** A1.

---

**A5 — Server socket not protected in a `try/finally`**
- **Status:** `[x]`
- **Finding:** `server_socket.close()` is at the end of the file. A `KeyboardInterrupt` or exception during `accept()` skips it.
- **Evidence:** `server.py:47`
- **Impact:** File descriptor leak; port may not release cleanly.
- **Category:** Robustness issue
- **Priority:** Low
- **Recommendation:** Wrap the accept loop in `try/finally: server_socket.close()`, or use `with socket.socket(...) as server_socket:`.
- **Learning value:** Resource cleanup discipline; context managers on sockets.
- **Dependencies:** A1.

---

### B. HTTP Request Parsing

---

**B1 — `method.isalpha()` does not enforce uppercase**
- **Status:** `[x]`
- **Finding:** `method.isalpha()` accepts lowercase and mixed-case methods like `get` or `Get`.
- **Evidence:** `http_parser.py:9`
- **Impact:** A lowercase method passes parsing but is silently misrouted to the 404 branch instead of being rejected at the protocol layer.
- **Category:** Correctness bug
- **Priority:** Medium
- **Recommendation:** Replace with `method.isascii() and method.isalpha() and method.isupper()`, or validate against an explicit set of known methods.
- **Learning value:** HTTP method token rules (RFC 7230 §3.1.1); case-sensitivity in the protocol.
- **Dependencies:** None.

---

**B2 — Duplicate headers rejected too broadly**
- **Status:** `[x]`
- **Finding:** Any duplicate header raises `ValueError("Duplicate header not supported yet")`.
- **Evidence:** `http_parser.py:52–53`
- **Impact:** Legitimate requests with multiple `Accept`, `Accept-Encoding`, or `Cookie` headers are rejected with 400. Modern browsers and HTTP clients routinely send these.
- **Category:** Protocol limitation (labeled "not supported yet" — intentional, but impactful)
- **Priority:** Medium
- **Recommendation:** Accumulate repeated headers into a list, or concatenate with `, ` per RFC 7230 §3.2.2. Only reject headers that must not repeat (e.g., `Content-Length`).
- **Learning value:** RFC 7230 combining rule; which headers are singular vs repeatable.
- **Dependencies:** None.

---

**B3 — Missing `Host` header validation for HTTP/1.1**
- **Status:** `[ ]`
- **Finding:** The `Host` header is never checked for presence after parsing.
- **Evidence:** `http_parser.py:39–55`
- **Impact:** HTTP/1.1 requires `Host` (RFC 7230 §5.4). Accepting requests without it is technically incorrect.
- **Category:** Protocol limitation
- **Priority:** Medium
- **Recommendation:** After parsing headers, if `version == "HTTP/1.1"` and `"host" not in headers`, raise `ValueError("Missing required Host header")`.
- **Learning value:** Why `Host` exists (virtual hosting, proxies); differences between HTTP/1.0 and HTTP/1.1.
- **Dependencies:** None.

---

**B4 — Header size check can fire after the header terminator has already arrived**
- **Status:** `[ ]`
- **Finding:** The size check `if len(data) > max_header_size` runs after `data.extend(chunk)` inside the loop. If the final chunk both introduces `\r\n\r\n` and pushes `len(data)` past 65536, a valid request is rejected.
- **Evidence:** `http_parser.py:72–78`
- **Impact:** Edge-case false 400 for requests with headers ending near the 64 KB limit.
- **Category:** Correctness bug
- **Priority:** Low
- **Recommendation:** Check the projected size before extending: `if len(data) + len(chunk) > max_header_size: raise ValueError(...)`.
- **Learning value:** Loop invariant reasoning; why ordering of checks matters.
- **Dependencies:** None.

---

### C. Request-Body Framing

---

**C1 — `Content-Length` value not validated before `int()` conversion**
- **Status:** `[ ]`
- **Finding:** `int(request["headers"].get("content-length", "0"))` has no surrounding validation.
- **Evidence:** `http_parser.py:84`
- **Impact:** A non-integer value raises `ValueError` (caught → 400, acceptable). A negative value silently passes and produces a zero-byte body read with no error.
- **Category:** Correctness bug
- **Priority:** Medium
- **Recommendation:**
  ```python
  raw = request["headers"].get("content-length", "0")
  try:
      content_length = int(raw)
  except ValueError:
      raise ValueError("Content-Length is not an integer")
  if content_length < 0:
      raise ValueError("Content-Length must not be negative")
  ```
- **Learning value:** Defensive number parsing; difference between a parse error and a semantic error.
- **Dependencies:** None.

---

**C2 — No upper bound on `Content-Length`**
- **Status:** `[ ]`
- **Finding:** `content_length` is used with no ceiling.
- **Evidence:** `http_parser.py:84–95`
- **Impact:** A client declaring `Content-Length: 10000000000` causes the server to loop on `recv` attempting to read 10 GB.
- **Category:** Robustness issue
- **Priority:** Medium
- **Recommendation:** Add a `MAX_BODY_SIZE` constant (e.g., 1 MB) and raise `ValueError("Request body too large")` if `content_length` exceeds it. Return 413 for this specific error.
- **Learning value:** Why servers impose size limits; relationship between declared size and memory use.
- **Dependencies:** C1.

---

**C3 — `Transfer-Encoding` is silently ignored**
- **Status:** `[ ]`
- **Finding:** No check for a `transfer-encoding` header exists anywhere.
- **Evidence:** `http_parser.py` — entire file
- **Impact:** A client sending `Transfer-Encoding: chunked` with no `Content-Length` gets a silently misread (likely empty) body with no error.
- **Category:** Protocol limitation
- **Priority:** Medium
- **Recommendation:** Detect `"transfer-encoding" in headers` and return `501 Not Implemented`. Honest and correct — do not silently mishandle it.
- **Learning value:** Why chunked encoding exists; the difference between `Content-Length` and `Transfer-Encoding` framing; when 501 vs 400 is appropriate.
- **Dependencies:** None.

---

**C4 — Body bytes without a `Content-Length` header are silently kept**
- **Status:** `[ ]`
- **Finding:** `body = request["body"]` initialises from bytes received past `\r\n\r\n`. With no `Content-Length`, the loop skips, but those bytes stay in `request["body"]`.
- **Evidence:** `http_parser.py:85`
- **Impact:** Harmless for typical GET requests, but semantically wrong. A body exists only when framing metadata declares it.
- **Category:** Minor correctness issue
- **Priority:** Low
- **Recommendation:** When there is no `content-length` header, set `request["body"] = b""` explicitly.
- **Learning value:** HTTP rule that a message body exists only when declared by framing metadata.
- **Dependencies:** None.

---

### D. HTTP Responses

---

**D1 — `build_response` can be called with undefined `status` and `body`**
- **Status:** `[x]` *(catch-all `except Exception` added as part of A1)*
- **Finding:** `response = build_response(status, body)` is outside the try/except. If any exception that is not `ValueError` or `ConnectionError` is raised (e.g., `OSError`, `MemoryError`), `status` and `body` are undefined and the call raises `NameError`.
- **Evidence:** `server.py:35–46`
- **Impact:** The original error is silently lost, no response is sent, and the server crashes with an unrelated-looking `NameError`.
- **Category:** Correctness bug
- **Priority:** High
- **Recommendation:** Initialise `status` and `body` to 500 defaults before the try block, and add a catch-all `except Exception` to log unexpected errors.
- **Learning value:** Variable scope inside try/except; why a last-resort handler matters; 500 vs 400 semantics.
- **Dependencies:** None.

---

**D2 — `Content-Type` is hardcoded as `text/plain`**
- **Status:** `[ ]`
- **Finding:** `b"Content-Type: text/plain\r\n"` is unconditional in `build_response`.
- **Evidence:** `response.py:4`
- **Impact:** No way to serve JSON, HTML, or binary content without modifying the function.
- **Category:** Design improvement
- **Priority:** Low
- **Recommendation:** Add an optional `content_type=b"text/plain"` parameter to `build_response`.
- **Learning value:** How `Content-Type` is used; MIME types.
- **Dependencies:** None.

---

### E. Routing and Application Behavior

---

**E1 — `404 Not Found` returned for known paths with an unsupported method**
- **Status:** `[ ]`
- **Finding:** The `else` branch in the router catches both unrecognised paths and wrong methods on recognised paths. `POST /` returns 404 instead of 405.
- **Evidence:** `router.py:13–15`
- **Impact:** Incorrect status code. RFC 7231 §6.5.5 requires 405 when the method is not allowed, and the response must include an `Allow` header.
- **Category:** Protocol correctness
- **Priority:** Medium
- **Recommendation:** Restructure routing into two passes: check if the path exists (→ 404), then check if the method is supported for that path (→ 405 with `Allow:` header).
- **Learning value:** 404 vs 405 semantics; the `Allow` response header.
- **Dependencies:** None.

---

**E2 — Router couples method and path into a single conditional chain**
- **Status:** `[ ]`
- **Finding:** Each route is a single `if method == "..." and target == "..."` branch.
- **Evidence:** `router.py:5–15`
- **Impact:** Adding routes or distinguishing 404 from 405 requires restructuring the entire chain.
- **Category:** Design improvement
- **Priority:** Medium
- **Recommendation:** Use a dict-of-dicts like `routes = {"/": {"GET": handler_fn}}` to make path-then-method lookup explicit and extensible.
- **Learning value:** Dispatch tables; separating route registration from route execution.
- **Dependencies:** None. Pairs naturally with E1.

---

### F. Testing and Observability

---

**F1 — No automated tests**
- **Status:** `[ ]`
- **Finding:** No test files exist. The only documented testing method is a manual raw socket one-liner in a comment.
- **Evidence:** No `tests/` directory; `server.py:51` comment
- **Impact:** Changes cannot be safely verified without running the server manually.
- **Category:** Testing gap
- **Priority:** High
- **Recommendation:** Write unit tests for `parse_request_line`, `parse_request`, and `read_request_body` using `pytest` and static byte strings. These functions require no live socket.
- **Learning value:** Testing bytes-level logic; value of separating I/O from parsing.
- **Dependencies:** None.

---

**F2 — No raw-socket test harness**
- **Status:** `[ ]`
- **Finding:** No test client exists for sending malformed or fragmented requests.
- **Evidence:** No `test_client.py` or equivalent
- **Impact:** Protocol-level edge cases (partial reads, truncated headers, invalid framing) cannot be tested with `curl`.
- **Category:** Testing gap
- **Priority:** Medium
- **Recommendation:** Write a small `test_client.py` that sends crafted byte strings over a raw socket and asserts on the response status line.
- **Learning value:** Simulating protocol-level misbehavior; difference between a compliant client and a fuzzing client.
- **Dependencies:** F1.

---

**F3 — No structured request logging**
- **Status:** `[ ]`
- **Finding:** Five separate `print` statements emit request fields with no timestamp or connection context.
- **Evidence:** `server.py:29–33`
- **Impact:** Hard to follow once a connection loop is added (A1). No record of what status was sent.
- **Category:** Observability
- **Priority:** Low
- **Recommendation:** Emit one structured log line per request: method, target, version, response status, content-length.
- **Learning value:** Access log format; structured vs ad-hoc logging.
- **Dependencies:** A1.

---

## Milestones

Milestones are ordered by dependency and learning value. Complete them in order.

---

### Milestone 0 — Pre-flight fixes

**Findings addressed:** A2, B4, C1, C3, D1

**Problem:** Several bugs cause incorrect behavior or silent crashes today, and are cheap to fix before adding anything new.

**Target behavior after change:**
- Unexpected exceptions return 500 instead of crashing with `NameError`.
- `SO_REUSEADDR` allows immediate server restart.
- Negative `Content-Length` is rejected with 400.
- Non-integer `Content-Length` gives a clear error message.
- `Transfer-Encoding` presence returns 501.
- Header size check does not fire on valid requests at the size boundary.

**Files:** `server.py`, `http_parser.py`

**Acceptance tests:**
- `GET /` returns 200. Existing behavior unchanged.
- Kill the server and restart within 5 seconds. It binds successfully.
- Send `Content-Length: -5`. Receive 400.
- Send `Content-Length: abc`. Receive 400.
- Send `Transfer-Encoding: chunked`. Receive 501.
- Temporarily raise `RuntimeError` inside the try block. Server returns 500, does not crash.

**Concepts learned:** Exception scope, socket options, defensive parsing, 5xx vs 4xx.

---

### Milestone 1 — Unit tests for parsing

**Findings addressed:** F1

**Problem:** There is no way to verify parsing logic without running the server manually.

**Target behavior:** `pytest` can be run and tests all parsing functions with static byte strings. No live socket required.

**Files:** new `tests/test_http_parser.py`

**Acceptance tests:**
- `parse_request_line("GET / HTTP/1.1")` returns `{"method": "GET", "target": "/", "version": "HTTP/1.1"}`.
- Malformed request lines raise `ValueError`.
- Valid headers parse into a lowercased dict.
- Negative or non-integer `Content-Length` raises `ValueError`.
- `Content-Length` over the limit raises `ValueError`.

**Concepts learned:** Testing bytes-level logic; separating I/O from parsing.

**Dependencies:** Milestone 0.

---

### Milestone 2 — Server accept loop with connection isolation

**Findings addressed:** A1, A3, A5

**Problem:** The server handles one request and exits. One bad connection can kill the server.

**Target behavior:**
- Server runs continuously and accepts sequential connections.
- An exception from one connection is logged and the server continues.
- `Ctrl-C` exits cleanly and closes the server socket.

**Files:** `server.py`

**Acceptance tests:**
- Two sequential `curl` requests both receive correct responses.
- Close a connection mid-headers (raw socket). Server logs the error and remains running.
- `Ctrl-C` exits without leaving the port occupied.

**Concepts learned:** Accept loops; per-connection isolation; why one connection's failure must not kill the server.

**Dependencies:** Milestone 0.

---

### Milestone 3 — Read timeout and request-size limits

**Findings addressed:** A4, C2

**Problem:** A stalled client can hold the server forever. A large declared body can exhaust memory.

**Target behavior:**
- Each connection has a 30-second read deadline.
- `Content-Length` above 1 MB is rejected with 413.
- A timed-out connection returns 408 (or closes silently).

**Files:** `server.py`, `http_parser.py`

**Acceptance tests:**
- Open a raw socket, send nothing. After 30 s, connection closes or a 408 is received.
- Send `Content-Length: 2000000`. Receive 413 without reading the body.
- Send a body that matches a declared small `Content-Length`. Receive 200.

**Concepts learned:** Socket timeouts; 408 vs 400 vs 413; why servers impose size limits.

**Dependencies:** Milestone 2.

---

### Milestone 4 — Correct routing with 404 / 405 distinction

**Findings addressed:** E1, E2

**Problem:** An unsupported method on a known path incorrectly returns 404.

**Target behavior:**
- `GET /` → 200
- `POST /` → 405 with `Allow: GET`
- `GET /nonexistent` → 404

**Files:** `router.py`, `response.py` (to support additional response headers)

**Acceptance tests:**
- `curl -X POST http://localhost:8000/` returns 405 with an `Allow: GET` header.
- `curl http://localhost:8000/unknown` returns 404.
- `curl http://localhost:8000/` returns 200.

**Concepts learned:** 404 vs 405 semantics; the `Allow` header; dispatch-table routing.

**Dependencies:** Milestone 0.

---

### Milestone 5 — Host header validation and method case enforcement

**Findings addressed:** B1, B3

**Problem:** HTTP/1.1 requires a `Host` header. Lowercase methods are silently misrouted.

**Target behavior:**
- HTTP/1.1 request without `Host` → 400.
- Request line with a lowercase method → 400.

**Files:** `http_parser.py`

**Acceptance tests:**
- `parse_request` on an HTTP/1.1 request with no `Host` header raises `ValueError`.
- `parse_request_line("get / HTTP/1.1")` raises `ValueError`.
- `parse_request_line("GET / HTTP/1.1")` still succeeds.

**Concepts learned:** HTTP/1.1 requirements vs HTTP/1.0; method token rules.

**Dependencies:** Milestone 1.

---

### Milestone 6 — Raw-socket test harness

**Findings addressed:** F2

**Problem:** Protocol-level edge cases cannot be tested with `curl`.

**Target behavior:** A `tests/test_client.py` script sends crafted byte strings over a raw socket and checks the response status line.

**Files:** new `tests/test_client.py`

**Example test cases:**
- Send a request truncated before `\r\n\r\n`. Assert 400 or connection close.
- Send a valid request in 1-byte fragments. Assert 200.
- Send `Content-Length: abc`. Assert 400.
- Send `Content-Length: -1`. Assert 400.

**Concepts learned:** TCP fragmentation; how framing interacts with partial reads.

**Dependencies:** Milestone 2, Milestone 1.

---

### Milestone 7 — Duplicate header handling

**Findings addressed:** B2

**Problem:** Duplicate headers are rejected too broadly, breaking real client requests.

**Target behavior:**
- Multiple headers with the same name are accumulated into a list (or combined with `, `).
- Singular-only headers (e.g., `Content-Length`) still reject duplicates.

**Files:** `http_parser.py`

**Acceptance tests:**
- A request with two `Accept` headers parses cleanly.
- A request with two `Content-Length` headers returns 400.

**Concepts learned:** RFC 7230 combining rule; which headers are singular vs repeatable.

**Dependencies:** Milestone 5.

---

### Milestone 8 — Minor polish

**Findings addressed:** A5, C4, D2, F3

**Problem:** Small rough edges in logging, body semantics, resource cleanup, and response headers.

**Target behavior:**
- One structured log line per request (method, target, status).
- Body is explicitly `b""` when no `Content-Length` header is present.
- `build_response` accepts an optional `content_type` parameter.
- Server socket closed in a `finally` block.

**Files:** `server.py`, `http_parser.py`, `response.py`

**Dependencies:** Milestones 2, 3.

---

## Out of Scope (Intentionally)

These will not be implemented. The server will return `501 Not Implemented` for protocol features in this list, and simply not support the others.

| Feature | Decision |
|---------|----------|
| `Transfer-Encoding: chunked` | Return 501 explicitly. Body framing without Content-Length is out of scope. |
| HTTP/2, HTTP/3 | Different protocol entirely. Out of scope. |
| TLS / HTTPS | Meaningful but large. Deferred indefinitely. |
| `CONNECT` method | Tunnel semantics are out of scope. |
| Cookie parsing | Application layer. Out of scope. |
| Multipart bodies | Complex framing. No proportionate learning value. |
| URL decoding / query strings | Useful but orthogonal to the core framing work. |
| HTTP pipelining | Keep-alive without pipelining is sufficient. Pipelining adds ordering complexity. |
| `gzip` / `deflate` encoding | Adds a `zlib` dependency. Deferred. |
| Virtual hosting | `Host` validation is enough for this scope. |
