"""Static pre-launch audit (the measurable part of skills/launch-qa).

Every finding has a severity from the launch-qa skill:
  blocker     broken functionality, inaccessible core content, placeholder
              content, a site that cannot be indexed
  should-fix  measurable harm to speed, accessibility or search appearance
  polish      minor inconsistencies
and one line each of problem, location and fix. What this tool cannot check
is listed under "Not checked" instead of being reported as passed.
"""
from __future__ import annotations

import datetime as _dt
import json
import re
import urllib.parse
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

from . import css, detect, source
from .dom import Node
from .source import Page, Site

SEVERITIES = ("blocker", "should-fix", "polish")
LABELS = {"blocker": "Blockers", "should-fix": "Should fix", "polish": "Polish"}


@dataclass
class Finding:
    id: str
    severity: str
    area: str
    problem: str
    where: str
    fix: str
    count: int = 1
    examples: List[str] = field(default_factory=list)


@dataclass
class Report:
    target: str
    kind: str
    pages: List[str]
    checked: str
    findings: List[Finding]
    not_checked: List[str]
    passed: List[str]
    errors: List[str]

    @property
    def verdict(self) -> str:
        blockers = sum(1 for f in self.findings if f.severity == "blocker")
        if blockers == 0:
            return "Ready"
        return "Ready after blockers" if blockers <= 3 else "Not ready"

    def counts(self) -> Dict[str, int]:
        c = Counter(f.severity for f in self.findings)
        return {s: c.get(s, 0) for s in SEVERITIES}

    def to_dict(self) -> dict:
        d = asdict(self)
        d["verdict"] = self.verdict
        d["counts"] = self.counts()
        return d


class Ctx:
    """Collects findings and which checks ran clean."""

    def __init__(self, site: Site):
        self.site = site
        self.findings: List[Finding] = []
        self.ran: List[str] = []

    def add(self, id, severity, area, problem, where, fix, examples=None, count=None):
        examples = [e for e in (examples or []) if e][:4]
        self.findings.append(Finding(id, severity, area, problem, where, fix,
                                     count if count is not None else max(len(examples), 1), examples))


PLACEHOLDER_PATTERNS = [
    (r"\blorem ipsum\b|\bdolor sit amet\b", "lorem ipsum text"),
    (r"\bjust another wordpress site\b", "WordPress default tagline"),
    (r"\bhello world!", "WordPress default post"),
    (r"\bsample page\b", "WordPress sample page"),
    (r"\byour (?:company|business|brand) name\b", "template company name"),
    (r"\[(?:placeholder|insert|your)[^\]]{0,40}\]", "bracketed placeholder"),
    (r"\b(?:TODO|FIXME|TBD)\b:?", "TODO marker"),
    (r"\b(?:123[-. ]456[-. ]7890|555[-. ]\d{3}[-. ]\d{4}|\(555\))", "dummy phone number"),
    (r"\b[\w.+-]+@(?:example|test|domain|yourdomain|email)\.(?:com|org|net)\b", "example email address"),
]

GENERIC_LINK_TEXT = {"click here", "here", "read more", "learn more", "more", "click", "this", "link",
                     "this link", "go", "details"}
MOTION_LIBS = {"GSAP", "ScrollTrigger", "Lenis", "Locomotive Scroll", "AOS", "Framer Motion", "Anime.js",
               "Animate.css", "Barba.js", "Swup", "Motion One", "Lottie"}
THIRD_PARTY_OK = ("fonts.googleapis.com", "fonts.gstatic.com")


def _host(url: str) -> str:
    return urllib.parse.urlsplit(url).netloc.lower()


def _where(page: Page) -> str:
    return page.location


def _visible_text(page: Page) -> str:
    body = page.tree.find("body") or page.tree
    return body.text()


def _meta(page: Page, name: str) -> Optional[str]:
    for m in page.tree.find_all("meta"):
        if m.get("name").lower() == name or m.get("property").lower() == name:
            return m.get("content")
    return None


def _has_accessible_name(n: Node) -> bool:
    if n.text() or n.get("aria-label").strip() or n.get("aria-labelledby").strip() or n.get("title").strip():
        return True
    for img in n.find_all("img"):
        if img.get("alt").strip():
            return True
    for svg in n.find_all("svg"):
        if svg.get("aria-label") or svg.find("title"):
            return True
    if n.tag == "input" and n.get("value").strip():
        return True
    return False


# --- page checks ------------------------------------------------------------

