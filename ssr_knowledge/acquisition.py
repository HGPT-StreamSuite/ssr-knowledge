"""Bounded HTTP collection from operator-reviewed exact URLs; no link traversal."""
from __future__ import annotations

import codecs
import http.client
import ipaddress
import json
import re
import socket
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from email.message import Message
from html.parser import HTMLParser
from typing import Any

from .catalog import Catalog, SOURCE_TYPES, canonical, digest, identifier, required_text
from .contracts import ContractError

USER_AGENT = "SSRKnowledge/0.1 (+https://github.com/HGPT-StreamSuite/ssr-knowledge; local reference research)"
ROBOTS_AGENTS = ("SSRKnowledge", "GPTBot", "ChatGPT-User")
EXTRACTOR_VERSION = "html-subtree-v1"


def safe_url(value: Any) -> str:
    required_text(value, "HTTPS URL", 2000)
    parsed = urllib.parse.urlsplit(value)
    try:
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.port not in (None, 443) or parsed.fragment or "\\" in value
                or any(ord(c) < 33 for c in value) or not parsed.hostname.isascii()):
            raise ValueError
    except ValueError as exc:
        raise ContractError("only credential-free public HTTPS URLs on port 443 without fragments are supported") from exc
    host = parsed.hostname.lower()
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is None and (host == "localhost" or "." not in host or host.endswith((".local", ".internal"))):
        raise ContractError("public hostname required")
    if address is not None and (not address.is_global or "%" in host):
        raise ContractError("non-public address forbidden")
    authority = f"[{host}]" if ":" in host else host
    return urllib.parse.urlunsplit(("https", authority, parsed.path or "/", parsed.query, ""))


def validate_manifest(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, dict) or set(value) != {"manifest_version", "game", "sources"}:
        raise ContractError("manifest needs manifest_version, game, sources")
    if value["manifest_version"] != 1 or value["game"] != "PEAK:3527290":
        raise ContractError("unsupported manifest version or game")
    if not isinstance(value["sources"], list) or not 1 <= len(value["sources"]) <= 20:
        raise ContractError("one to twenty exact sources required")
    result = []
    for item in value["sources"]:
        fields = {"source_id", "url", "source_type", "title", "language", "declared_version", "selector", "policy", "interval_seconds"}
        if not isinstance(item, dict) or set(item) != fields:
            raise ContractError("source must contain exactly the documented fields")
        item = json.loads(canonical(item))
        identifier(item["source_id"])
        item["url"] = safe_url(item["url"])
        if item["source_type"] not in SOURCE_TYPES or item["language"] != "en":
            raise ContractError("invalid source_type or language (this batch uses English)")
        for field in ("title", "declared_version"):
            required_text(item[field], field)
        delay = item["interval_seconds"]
        if isinstance(delay, bool) or not isinstance(delay, (int, float)) or not 2 <= delay <= 60:
            raise ContractError("interval_seconds must be 2 to 60")
        selector = item["selector"]
        if not isinstance(selector, dict) or set(selector) not in ({"tag"}, {"tag", "attribute", "value"}):
            raise ContractError("selector requires tag and optionally attribute/value")
        if selector["tag"] not in {"main", "article", "div", "section", "body"}:
            raise ContractError("unsupported selector tag")
        if "attribute" in selector:
            if selector["attribute"] not in {"id", "class"}:
                raise ContractError("selector attribute must be id or class")
            required_text(selector["value"], "selector value", 200)
        policy = item["policy"]
        if not isinstance(policy, dict) or set(policy) != {"allow_fetch", "reviewed_at", "terms_url", "notes"}:
            raise ContractError("policy requires allow_fetch, reviewed_at, terms_url, notes")
        if not isinstance(policy["allow_fetch"], bool):
            raise ContractError("allow_fetch must be boolean")
        safe_url(policy["terms_url"])
        required_text(policy["notes"], "policy notes")
        try:
            reviewed = datetime.fromisoformat(policy["reviewed_at"])
            if reviewed.tzinfo is None or not 0 <= (datetime.now(timezone.utc) - reviewed).total_seconds() <= 31 * 86400:
                raise ValueError
        except (TypeError, ValueError) as exc:
            raise ContractError("policy reviewed_at must be timezone-aware and within the past 31 days") from exc
        result.append(item)
    if len({s["source_id"] for s in result}) != len(result) or len({s["url"] for s in result}) != len(result):
        raise ContractError("duplicate source_id or canonical URL in manifest")
    return result


