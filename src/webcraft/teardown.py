"""Draft a placeholder-based rebuild brief from a page (skills/site-teardown).

The output keeps the structure and the shape of the copy (line counts, word
counts) and never the original wording, brand name, image URLs or class
names. Layout geometry and motion values need a browser, so they are marked
as inferred for the agent or person to complete.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Dict, List, Optional

from . import detect, source
from .dom import Node

SECTION_TAGS = {"header", "nav", "section", "footer", "aside", "article"}
WRAPPER_TAGS = {"main", "div", "body", "#document", "html"}

# keyword in id/class/heading -> canonical section name
NAMES = [
    (r"hero|banner|masthead|intro|jumbotron|above-?fold", "Hero"),
    (r"logos?|clients?|brands|trusted|partners|press", "Proof strip (logos)"),
    (r"stats?|numbers|metrics|counter|kpi", "Stats"),
    (r"about|story|who-?we|mission", "About"),
    (r"services?|offer|what-?we-?do|solutions|capabilit", "Services"),
    (r"features?|benefits", "Features"),
    (r"why|different|advantage|usp", "Differentiators"),
    (r"process|how-?it-?works|steps|approach|method", "Process"),
    (r"work|portfolio|projects|case-?stud|showcase|gallery", "Work / portfolio"),
    (r"pricing|plans|packages|rates", "Pricing"),
    (r"testimonial|reviews?|quotes?|what-?(?:clients|people)", "Testimonials"),
    (r"team|people|staff|founders", "Team"),
    (r"faq|questions|accordion", "FAQ"),
    (r"blog|news|articles|journal|insights|posts", "Blog preview"),
    (r"cta|get-?started|call-?to-?action|ready", "CTA band"),
    (r"contact|enquir|inquir|get-?in-?touch|book|form", "Contact"),
    (r"newsletter|subscribe|signup", "Newsletter"),
    (r"marquee|ticker|scroller", "Marquee"),
]
LAYOUT_HINTS = ["grid", "bento", "masonry", "split", "two-col", "three-col", "col-", "columns", "row", "flex",
                "sticky", "marquee", "slider", "carousel", "swiper", "splide", "accordion", "tabs", "full-bleed",
                "container", "pin", "horizontal"]
MOTION_ATTRS = ["data-aos", "data-scroll", "data-scroll-speed", "data-speed", "data-animate", "data-animation",
                "data-reveal", "data-fade", "data-parallax", "data-lag", "data-splitting", "data-io", "data-clip",
                "data-drift", "data-w-id"]
MOTION_CLASSES = r"\b(?:reveal|fade|parallax|marquee|split|animate|stagger|scroll|magnetic|cursor|pin)[\w-]*"


def _words(text: str) -> int:
    return len(re.findall(r"\w+", text))


def _is_section_like(n: Node) -> bool:
    if n.tag in SECTION_TAGS:
        return True
    ident = (n.get("id") + " " + n.get("class")).lower()
    return bool(re.search(r"\b(?:section|hero|banner|block)\b|section", ident)) and n.find("h1", "h2", "h3") is not None


def collect_sections(root: Node) -> List[Node]:
    body = root.find("body") or root
    out: List[Node] = []

    def walk(n: Node):
        for c in n.elements():
            if c.tag in ("script", "style", "noscript", "template", "link", "meta"):
                continue
            if _is_section_like(c):
                out.append(c)
            elif c.tag in WRAPPER_TAGS or c.find("section", "header", "footer") is not None:
                walk(c)

    walk(body)
    if not out:  # no semantic sections: fall back to body children that hold headings
        out = [c for c in body.elements() if c.find("h1", "h2", "h3") is not None]
    return out


def _name(n: Node, index: int, total: int) -> str:
    if n.tag == "header" or (n.tag == "nav" and index == 0):
        return "Header / navigation"
    if n.tag == "footer":
        return "Footer"
    ident = (n.get("id") + " " + n.get("class") + " " + n.get("aria-label")).lower()
    for pattern, name in NAMES:
        if re.search(pattern, ident):
            return name
    heading = n.find("h1", "h2", "h3")
    if heading is not None and heading.tag == "h1":
        return "Hero"
    htext = (heading.text() if heading is not None else "").lower()
    for pattern, name in NAMES:
        if re.search(pattern.replace("-?", r"\s?"), htext):
            return name
    if n.find("form") is not None:
        return "Contact"
    return "Section"


def _repeated_items(n: Node) -> Optional[dict]:
    """Find the largest group of siblings sharing a class (cards, logos, steps)."""
    best = None
    for parent in n.iter():
        kids = parent.elements()
        if len(kids) < 3:
            continue
        sig = Counter((k.tag, k.classes[0] if k.classes else "") for k in kids)
        (tag, cls), count = sig.most_common(1)[0]
        if count >= 3 and (best is None or count > best[0]):
            sample = next(k for k in kids if (k.tag, k.classes[0] if k.classes else "") == (tag, cls))
            best = (count, sample, parent)
    if best is None:
        return None
    count, sample, parent = best
    slots = []
    if sample.find("img", "picture", "svg") is not None:
        slots.append("image/icon")
    h = sample.find("h2", "h3", "h4", "h5", "strong")
    if h is not None:
        slots.append(f"title ({_words(h.text())} words)")
    p = sample.find("p")
    if p is not None:
        slots.append(f"text (~{_words(p.text())} words)")
    if sample.find("a", "button") is not None:
        slots.append("link")
    if sample.find("blockquote") is not None or sample.tag == "blockquote":
        slots.append("quote")
    kind = "items"
    if slots == ["image/icon"]:
        kind = "logos/images"
    elif sample.tag == "a" and not slots:
        kind = "links"
    elif sample.tag == "li" and sample.find("details", "summary") is not None:
        kind = "accordion items"
    return {"count": count, "kind": kind, "slots": slots or ["text"]}


def describe_section(n: Node, index: int, total: int) -> dict:
    name = _name(n, index, total)
    headings = [h for h in n.iter() if re.fullmatch(r"h[1-6]", h.tag)]
    slots = []
    # Eyebrow: short text immediately before the first heading
    first_h = headings[0] if headings else None
    if first_h is not None and first_h.parent is not None:
        sibs = first_h.parent.elements()
        i = sibs.index(first_h)
        if i > 0 and 0 < _words(sibs[i - 1].text()) <= 5 and sibs[i - 1].tag not in ("img", "picture"):
            slots.append(f"eyebrow label ({_words(sibs[i - 1].text())} words)")
    for h in headings[:3]:
        line_spans = [s for s in h.find_all("span") if "line" in s.classes]
        lines = len(line_spans) if line_spans else len(h.find_all("br")) + 1
        words = sum(_words(s.text()) for s in line_spans) if line_spans else _words(h.text())
        shape = f"[{h.tag.upper()} headline, {words} words"
        shape += f", {lines} lines]" if lines > 1 else "]"
        slots.append(shape)
    if len(headings) > 3:
        slots.append(f"+{len(headings) - 3} more headings (inside repeated items)")
    paras = [p for p in n.find_all("p") if _words(p.text()) > 3]
    if paras:
        total_words = sum(_words(p.text()) for p in paras)
        slots.append(f"{len(paras)} paragraph(s), ~{total_words} words")
    ctas = [a for a in n.find_all("a", "button")
            if re.search(r"btn|button|cta", a.get("class"), re.I) or a.tag == "button"]
    if ctas:
        slots.append(", ".join(f"[CTA, {_words(c.text())} words]" for c in ctas[:3]))
    imgs = n.find_all("img", "picture")
    imgs = [i for i in imgs if not (i.tag == "img" and i.parent is not None and i.parent.tag == "picture")]
    if imgs:
        slots.append(f"{len(imgs)} image(s) [IMAGE 1..{len(imgs)}]" if len(imgs) > 1 else "[IMAGE]")
    if n.find("video") is not None:
        v = n.find("video")
        flags = [a for a in ("autoplay", "muted", "loop", "playsinline") if v.has(a)]
        slots.append(f"[VIDEO] ({' '.join(flags) or 'controls'})")
    forms = n.find_all("form")
    for f in forms:
        fields = [x for x in f.find_all("input", "select", "textarea")
                  if x.get("type").lower() not in ("hidden", "submit", "button")]
        slots.append(f"form with {len(fields)} field(s)")
    if n.find("details") is not None:
        slots.append(f"{len(n.find_all('details'))} accordion item(s) (<details>)")
    if n.find("nav") is not None or n.tag == "nav":
        links = len(n.find_all("a"))
        slots.append(f"navigation, {links} link(s)")
    rep = None if name in ("Header / navigation", "Footer") else _repeated_items(n)

    hints = set()
    for el in n.iter():
        cl = el.get("class").lower()
        for h in LAYOUT_HINTS:
            if re.search(r"(?:^|[\s_-])" + re.escape(h), cl):
                hints.add(h.rstrip("-"))
    motion = Counter()
    for el in n.iter():
        for a in MOTION_ATTRS:
            if el.has(a):
                motion[f'{a}="{el.get(a)}"' if el.get(a) and len(el.get(a)) < 20 else a] += 1
        for m in re.findall(MOTION_CLASSES, el.get("class").lower()):
            motion[f".{m}"] += 1
    return {
        "index": index + 1,
        "name": name,
        "slots": slots,
        "repeated": rep,
        "layout_hints": sorted(hints),
        "motion_hooks": [f"{k} x{v}" if v > 1 else k for k, v in motion.most_common(6)],
    }


def teardown(target: str) -> dict:
    site = source.load(target, max_pages=1)
    page = site.pages[0]
    stack = detect.detect(site)
    sections = collect_sections(page.tree)
    described = [describe_section(s, i, len(sections)) for i, s in enumerate(sections)]
    return {"target": target, "stack": stack, "sections": described}


def render(result: dict) -> str:
    stack = result["stack"]
    techs = stack["technologies"]
    names = [t["name"] for cat in ("cms", "framework", "css", "motion", "slider", "3d") for t in techs.get(cat, [])]
    pal = stack.get("palette") or {}
    fonts = stack.get("fonts") or {}
    roles = fonts.get("roles") or {}
    used = fonts.get("used") or fonts.get("loaded") or []
    display = roles.get("display") or (used[0] if used else None)
    body = roles.get("body") or next((f for f in used if f != display), None)
    kinds = [detect.classify_font(f) for f in (display, body) if f]
    motion_libs = [t["name"] for t in techs.get("motion", [])]
    theme = pal.get("theme", "unknown")

    b = []
    b.append(f"Build [PAGE TYPE] as [STACK: e.g. HTML/CSS/JS{', GSAP + ScrollTrigger' if 'GSAP' in names else ''}]. "
             f"Theme: {theme if theme != 'unknown' else '[light/dark]'}. Fully responsive.")
    b.append("Respect prefers-reduced-motion.")
    b.append("")
    b.append("BRAND")
    b.append("- Name: [BRAND NAME]")
    b.append("- Colors: [BACKGROUND], [SURFACE], [TEXT], [MUTED], [BORDER], [ACCENT]"
             + (" (one saturated accent)" if len(pal.get("accent_candidates") or []) <= 1 else " (two accents observed)"))
    if kinds:
        b.append(f"- Fonts: [DISPLAY FONT] ({kinds[0]})" + (f", [BODY FONT] ({kinds[1]})" if len(kinds) > 1 else ", [BODY FONT]"))
    else:
        b.append("- Fonts: [DISPLAY FONT], [BODY FONT]")
    img_count = sum(1 for s in result["sections"] for slot in s["slots"] if "IMAGE" in slot)
    b.append(f"- Images: [IMAGE LIST] (sections with media: {img_count})")
    b.append("")
    b.append("GLOBAL PATTERNS")
    b.append("- Section label format: [inferred: verify in browser]")
    b.append("- Headline reveal: " + ("[observed motion library: " + ", ".join(motion_libs) + "; values to measure]"
                                     if motion_libs else "[none detected in markup; verify in browser]"))
    b.append("- Button behavior: [hover state to measure]")
    b.append("- Card behavior: [hover state to measure]")
    b.append("")
    b.append("SECTIONS (numbered, in page order)")
    for s in result["sections"]:
        b.append(f"{s['index']}. {s['name'].upper()}")
        hints = ", ".join(s["layout_hints"])
        b.append(f"   Layout: [inferred: verify columns and alignment]" + (f" (markup hints: {hints})" if hints else ""))
        slots = list(s["slots"])
        if s["repeated"]:
            r = s["repeated"]
            slots.append(f"{r['count']} repeated {r['kind']}, each: {', '.join(r['slots'])}")
        b.append("   Content slots: " + ("; ".join(slots) if slots else "[none found in static markup]"))
        if s["motion_hooks"]:
            b.append("   Motion: hooks " + ", ".join(s["motion_hooks"]) +
                     " (trigger, from/to values, duration, easing, stagger: measure in browser)")
        else:
            b.append("   Motion: [none in markup; check in browser]")
    b.append("")
    b.append("QUALITY BAR")
    b.append("- LCP under 2.5s, CLS under 0.1, INP under 200ms on a mid-range phone")
    b.append("- WCAG AA contrast, keyboard operable, one h1, alt text on meaningful images")
    b.append("- Breakpoints: 320, 390, 768, 1024, 1440; no horizontal scroll")
    b.append("- Animate transform and opacity only; content visible without JS and with reduced motion")

    detected = ", ".join(names) or "nothing recognizable"
    head = [
        f"# Teardown draft: {result['target']}",
        "",
        f"Observed: static markup and same-origin CSS/JS ({len(result['sections'])} sections; stack: {detected}). "
        "Inferred: layout geometry, motion values, anything rendered by JavaScript. Complete the [bracketed] parts "
        "by viewing the page in a browser, then remove this line.",
        "",
        "```",
    ]
    return "\n".join(head + b + ["```"])