def check_head(ctx: Ctx, page: Page):
    t = page.tree
    w = _where(page)
    vp = _meta(page, "viewport")
    if vp is None:
        ctx.add("viewport", "blocker", "Cross-device", "No viewport meta tag, so phones render the desktop layout zoomed out",
                w, 'Add <meta name="viewport" content="width=device-width, initial-scale=1">')
    elif re.search(r"user-scalable\s*=\s*(?:no|0)|maximum-scale\s*=\s*1(?:\.0)?\b", vp):
        ctx.add("zoom-blocked", "should-fix", "Accessibility", "Viewport meta blocks pinch zoom",
                w, "Remove user-scalable=no and maximum-scale=1; the page must work at 200% zoom")
    html = t.find("html")
    if html is None or not html.get("lang").strip():
        ctx.add("lang", "should-fix", "Accessibility", "<html> has no lang attribute; screen readers guess the language",
                w, 'Add lang, e.g. <html lang="en">')
    title = t.find("title")
    title_text = title.text() if title else ""
    if not title_text:
        ctx.add("title", "should-fix", "SEO", "Page has no <title>", w, "Add a unique title of 50 to 60 characters")
    elif not 30 <= len(title_text) <= 60:
        ctx.add("title-length", "polish", "SEO", f"Title is {len(title_text)} characters (aim for 50 to 60)",
                w, "Rewrite so it is descriptive and under 60 characters", [title_text[:70]])
    desc = _meta(page, "description")
    if not desc:
        ctx.add("meta-description", "should-fix", "SEO", "No meta description; search engines will pick arbitrary text",
                w, "Add a meta description of about 150 characters")
    elif not 70 <= len(desc) <= 170:
        ctx.add("meta-description-length", "polish", "SEO", f"Meta description is {len(desc)} characters (aim for about 150)",
                w, "Rewrite to roughly 120 to 160 characters")
    robots = (_meta(page, "robots") or "") + " " + page.headers.get("x-robots-tag", "")
    if "noindex" in robots.lower():
        ctx.add("noindex", "blocker", "SEO", "Page is set to noindex (often left over from staging)",
                w, "Remove noindex from the robots meta tag / X-Robots-Tag header before launch")
    canon = [l for l in t.find_all("link") if "canonical" in l.get("rel").lower().split()]
    if not canon:
        ctx.add("canonical", "should-fix", "SEO", "No canonical URL", w,
                'Add <link rel="canonical" href="https://..."> with the preferred https URL')
    og = {k: _meta(page, k) for k in ("og:title", "og:description", "og:image")}
    missing = [k for k, v in og.items() if not v]
    if missing:
        ctx.add("open-graph", "should-fix", "SEO", f"Missing Open Graph tags: {', '.join(missing)}; shared links look bare",
                w, "Add og:title, og:description and a 1200x630 og:image served over https")
    elif og["og:image"] and not og["og:image"].startswith("https://"):
        ctx.add("og-image-url", "should-fix", "SEO", "og:image is not an absolute https URL; most platforms ignore it",
                w, "Use the full https:// URL of the image", [og["og:image"]])
    icons = [l for l in t.find_all("link") if "icon" in l.get("rel").lower()]
    if not icons:
        ctx.add("favicon", "polish", "Operations", "No favicon link", w,
                'Add <link rel="icon" href="/favicon.svg"> and an apple-touch-icon')
    ld = [s for s in t.find_all("script") if s.get("type").lower() == "application/ld+json"]
    bad_ld = []
    for s in ld:
        try:
            json.loads(s.raw_text())
        except ValueError:
            bad_ld.append(s.raw_text().strip()[:60])
    if bad_ld:
        ctx.add("structured-data-invalid", "should-fix", "SEO", "JSON-LD block is not valid JSON; search engines ignore it",
                w, "Fix the JSON (validate at validator.schema.org)", bad_ld)
    elif not ld and not any(n.has("itemscope") for n in t.iter()):
        ctx.add("structured-data", "polish", "SEO", "No structured data", w,
                "Add Organization or LocalBusiness JSON-LD (and FAQPage/Article where they fit)")