def robots_policy(text: str, url: str) -> tuple[bool, float, str]:
    """Merge equal-specificity groups, support Allow, *, $, delay and request-rate.

    Conservatively check the local bot and OpenAI user/training identities too;
    renaming our user-agent never bypasses an explicit AI-agent restriction.
    """
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    agents: list[str] = []
    rules: list[tuple[str, str]] = []
    for line in text.lstrip("\ufeff").splitlines():
        line = line.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        key, val = [p.strip() for p in line.split(":", 1)]
        key = key.lower()
        if key == "user-agent":
            if rules:
                groups.append((agents, rules))
                agents, rules = [], []
            agents.append(val.lower())
        elif agents:
            rules.append((key, val))
    if agents:
        groups.append((agents, rules))
    parsed = urllib.parse.urlsplit(url)
    target = urllib.parse.quote(parsed.path, safe="/%:@!$&'()*+,;=-._~") + ("?" + parsed.query if parsed.query else "")
    delay = 0.0
    for identity in ROBOTS_AGENTS:
        matching = [(max((len(a) if a != "*" else 0) for a in aa if a == "*" or a in identity.lower()), rr)
                    for aa, rr in groups if any(a == "*" or a in identity.lower() for a in aa)]
        if not matching:
            continue
        specificity = max(score for score, _ in matching)
        best = (-1, True)
        for score, rr in matching:
            if score != specificity:
                continue
            for key, val in rr:
                if key in {"allow", "disallow"} and val:
                    pattern = "^" + ".*".join(re.escape(p) for p in val.rstrip("$").split("*")) + ("$" if val.endswith("$") else "")
                    if re.search(pattern, target):
                        candidate = (len(val.replace("*", "").rstrip("$")), key == "allow")
                        best = max(best, candidate)
                elif key == "crawl-delay":
                    try:
                        delay = max(delay, float(val))
                    except ValueError:
                        return False, delay, "invalid crawl-delay; fail closed"
                elif key == "request-rate":
                    try:
                        requests, seconds = map(float, val.split("/"))
                        delay = max(delay, seconds / requests)
                    except (ValueError, ZeroDivisionError):
                        return False, delay, "invalid request-rate; fail closed"
                elif key == "content-signal":
                    signals = dict(p.strip().lower().split("=", 1) for p in val.split(",") if "=" in p)
                    if signals.get("ai-input") == "no" or signals.get("search") == "no" or signals.get("use") == "reference":
                        return False, delay, "content signal restricts local full-text/AI use"
        if not best[1]:
            return False, delay, f"robots disallows {identity}"
    if not 0 <= delay <= 3600:
        return False, delay, "unsupported crawl-delay; fail closed"
    return True, delay, "robots permits reviewed exact URL"


