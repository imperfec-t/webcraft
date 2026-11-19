"""Load what an audit or teardown inspects: a URL, an HTML file or a folder."""
from __future__ import annotations

import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import __version__, dom

USER_AGENT = f"Mozilla/5.0 (compatible; webcraft/{__version__}; site audit)"
MAX_BYTES = 6 * 1024 * 1024
ASSET_LIMIT = 16
SKIP_DIRS = {"node_modules", ".git", ".svn", "vendor", "__pycache__", ".next", ".cache"}


@dataclass
class Response:
    status: int
    url: str
    headers: Dict[str, str]
    text: str


_SSL_CTX = None
last_error: Optional[str] = None


def _ssl_context():
    """Prefer the OS certificate verifier (truststore), then certifi, then Python's default.
    Python's bundled store fails on servers that omit intermediate certificates."""
    global _SSL_CTX
    if _SSL_CTX is None:
        try:
            import truststore  # optional: pip install webcraft[tls]
            _SSL_CTX = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        except ImportError:
            try:
                import certifi
                _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
            except ImportError:
                _SSL_CTX = ssl.create_default_context()
    return _SSL_CTX


def fetch(url: str, method: str = "GET", timeout: float = 15.0, max_bytes: int = MAX_BYTES) -> Optional[Response]:
    global last_error
    req = urllib.request.Request(url, method=method, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,text/css,application/javascript,*/*;q=0.8",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as r:
            body = r.read(max_bytes) if method != "HEAD" else b""
            headers = {k.lower(): v for k, v in r.headers.items()}
            return Response(r.status, r.geturl(), headers, _decode(body, headers))
    except urllib.error.HTTPError as e:
        try:
            body = e.read(max_bytes) if method != "HEAD" else b""
        except Exception:
            body = b""
        headers = {k.lower(): v for k, v in (e.headers or {}).items()}
        return Response(e.code, e.geturl() or url, headers, _decode(body, headers))
    except Exception as e:
        reason = getattr(e, "reason", e)
        last_error = f"{type(reason).__name__}: {reason}"
        if isinstance(reason, ssl.SSLCertVerificationError):
            last_error += " (install the OS trust store bridge: pip install truststore)"
        return None


def _decode(body: bytes, headers: Dict[str, str]) -> str:
    m = re.search(r"charset=([\w-]+)", headers.get("content-type", ""), re.I)
    enc = m.group(1) if m else "utf-8"
    try:
        return body.decode(enc, errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


@dataclass
class Page:
    location: str                      # URL or path, for display
    html: str
    tree: dom.Node
    url: Optional[str] = None          # final URL when fetched
    path: Optional[Path] = None        # local file
    status: Optional[int] = None
    headers: Dict[str, str] = field(default_factory=dict)
    css: List[Tuple[str, str]] = field(default_factory=list)   # (where, text)
    js: List[Tuple[str, str]] = field(default_factory=list)
    script_srcs: List[str] = field(default_factory=list)
    stylesheet_hrefs: List[str] = field(default_factory=list)

    @property
    def is_https(self) -> bool:
        return bool(self.url and self.url.startswith("https://"))

    def all_css(self) -> str:
        return "\n".join(t for _, t in self.css)

    def all_js(self) -> str:
        return "\n".join(t for _, t in self.js)


@dataclass
class Site:
    kind: str                         # url, file, dir
    target: str
    pages: List[Page]
    root: Optional[Path] = None
    origin: Optional[str] = None
    errors: List[str] = field(default_factory=list)


def is_url(target: str) -> bool:
    return bool(re.match(r"^https?://", target, re.I))


def _same_origin(a: str, b: str) -> bool:
    pa, pb = urllib.parse.urlsplit(a), urllib.parse.urlsplit(b)
    return (pa.scheme, pa.netloc.lower().removeprefix("www.")) == (pb.scheme, pb.netloc.lower().removeprefix("www."))


def _build_page(location: str, html: str, url: Optional[str] = None, path: Optional[Path] = None,
                root: Optional[Path] = None, status: Optional[int] = None,
                headers: Optional[Dict[str, str]] = None, fetch_assets: bool = True) -> Page:
    tree = dom.parse(html)
    page = Page(location, html, tree, url=url, path=path, status=status, headers=headers or {})
    for st in tree.find_all("style"):
        page.css.append(("inline <style>", st.raw_text()))
    for n in tree.find_all("script"):
        src = n.get("src")
        if src:
            page.script_srcs.append(src)
        elif n.get("type", "").lower() not in ("application/ld+json", "application/json", "importmap"):
            page.js.append(("inline <script>", n.raw_text()))
    for n in tree.find_all("link"):
        rel = n.get("rel").lower().split()
        if "stylesheet" in rel and n.get("href"):
            page.stylesheet_hrefs.append(n.get("href"))
        elif "preload" in rel and n.get("as") == "style" and n.get("href"):
            page.stylesheet_hrefs.append(n.get("href"))
    for n in tree.iter():
        if n.has("style") and n.get("style").strip():
            page.css.append(("style attribute", f"x{{{n.get('style')}}}"))
    if fetch_assets:
        _load_assets(page, root)
    return page


def _load_assets(page: Page, root: Optional[Path]) -> None:
    budget = ASSET_LIMIT
    for kind, refs in (("css", page.stylesheet_hrefs), ("js", page.script_srcs)):
        for ref in refs:
            if budget <= 0:
                return
            text = None
            if page.url:
                absolute = urllib.parse.urljoin(page.url, ref)
                if not _same_origin(absolute, page.url):
                    continue
                r = fetch(absolute, max_bytes=2 * 1024 * 1024)
                if r and r.status < 400:
                    text = r.text
                where = absolute
            elif page.path:
                local = resolve_local(ref, page.path, root)
                if local is None or not local.is_file():
                    continue
                text = local.read_text(encoding="utf-8", errors="replace")
                where = str(local)
            if text is None:
                continue
            budget -= 1
            (page.css if kind == "css" else page.js).append((where, text))


def resolve_local(ref: str, page_path: Path, root: Optional[Path]) -> Optional[Path]:
    if re.match(r"^(?:[a-z]+:)?//", ref, re.I) or ref.startswith(("data:", "mailto:", "tel:", "javascript:", "#")):
        return None
    ref = urllib.parse.unquote(ref.split("#", 1)[0].split("?", 1)[0])
    if not ref:
        return None
    if ref.startswith("/"):
        return (root or page_path.parent) / ref.lstrip("/")
    return (page_path.parent / ref).resolve()


def load(target: str, max_pages: int = 1, fetch_assets: bool = True) -> Site:
    if is_url(target):
        return _load_url(target, max_pages, fetch_assets)
    p = Path(target).expanduser()
    if p.is_file():
        root = p.parent
        html = p.read_text(encoding="utf-8", errors="replace")
        return Site("file", target, [_build_page(str(p), html, path=p.resolve(), root=root.resolve(),
                                                 fetch_assets=fetch_assets)], root=root.resolve())
    if p.is_dir():
        root = p.resolve()
        files = []
        for f in sorted(root.rglob("*")):
            if f.suffix.lower() in (".html", ".htm") and not (set(f.relative_to(root).parts) & SKIP_DIRS):
                files.append(f)
        # index.html first so "first page" heuristics apply to the homepage
        files.sort(key=lambda f: (f.relative_to(root).as_posix() != "index.html", f.relative_to(root).as_posix()))
        limit = max(max_pages, 1) if max_pages > 1 else 200
        pages = [_build_page(f.relative_to(root).as_posix(), f.read_text(encoding="utf-8", errors="replace"),
                             path=f, root=root, fetch_assets=fetch_assets) for f in files[:limit]]
        site = Site("dir", target, pages, root=root)
        if not pages:
            site.errors.append(f"no .html files found in {target}")
        return site
    raise FileNotFoundError(f"{target} is not a URL, file or folder")


def _load_url(url: str, max_pages: int, fetch_assets: bool) -> Site:
    r = fetch(url)
    if r is None:
        raise ConnectionError(f"could not fetch {url}: {last_error}")
    origin = "{0.scheme}://{0.netloc}".format(urllib.parse.urlsplit(r.url))
    site = Site("url", url, [], origin=origin)
    if r.status >= 400:
        site.errors.append(f"{url} returned HTTP {r.status}")
    first = _build_page(r.url, r.text, url=r.url, status=r.status, headers=r.headers, fetch_assets=fetch_assets)
    site.pages.append(first)
    if max_pages > 1:
        seen = {_norm(r.url)}
        queue = []
        for a in first.tree.find_all("a"):
            href = a.get("href")
            if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
                continue
            absolute = urllib.parse.urljoin(r.url, href).split("#", 1)[0]
            if not _same_origin(absolute, r.url):
                continue
            if re.search(r"\.(?:pdf|jpe?g|png|gif|webp|avif|svg|zip|mp4|webm|mp3|xml|txt)$", absolute, re.I):
                continue
            if _norm(absolute) not in seen:
                seen.add(_norm(absolute))
                queue.append(absolute)
        for link in queue[: max_pages - 1]:
            pr = fetch(link)
            if pr is None or "html" not in pr.headers.get("content-type", "html"):
                continue
            site.pages.append(_build_page(pr.url, pr.text, url=pr.url, status=pr.status, headers=pr.headers,
                                          fetch_assets=fetch_assets))
    return site


def _norm(url: str) -> str:
    return url.rstrip("/").lower()