def check_content(ctx: Ctx, page: Page):
    w = _where(page)
    text = _visible_text(page)
    hits = []
    for pattern, label in PLACEHOLDER_PATTERNS:
        m = re.search(pattern, text, re.I if label != "TODO marker" else 0)
        if m:
            hits.append(f"{label}: \"{m.group(0)[:50]}\"")
    if hits:
        ctx.add("placeholder-content", "blocker", "Content", "Placeholder or template content is visible",
                w, "Replace with real content or remove", hits, count=len(hits))
    year = _dt.date.today().year
    m = re.search(r"(?:©|&copy;|\bcopyright\b)\s*(?:\d{4}\s*[-–]\s*)?(\d{4})", text, re.I)
    if m and int(m.group(1)) < year:
        ctx.add("copyright-year", "polish", "Content", f"Copyright year is {m.group(1)}", w,
                f"Update to {year} or print it from the server/CMS", [m.group(0)])


def check_headings(ctx: Ctx, page: Page):
    w = _where(page)
    hs = [n for n in page.tree.iter() if re.fullmatch(r"h[1-6]", n.tag)]
    h1 = [n for n in hs if n.tag == "h1"]
    if not h1:
        ctx.add("h1-missing", "should-fix", "Accessibility", "No <h1> on the page", w,
                "Give the page one h1 that says what it is (usually the hero headline)")
    elif len(h1) > 1:
        ctx.add("h1-multiple", "should-fix", "Accessibility", f"{len(h1)} <h1> elements; use exactly one", w,
                "Keep the main headline as h1 and demote the others to h2", [n.text()[:50] for n in h1])
    prev = 0
    skips = []
    for n in hs:
        level = int(n.tag[1])
        if prev and level > prev + 1:
            skips.append(f"h{prev} -> {n.tag} \"{n.text()[:40]}\"")
        prev = level
    if skips:
        ctx.add("heading-skip", "should-fix", "Accessibility", "Heading levels skip", w,
                "Use the next level down (style with CSS, not with the heading level)", skips, count=len(skips))


def check_images(ctx: Ctx, page: Page):
    w = _where(page)
    imgs = page.tree.find_all("img")
    no_alt, no_dims, legacy = [], [], []
    for i, img in enumerate(imgs):
        src = img.get("src") or img.get("data-src") or img.get("srcset").split(" ")[0]
        label = src.rsplit("/", 1)[-1][:60] or img.snippet()
        if not img.has("alt"):
            no_alt.append(label)
        if not (img.get("width") and img.get("height")) and not src.startswith("data:"):
            no_dims.append(label)
        in_picture = img.parent is not None and img.parent.tag == "picture" and any(
            re.search(r"image/(?:webp|avif)", s.get("type")) for s in img.parent.find_all("source"))
        if re.search(r"\.(?:jpe?g|png|gif)(?:\?|$)", src, re.I) and not in_picture and not re.search(
                r"\.(?:webp|avif)", img.get("srcset"), re.I):
            legacy.append(label)
    if no_alt:
        ctx.add("img-alt", "should-fix", "Accessibility", f"{len(no_alt)} image(s) without an alt attribute", w,
                'Describe meaningful images in alt; use alt="" for decorative ones', no_alt, len(no_alt))
    if no_dims:
        ctx.add("img-dimensions", "should-fix", "Performance",
                f"{len(no_dims)} image(s) without width and height, causing layout shift (CLS)", w,
                "Set width and height attributes to the intrinsic size; CSS can still resize", no_dims, len(no_dims))
    if legacy:
        ctx.add("img-format", "should-fix", "Performance", f"{len(legacy)} image(s) in JPEG/PNG/GIF only", w,
                "Serve WebP or AVIF (with <picture> or srcset), sized to the display size", legacy, len(legacy))
    # The LCP image is usually the first content image, not the logo in the header.
    content_imgs = [i for i in imgs if not any(a.tag in ("header", "nav", "footer") for a in i.ancestors())]
    if content_imgs:
        first = content_imgs[0]
        if first.get("loading").lower() == "lazy":
            ctx.add("lcp-lazy", "should-fix", "Performance",
                    "The first image on the page (likely the LCP image) is lazy-loaded", w,
                    'Remove loading="lazy" from it and preload it; lazy-load only below the fold', [first.snippet()])
        lazy_count = sum(1 for i in imgs if i.get("loading").lower() == "lazy")
        if len(imgs) >= 6 and lazy_count == 0:
            ctx.add("lazy-missing", "should-fix", "Performance", f"None of {len(imgs)} images are lazy-loaded", w,
                    'Add loading="lazy" to images below the first screen')