class BodyExtractor(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
    SKIP = {"script", "style", "noscript", "nav", "footer", "form", "svg", "template"}
    BLOCK = {"p", "div", "section", "article", "main", "h1", "h2", "h3", "h4", "li", "tr", "br"}

    def __init__(self, selector: dict[str, str]) -> None:
        super().__init__(convert_charrefs=True)
        self.selector = selector
        self.stack: list[tuple[str, bool, bool]] = []
        self.parts: list[str] = []
        self.titles: list[str] = []
        self.meta: dict[str, str] = {}
        self.matched = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        selected = tag == self.selector["tag"]
        if "attribute" in self.selector:
            attr = values.get(self.selector["attribute"], "") or ""
            selected = selected and (self.selector["value"] in attr.split() if self.selector["attribute"] == "class"
                                     else self.selector["value"] == attr)
        if selected:
            self.matched += 1
        active = selected or (self.stack[-1][1] if self.stack else False)
        hidden = tag in self.SKIP or "hidden" in values or values.get("aria-hidden") == "true" or (self.stack[-1][2] if self.stack else False)
        if tag == "meta":
            name = values.get("property") or values.get("name") or ""
            if name in {"article:modified_time", "article:published_time", "dc.modified", "dc.date", "mw:revisionId"}:
                self.meta[name] = values.get("content") or ""
        if active and not hidden and tag in self.BLOCK:
            self.parts.append("\n")
        if tag not in self.VOID:
            self.stack.append((tag, active, hidden))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag in self.VOID:
            return
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                if self.stack[index][1] and not self.stack[index][2] and tag in self.BLOCK:
                    self.parts.append("\n")
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if self.stack and self.stack[-1][0] == "title":
            self.titles.append(data)
        if self.stack and self.stack[-1][1] and not self.stack[-1][2]:
            self.parts.append(data)

    def body(self) -> str:
        if self.matched != 1:
            raise ContractError(f"selector must match exactly one element; matched {self.matched}")
        text = "\n".join(" ".join(line.split()) for line in "".join(self.parts).splitlines() if line.strip())
        if len(text) < 40:
            raise ContractError("extracted body too short; inspect selector or access challenge")
        return text


@dataclass
class Response:
    status: int
    headers: dict[str, str]
    raw: bytes


def decode_robots(response: Response) -> str:
    """Reject challenge/error documents before interpreting a 200 as robots rules."""
    if response.headers.get("content-encoding", "identity").strip().lower() != "identity":
        raise ContractError("robots unsupported content encoding; fail closed")
    content_type = Message()
    content_type["content-type"] = response.headers.get("content-type", "")
    if content_type.get_content_type().lower() != "text/plain":
        raise ContractError("robots must be text/plain, not HTML/challenge content; fail closed")
    charset = content_type.get_content_charset() or "utf-8"
    try:
        encoding = codecs.lookup(charset).name
    except LookupError as exc:
        raise ContractError("robots unsupported charset; fail closed") from exc
    if encoding not in {"utf-8", "utf-8-sig", "ascii"}:
        raise ContractError("robots unsupported charset; expected UTF-8 or ASCII; fail closed")
    try:
        text = response.raw.decode("ascii" if encoding == "ascii" else "utf-8-sig", errors="strict")
    except UnicodeError as exc:
        raise ContractError("robots invalid text encoding; fail closed") from exc
    if any(ord(c) < 32 and c not in "\t\r\n" or ord(c) == 127 for c in text):
        raise ContractError("robots contains non-text control bytes; fail closed")
    lines = [line.split("#", 1)[0].strip() for line in text.splitlines()]
    active = [line for line in lines if line]
    # Empty/whitespace/comment-only robots are legitimate. A challenge page or an
    # unstructured error message is not an empty rule set, even if mislabeled plain text.
    if any(re.search(r"<\s*(?:!doctype|/?[a-z][\w:-]*\b)[^>]*>", line, re.I) for line in active):
        raise ContractError("robots HTML/XML challenge detected; fail closed")
    if any(not re.match(r"^[A-Za-z][A-Za-z0-9_-]*\s*:", line) for line in active):
        raise ContractError("robots unstructured error/challenge content; fail closed")
    known = {"user-agent", "allow", "disallow", "sitemap", "host", "crawl-delay", "request-rate",
             "content-signal", "clean-param", "visit-time"}
    if active and not any(line.split(":", 1)[0].strip().lower() in known for line in active):
        raise ContractError("robots contains no supported directives; fail closed")
    return text


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_: Any, **__: Any) -> None:
        return None