def check_links(ctx: Ctx, page: Page):
    w = _where(page)
    dead, generic, noname = [], [], []
    for a in page.tree.find_all("a"):
        href = a.get("href").strip()
        if not a.has("href"):
            continue
        if href in ("", "#") or href.lower().startswith("javascript:"):
            dead.append(a.text()[:40] or a.snippet())
        txt = a.text().lower().strip(" .!→»>")
        if txt in GENERIC_LINK_TEXT and not a.get("aria-label"):
            generic.append(a.text()[:40])
        if not _has_accessible_name(a):
            noname.append(a.snippet())
    for b in page.tree.find_all("button"):
        if not _has_accessible_name(b):
            noname.append(b.snippet())
    if dead:
        ctx.add("dead-links", "should-fix", "Content", f'{len(dead)} link(s) go nowhere (href="#", empty or javascript:)',
                w, "Point them at a real page, or use <button> for controls", dead, len(dead))
    if generic:
        ctx.add("link-text", "polish", "SEO", f"{len(generic)} link(s) with generic text such as \"read more\"", w,
                "Use descriptive link text, or add an aria-label naming the destination", generic, len(generic))
    if noname:
        ctx.add("accessible-name", "should-fix", "Accessibility",
                f"{len(noname)} link(s)/button(s) with no accessible name (icon-only)", w,
                "Add aria-label, visually hidden text, or alt text on the icon image", noname, len(noname))


def check_forms(ctx: Ctx, page: Page):
    w = _where(page)
    t = page.tree
    labelled = {l.get("for") for l in t.find_all("label") if l.get("for")}
    unlabeled = []
    for f in t.find_all("input", "select", "textarea"):
        if f.tag == "input" and f.get("type").lower() in ("hidden", "submit", "button", "reset", "image"):
            continue
        if f.get("id") and f.get("id") in labelled:
            continue
        if any(a.tag == "label" for a in f.ancestors()):
            continue
        if f.get("aria-label").strip() or f.get("aria-labelledby").strip() or f.get("title").strip():
            continue
        unlabeled.append(f.get("name") or f.get("placeholder") or f.snippet())
    if unlabeled:
        ctx.add("form-labels", "should-fix", "Accessibility",
                f"{len(unlabeled)} form field(s) without a label (a placeholder is not a label)", w,
                "Associate a <label for> with each field", unlabeled, len(unlabeled))
    forms = t.find_all("form")
    if forms:
        ctx.ran.append("forms present: submit a real test entry and confirm it arrives")


def check_media(ctx: Ctx, page: Page):
    w = _where(page)
    for v in page.tree.find_all("video"):
        if v.has("autoplay"):
            missing = [a for a in ("muted", "playsinline") if not v.has(a)]
            if missing:
                ctx.add("video-autoplay", "should-fix", "Cross-device",
                        f"Autoplay video without {' and '.join(missing)}; mobile browsers will not autoplay it", w,
                        "Use autoplay muted loop playsinline", [v.snippet()])
        if not v.get("poster"):
            ctx.add("video-poster", "should-fix", "Performance", "Video has no poster image", w,
                    "Add a poster (a preloaded image) so the video is never the LCP blocker", [v.snippet()])
    for f in page.tree.find_all("iframe"):
        if not f.get("title").strip():
            ctx.add("iframe-title", "should-fix", "Accessibility", "<iframe> without a title", w,
                    "Add a title describing the embed", [f.get("src")[:80]])
    tabbed = [n.snippet() for n in page.tree.iter() if re.fullmatch(r"[1-9]\d*", n.get("tabindex").strip() or "x")]
    if tabbed:
        ctx.add("tabindex-positive", "polish", "Accessibility", "Positive tabindex values break the natural focus order",
                w, 'Use tabindex="0" or reorder the markup', tabbed, len(tabbed))


def check_performance(ctx: Ctx, page: Page):
    w = _where(page)
    head = page.tree.find("head")
    if head:
        blocking = [s.get("src") for s in head.find_all("script") if s.get("src")
                    and not (s.has("defer") or s.has("async") or s.get("type").lower() == "module")]
        if blocking:
            ctx.add("render-blocking-js", "should-fix", "Performance",
                    f"{len(blocking)} script(s) in <head> block rendering", w,
                    "Add defer (or move to the end of <body>)", [b.rsplit("/", 1)[-1] for b in blocking], len(blocking))
    gf = [l.get("href") for l in page.tree.find_all("link") if "fonts.googleapis.com/css" in l.get("href")]
    no_swap = [h for h in gf if "display=" not in h]
    all_css = page.all_css()
    faces = css.font_faces(all_css)
    faces_no_display = [f.get("font-family", "?").strip("\"' ") for f in faces if "font-display" not in f]
    if no_swap or faces_no_display:
        ctx.add("font-display", "should-fix", "Performance", "Web fonts load without font-display, hiding text while they download",
                w, "Add &display=swap to Google Fonts URLs and font-display: swap to @font-face",
                no_swap[:2] + sorted(set(faces_no_display))[:2])
    fam = detect.font_families(page)
    families = {f.lower() for f in fam["loaded"]}
    if len(families) > 2:
        ctx.add("font-families", "polish", "Performance", f"{len(families)} font families loaded (aim for two at most)", w,
                "Drop to one display and one body family", sorted(fam["loaded"]))
    if page.url:
        own = _host(page.url).removeprefix("www.")
        third = Counter()
        for src in page.script_srcs:
            absolute = urllib.parse.urljoin(page.url, src)
            h = _host(absolute)
            if h and h.removeprefix("www.") != own and not h.endswith("." + own) and h not in THIRD_PARTY_OK:
                third[h] += 1
        if len(third) >= 5:
            ctx.add("third-party", "should-fix", "Performance", f"Scripts from {len(third)} third-party domains", w,
                    "Justify each one; chat widgets and trackers are frequent LCP and INP offenders", list(third)[:4], len(third))


def check_motion(ctx: Ctx, page: Page, techs: List[dict]):
    w = _where(page)
    names = {t["name"] for t in techs}
    motion = sorted(names & MOTION_LIBS)
    all_text = page.all_css() + "\n" + page.all_js()
    has_keyframes = "@keyframes" in all_text
    guarded = re.search(r"prefers-reduced-motion", all_text) or "gsap.matchMedia" in all_text
    if (motion or has_keyframes) and not guarded:
        ctx.add("reduced-motion", "should-fix", "Accessibility",
                "Animation is present but prefers-reduced-motion is never checked", w,
                "Wrap animations in a reduced-motion guard (gsap.matchMedia or @media (prefers-reduced-motion: reduce))",
                motion or ["CSS @keyframes"])
    # Content hidden by CSS waiting for JS to reveal it (scroll-motion house rule).
    hidden = []
    for _, sel, body in css.iter_rules(page.all_css()):
        d = css.parse_decls(body)
        if d.get("opacity", "").strip() in ("0", "0.0") and re.search(
                r"\[data-(?:aos|animate|reveal|fade|io|scroll)|\.(?:reveal|fade|animate|js-)", sel) and not re.search(
                r"\.js\b|\.no-js|:not\(\.no-js\)|\.is-|\.in\b|\.visible|\.active", sel):
            hidden.append(sel.strip()[:60])
    if hidden:
        ctx.add("css-hidden-content", "should-fix", "Cross-device",
                "Content is hidden in CSS until a script reveals it; if JS fails it stays invisible", w,
                "Set the initial state in JS (gsap.from / a .js class on <html>), not in plain CSS", hidden, len(hidden))


def check_css(ctx: Ctx, page: Page):
    w = _where(page)
    all_css = page.all_css()
    if not all_css.strip():
        return
    vw = [sel.strip()[:50] for sel, v in css.declarations(all_css, "width") if re.search(r"\b100vw\b", v)]
    if vw:
        ctx.add("100vw", "polish", "Cross-device", "width: 100vw inside a padded parent causes horizontal scroll", w,
                "Use width: 100% (or a full-bleed grid) instead", vw, len(vw))
    vh = [sel.strip()[:50] for prop in ("height", "min-height") for sel, v in css.declarations(all_css, prop)
          if re.search(r"\b100vh\b", v)]
    if vh:
        ctx.add("100vh", "polish", "Cross-device", "100vh is cut off by mobile browser bars", w,
                "Use 100svh (or 100dvh) with 100vh as a fallback line before it", vh, len(vh))
    hexes = Counter(css.color_values(all_css))
    themes = css.themes(all_css)
    if len(hexes) > 14:
        ctx.add("color-sprawl", "polish", "Design system", f"{len(hexes)} distinct hard-coded colors",
                w, "Map them to role tokens (webcraft tokens / the design-tokens skill)",
                [h for h, _ in hexes.most_common(4)], len(hexes))
    radii = Counter(v.strip() for _, v in css.declarations(all_css, "border-radius")
                    if not v.strip().startswith("var(") and v.strip() not in ("0", "50%", "999px", "9999px", "inherit"))
    if len(radii) > 5:
        ctx.add("radius-sprawl", "polish", "Design system", f"{len(radii)} different border-radius values",
                w, "Pick one corner personality (sharp, soft or pill) and hold it", list(radii)[:5], len(radii))
    for label, results in css.check_tokens_css(all_css).items():
        fails = [r for r in results if r["status"] == "fail"]
        if fails:
            ctx.add("token-contrast", "should-fix", "Accessibility",
                    f"Token pairs below WCAG AA in {label}", w,
                    "Adjust lightness until each pair passes (webcraft contrast --tokens)",
                    [f"{r['pair']} {r['ratio']}:1" for r in fails], len(fails))