def _public_peer(host: str) -> tuple[int, tuple[Any, ...]]:
    """Resolve once, reject the entire answer if any address is not public, then pin one."""
    answers = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP)
    peers = []
    for family, socktype, protocol, _, sockaddr in answers:
        if family not in {socket.AF_INET, socket.AF_INET6} or socktype != socket.SOCK_STREAM or protocol != socket.IPPROTO_TCP:
            raise ContractError("DNS returned an unsupported socket address")
        ip = ipaddress.ip_address(sockaddr[0])
        if not ip.is_global or "%" in str(ip) or ip.version != (4 if family == socket.AF_INET else 6):
            raise ContractError("DNS resolved to a non-public address")
        # Rebuild a numeric endpoint, never reuse resolver-controlled host/port/scope fields.
        endpoint = (str(ip), 443) if family == socket.AF_INET else (str(ip), 443, 0, 0)
        peers.append((family, endpoint))
    if not peers:
        raise ContractError("DNS returned no public addresses")
    # One TCP/TLS attempt per HTTP attempt preserves the timeout bound. Prefer IPv4
    # when both families exist; the outer bounded retry may obtain a new validated peer.
    return next((peer for peer in peers if peer[0] == socket.AF_INET), peers[0])


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, host: str, *, expected_host: str, peer: tuple[int, tuple[Any, ...]], **kwargs: Any) -> None:
        super().__init__(host, **kwargs)
        if self.host != expected_host or self.port != 443:
            raise ContractError("connection hostname differs from the validated origin")
        if not self._context.check_hostname or self._context.verify_mode != ssl.CERT_REQUIRED:
            raise ContractError("verified TLS context with hostname checking is required")
        self._peer = peer

    def connect(self) -> None:
        if self._tunnel_host:
            raise ContractError("proxy tunnels are unsupported by the pinned-IP transport")
        family, endpoint = self._peer
        raw = socket.socket(family, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        try:
            raw.settimeout(self.timeout)
            raw.connect(endpoint)  # Numeric validated IP: no hostname resolution here.
            # Keep the original hostname for SNI and certificate hostname validation.
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


class _PinnedHTTPSHandler(urllib.request.HTTPSHandler):
    def __init__(self, host: str, peer: tuple[int, tuple[Any, ...]], context: ssl.SSLContext) -> None:
        super().__init__(context=context)
        self._expected_host, self._peer = host, peer

    def https_open(self, req: urllib.request.Request) -> Any:
        def connection(host: str, **kwargs: Any) -> _PinnedHTTPSConnection:
            return _PinnedHTTPSConnection(host, expected_host=self._expected_host, peer=self._peer, **kwargs)
        return self.do_open(connection, req, context=self._context)


class HttpTransport:
    def __init__(self) -> None:
        self._context = ssl.create_default_context()
        self._context.set_alpn_protocols(["http/1.1"])

    def get(self, url: str, max_bytes: int) -> Response:
        # A proxy resolves/connects on our behalf, so a local public-IP check cannot
        # constrain its destination. Fail closed instead of silently bypassing it or
        # tunneling a hostname that the proxy could resolve differently.
        proxies = urllib.request.getproxies()
        if any(proxies.get(kind) for kind in ("http", "https", "all")):
            raise ContractError("configured HTTP/HTTPS/ALL proxy unsupported by pinned-IP transport; no request sent")
        host = urllib.parse.urlsplit(safe_url(url)).hostname
        peer = _public_peer(host)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect(),
                                             _PinnedHTTPSHandler(host, peer, self._context))
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.9", "Accept-Encoding": "identity"})
        try:
            response = opener.open(req, timeout=15)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            if response.status != 200:
                return Response(response.status, {k.lower(): v for k, v in response.headers.items()}, b"")
            raw = response.read(max_bytes + 1)
            if len(raw) > max_bytes:
                raise ContractError("response exceeds byte limit")
            return Response(response.status, {k.lower(): v for k, v in response.headers.items()}, raw)