def check_mixed_content(ctx: Ctx, page: Page):
    if not page.is_https:
        return
    w = _where(page)
    active, passive = [], []
    for n in page.tree.iter():
        attr = "href" if n.tag == "link" else "src"
        val = n.get(attr)
        if not val.startswith("http://"):
            continue
        if n.tag in ("script", "iframe") or (n.tag == "link" and "stylesheet" in n.get("rel")):
            active.append(val[:80])
        elif n.tag in ("img", "video", "audio", "source"):
            passive.append(val[:80])
    if active:
        ctx.add("mixed-content-active", "blocker", "Security", "Scripts/styles/iframes loaded over http on an https page; browsers block them",
                w, "Load them over https", active, len(active))
    if passive:
        ctx.add("mixed-content", "should-fix", "Security", "Media loaded over http on an https page", w,
                "Load them over https", passive, len(passive))


PAGE_CHECKS: List[Callable] = [check_head, check_content, check_headings, check_images, check_links,
                               check_forms, check_media, check_performance, check_css, check_mixed_content]


# --- site checks ------------------------------------------------------------

def check_site_consistency(ctx: Ctx):
    pages = ctx.site.pages
    if len(pages) > 1:
        titles = defaultdict(list)
        for p in pages:
            t = p.tree.find("title")
            if t and t.text():
                titles[t.text()].append(p.location)
        dupes = [f"\"{t[:40]}\" on {len(locs)} pages" for t, locs in titles.items() if len(locs) > 1]
        if dupes:
            ctx.add("title-duplicate", "should-fix", "SEO", "Several pages share the same <title>", "multiple pages",
                    "Give every page a unique title", dupes, len(dupes))
    phones = defaultdict(set)
    for p in pages:
        for a in p.tree.find_all("a"):
            href = a.get("href")
            if href.lower().startswith("tel:"):
                digits = re.sub(r"\D", "", href)
                if digits:
                    phones[digits[-9:]].add(href[4:].strip())
    if len(phones) > 1:
        ctx.add("tel-mismatch", "polish", "Content", f"{len(phones)} different phone numbers in tel: links",
                "header/footer/contact", "Confirm each is intended; mismatched numbers between header and footer are common",
                [sorted(v)[0] for v in phones.values()], len(phones))


def check_local_links(ctx: Ctx):
    if ctx.site.kind not in ("dir", "file"):
        return
    broken = []
    for p in ctx.site.pages:
        for n in p.tree.iter():
            ref = n.get("href") if n.tag in ("a", "link") else n.get("src") if n.tag in ("img", "script", "source", "video") else ""
            if not ref:
                continue
            # A single file cannot tell us where the site root is.
            if ctx.site.kind == "file" and ref.startswith("/"):
                continue
            local = source.resolve_local(ref, p.path, ctx.site.root)
            if local is None:
                continue
            candidates = [local, Path(str(local).rstrip("/\\") + ".html"), local / "index.html"]
            if not any(c.exists() for c in candidates):
                broken.append(f"{p.location}: {ref}")
    if broken:
        ctx.add("broken-local-links", "blocker", "Functionality", f"{len(broken)} link(s)/asset(s) point to files that do not exist",
                "local files", "Fix the paths or add the missing files", broken, len(broken))
    if ctx.site.kind == "dir" and ctx.site.root and not any(
            (ctx.site.root / n).exists() for n in ("404.html", "404/index.html")):
        ctx.add("404-page", "polish", "Functionality", "No 404.html in the site folder", str(ctx.site.root),
                "Add a 404 page that links home (or confirm the host/CMS provides one)")