class Collector:
    def __init__(self, catalog: Catalog, *, transport: Any = None, sleep: Any = time.sleep,
                 clock: Any = time.time) -> None:
        self.catalog = catalog
        self.transport = transport or HttpTransport()
        self.sleep, self.clock = sleep, clock

    def _cooldown(self, origin: str, seconds: float) -> None:
        with self.catalog.db:
            self.catalog.db.execute("""INSERT INTO throttles VALUES(?,?) ON CONFLICT(origin)
                DO UPDATE SET next_at=max(next_at,excluded.next_at)""", (origin, self.clock() + seconds))

    def _reserve(self, origin: str, delay: float) -> None:
        db = self.catalog.db
        with db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT next_at FROM throttles WHERE origin=?", (origin,)).fetchone()
            now = self.clock()
            wait = max(0.0, row[0] - now) if row else 0.0
            if wait > 30:
                raise ContractError("deferred: host cooldown exceeds 30 seconds; retry later")
            db.execute("INSERT INTO throttles VALUES(?,?) ON CONFLICT(origin) DO UPDATE SET next_at=excluded.next_at",
                       (origin, now + wait + delay))
        if wait:
            self.sleep(wait)

    def _get(self, url: str, source_id: str, stage: str, delay: float, max_bytes: int) -> Response:
        parsed = urllib.parse.urlsplit(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        for attempt in range(1, 4):
            self._reserve(origin, delay)
            try:
                response = self.transport.get(url, max_bytes)
            except (OSError, TimeoutError) as exc:
                self.catalog.event(source_id, "http_attempt", {"url": url, "stage": stage, "attempt": attempt,
                                                            "error": type(exc).__name__})
                if attempt == 3:
                    raise ContractError("network failure after three attempts") from exc
                self._cooldown(origin, max(delay, 2 ** attempt))
                continue
            self.catalog.event(source_id, "http_attempt", {"url": url, "stage": stage, "attempt": attempt,
                                                        "http_status": response.status})
            if response.status not in {429, 500, 502, 503, 504}:
                return response
            retry = max(delay, 2 ** attempt)
            value = response.headers.get("retry-after")
            if value:
                try:
                    retry = max(retry, float(value))
                except ValueError:
                    try:
                        retry = max(retry, parsedate_to_datetime(value).timestamp() - self.clock())
                    except (TypeError, ValueError, OverflowError):
                        retry = max(retry, 60)  # Unknown server instruction: do not guess a shorter wait.
            self._cooldown(origin, retry)
            if retry > 30 or attempt == 3:
                return response
        raise AssertionError("unreachable")

    def collect(self, sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
        results = []
        for source in sources:
            self.catalog.register_source(source)
            sid, url = source["source_id"], source["url"]
            context: dict[str, Any] = {"url": url, "policy": source["policy"], "extractor_version": EXTRACTOR_VERSION}
            try:
                if not source["policy"]["allow_fetch"]:
                    raise ContractError("policy blocked: " + source["policy"]["notes"])
                parsed = urllib.parse.urlsplit(url)
                robots_url = f"https://{parsed.netloc}/robots.txt"
                robots = self._get(robots_url, sid, "robots", source["interval_seconds"], 512_000)
                context["robots_url"], context["robots_http_status"] = robots_url, robots.status
                if robots.status == 200:
                    context["robots_sha256"] = digest(robots.raw)
                    context["robots_headers"] = {k: robots.headers[k] for k in ("content-type", "content-encoding") if k in robots.headers}
                    robots_text = decode_robots(robots)
                    context["robots_text"] = robots_text
                    allowed, crawl_delay, reason = robots_policy(robots_text, url)
                    if not allowed:
                        raise ContractError(reason)
                elif robots.status in {404, 410}:
                    crawl_delay = 0
                    context["robots_note"] = "no robots file (404/410); operator-reviewed terms still apply"
                else:
                    raise ContractError(f"robots unavailable HTTP {robots.status}; fail closed")
                delay = max(source["interval_seconds"], crawl_delay)
                # The preceding robots request must also respect its newly discovered crawl delay.
                self._cooldown(f"https://{parsed.netloc}", delay)
                response = self._get(url, sid, "page", delay, 2_000_000)
                context["http_status"] = response.status
                if response.status != 200:
                    raise ContractError(f"page HTTP {response.status}; no redirects/auth/challenge bypass")
                content_type = response.headers.get("content-type", "")
                if "text/html" not in content_type.lower() or response.headers.get("content-encoding", "identity") != "identity":
                    raise ContractError("only uncompressed text/html accepted")
                charset = re.search(r"charset=([\w-]+)", content_type, re.I)
                encoding = charset.group(1) if charset else "utf-8"
                codecs.lookup(encoding)
                html = response.raw.decode(encoding, errors="strict")
                if re.search(r"<title>\s*(just a moment|access denied|attention required|sign in)", html, re.I):
                    raise ContractError("access challenge detected; no bypass")
                parser = BodyExtractor(source["selector"])
                parser.feed(html)
                parser.close()
                body = parser.body()
                context.update({"headers": {k: response.headers[k] for k in ("content-type", "etag", "last-modified", "date") if k in response.headers},
                                "title": "".join(parser.titles).strip(), "page_dates": parser.meta,
                                "declared_version": source["declared_version"], "selector": source["selector"]})
                result = self.catalog.save_snapshot(source, response.raw, body, context)
                self.catalog.event(sid, "collection_result", {**context, **result})
                results.append({**result, "url": url})
            except (ContractError, UnicodeError, LookupError, ValueError) as exc:
                result = {"source_id": sid, "url": url, "state": "blocked_or_failed", "error": str(exc)}
                self.catalog.event(sid, "collection_result", {**context, **result})
                results.append(result)
        return results