def check_remote(ctx: Ctx):
    site = ctx.site
    if site.kind != "url" or not site.origin:
        return
    origin = site.origin
    if origin.startswith("http://"):
        ctx.add("https", "blocker", "Security", "Site is served over http", origin,
                "Enable HTTPS and redirect http to https")
    else:
        r = source.fetch("http://" + origin[len("https://"):] + "/", timeout=10)
        if r is not None and not r.url.startswith("https://"):
            ctx.add("https-redirect", "should-fix", "Security", "http:// does not redirect to https://", origin,
                    "Add a permanent 301 redirect from http to https")
    host = _host(origin)
    alt = host[4:] if host.startswith("www.") else "www." + host
    r = source.fetch(f"https://{alt}/", timeout=10)
    if r is not None and r.status < 400 and _host(r.url) != host:
        pass  # redirected to some other canonical host; fine
    elif r is not None and r.status < 400 and _host(r.url) == alt:
        ctx.add("www-canonical", "polish", "SEO", f"Both {host} and {alt} serve the site without redirecting", origin,
                "Pick one and 301-redirect the other")
    robots = source.fetch(origin + "/robots.txt", timeout=10)
    sitemap_urls = []
    if robots is None or robots.status >= 400:
        ctx.add("robots-txt", "polish", "SEO", "No robots.txt", origin + "/robots.txt",
                "Add one that allows crawling and lists the sitemap")
    else:
        sitemap_urls = re.findall(r"(?im)^\s*sitemap:\s*(\S+)", robots.text)
        groups = re.split(r"(?im)^\s*user-agent:", robots.text)
        for g in groups[1:]:
            agent = g.splitlines()[0].strip() if g.splitlines() else ""
            if agent == "*" and re.search(r"(?im)^\s*disallow:\s*/\s*$", g):
                ctx.add("robots-blocks-all", "blocker", "SEO", "robots.txt disallows the whole site", origin + "/robots.txt",
                        "Remove 'Disallow: /' (often left from staging)")
    found = False
    for u in sitemap_urls[:2] + [origin + p for p in ("/sitemap.xml", "/sitemap_index.xml", "/wp-sitemap.xml")]:
        r = source.fetch(u, timeout=10, max_bytes=200_000)
        if r is not None and r.status < 400 and re.search(r"<(?:urlset|sitemapindex)", r.text):
            found = True
            break
    if not found:
        ctx.add("sitemap", "should-fix", "SEO", "No XML sitemap found", origin,
                "Publish /sitemap.xml and reference it in robots.txt")
    r = source.fetch(origin + "/webcraft-404-check-9f3a1c", timeout=10, max_bytes=200_000)
    if r is not None and r.status == 200:
        ctx.add("soft-404", "should-fix", "SEO", "Missing pages return HTTP 200 instead of 404", origin,
                "Serve a real 404 status with a page that links home")
    elif r is not None and r.status == 404 and len(r.text.strip()) < 200:
        ctx.add("404-page", "polish", "Functionality", "The 404 page is bare", origin,
                "Add a 404 page with navigation and a link home")
    # Internal links on the first page that are broken
    first = site.pages[0]
    links = []
    for a in first.tree.find_all("a"):
        href = a.get("href")
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = urllib.parse.urljoin(first.url or origin, href).split("#", 1)[0]
        if _host(absolute).removeprefix("www.") == host.removeprefix("www.") and absolute not in links:
            links.append(absolute)
    broken = []
    for link in links[:40]:
        r = source.fetch(link, method="HEAD", timeout=10)
        if r is not None and r.status in (405, 403, 501):
            r = source.fetch(link, timeout=10, max_bytes=50_000)
        # 401/403/429 usually mean "log in" or "slow down", not a broken page.
        if r is not None and (r.status in (404, 410) or r.status >= 500):
            broken.append(f"{link} ({r.status})")
    if broken:
        ctx.add("broken-links", "blocker", "Functionality", f"{len(broken)} internal link(s) return an error",
                first.location, "Fix or redirect them", broken, len(broken))


NOT_CHECKED_ALWAYS = [
    "Real device testing (iOS Safari vh units, sticky, video autoplay): open the site on an iPhone and an Android phone",
    "Core Web Vitals (LCP, INP, CLS) on a throttled connection: run PageSpeed Insights or Lighthouse",
    "Keyboard operation (focus ring, menu, accordions, no focus trap): tab through every page",
    "Contrast of text over images and gradients: check visually or with a browser contrast picker",
    "Layout at 320, 390, 768, 1024, 1440 widths and 200% zoom: resize a browser",
    "Legal pages and cookie consent suit the jurisdiction: review with the owner",
    "CMS, theme and plugin updates, backups and a tested restore: check the hosting/CMS dashboard",
    "Analytics and Search Console connected: check each account",
]


PASS_LABELS = {
    "viewport": "viewport meta", "lang": "html lang", "title": "page title", "meta-description": "meta description",
    "h1-missing": "h1 present", "img-alt": "image alt text", "img-dimensions": "image dimensions",
    "placeholder-content": "no placeholder content", "dead-links": "no dead links", "form-labels": "form labels",
    "canonical": "canonical URL", "open-graph": "Open Graph tags", "reduced-motion": "reduced-motion guard",
    "mixed-content-active": "no blocked mixed content", "render-blocking-js": "no render-blocking scripts",
    "font-display": "font-display set",
}


def audit(target: str, max_pages: int = 1, remote_checks: bool = True) -> Report:
    site = source.load(target, max_pages=max_pages)
    ctx = Ctx(site)
    techs_all: Dict[str, dict] = {}
    for page in site.pages:
        techs = detect.detect_page(page)
        for t in techs:
            techs_all.setdefault(t["name"], t)
        for check in PAGE_CHECKS:
            check(ctx, page)
        check_motion(ctx, page, techs)
    check_site_consistency(ctx)
    check_local_links(ctx)
    if remote_checks:
        check_remote(ctx)

    not_checked = list(NOT_CHECKED_ALWAYS)
    if any(p.tree.find("form") for p in site.pages):
        not_checked.insert(0, "Form delivery: submit a real test entry and confirm it arrives in the right inbox, with spam protection")
    if site.kind != "url":
        not_checked.append("Server: HTTPS, redirects, compression, caching, robots.txt and sitemap (re-run against the live URL)")
    if any(p.html.count("<script") > 0 and len(_visible_text(p)) < 200 for p in site.pages):
        not_checked.append("Content rendered by JavaScript: this page has little static text, so checks saw only the shell")

    findings = _merge(ctx.findings, len(site.pages))
    order = {s: i for i, s in enumerate(SEVERITIES)}
    findings.sort(key=lambda f: (order[f.severity], -f.count))
    checked_ids = {f.id for f in findings}
    passed = [label for cid, label in PASS_LABELS.items() if cid not in checked_ids]
    return Report(target=target, kind=site.kind, pages=[p.location for p in site.pages],
                  checked=_dt.date.today().isoformat(), findings=findings, not_checked=not_checked,
                  passed=passed, errors=site.errors)


def _merge(findings: List[Finding], page_count: int) -> List[Finding]:
    """Collapse the same finding across many pages into one line."""
    if page_count <= 1:
        return findings
    groups: Dict[tuple, List[Finding]] = defaultdict(list)
    for f in findings:
        groups[(f.id, f.severity, f.problem if f.id in ("token-contrast",) else "")].append(f)
    out = []
    for (fid, sev, _), fs in groups.items():
        if len(fs) == 1:
            out.append(fs[0])
            continue
        base = fs[0]
        examples = []
        for f in fs:
            examples.extend(f.examples[:1] or [f.where])
        where = f"{len(fs)} pages: " + ", ".join(f.where for f in fs[:3]) + (" ..." if len(fs) > 3 else "")
        out.append(Finding(fid, sev, base.area, base.problem, where, base.fix, sum(f.count for f in fs), examples[:4]))
    return out


def render(report: Report) -> str:
    scope = (f"static analysis of {len(report.pages)} page(s)"
             + (", linked CSS/JS, robots.txt, sitemap, redirects" if report.kind == "url" else ", linked local CSS/JS"))
    lines = [f"# Launch QA: {report.target}   Checked: {report.checked}   Scope: {scope}", "",
             f"Verdict: {report.verdict}"]
    c = report.counts()
    lines.append(f"({c['blocker']} blocker(s), {c['should-fix']} should fix, {c['polish']} polish)")
    for e in report.errors:
        lines.append(f"Warning: {e}")
    for sev in SEVERITIES:
        items = [f for f in report.findings if sev == f.severity]
        lines.append("")
        lines.append(f"## {LABELS[sev]}")
        if not items:
            lines.append("None found.")
            continue
        for i, f in enumerate(items, 1):
            lines.append(f"{i}. {f.problem} — {f.where} — {f.fix}")
            if f.examples:
                lines.append("   e.g. " + "; ".join(f.examples[:3]))
    if report.passed:
        lines.append("")
        lines.append("## Passed")
        lines.append(", ".join(report.passed))
    lines.append("")
    lines.append("## Not checked")
    for n in report.not_checked:
        check, _, how = n.partition(": ")
        lines.append(f"- {check} — {how}" if how else f"- {n}")
    return "\n".join(lines)
