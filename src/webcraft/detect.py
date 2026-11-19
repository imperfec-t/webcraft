"""Detect a site's stack from library fingerprints (site-teardown step 5)."""
from __future__ import annotations

import re
import urllib.parse
from collections import Counter
from typing import Dict, List

from . import color, css
from .source import Page, Site

# name, category, regexes matched against markup, asset URLs and asset text
FINGERPRINTS = [
    ("GSAP", "motion", [r"gsap(?:\.min)?\.js", r"\bgsap\.(?:to|from|timeline|registerPlugin)\b", r"cdn\.jsdelivr\.net/npm/gsap"]),
    ("ScrollTrigger", "motion", [r"ScrollTrigger"]),
    ("SplitText", "motion", [r"\bSplitText\b"]),
    ("Lenis", "motion", [r"\blenis\b", r"\bnew Lenis\("]),
    ("Locomotive Scroll", "motion", [r"locomotive-scroll", r"data-scroll-container"]),
    ("AOS", "motion", [r"\baos(?:\.min)?\.(?:js|css)", r"data-aos="]),
    ("Framer Motion", "motion", [r"framer-motion", r"\bmotion\.div\b"]),
    ("Motion One", "motion", [r"@motionone|motion\.dev"]),
    ("Anime.js", "motion", [r"anime(?:\.min)?\.js", r"\banime\(\{"]),
    ("Lottie", "motion", [r"lottie(?:-web|-player|\.min)?", r"<lottie-player|<dotlottie"]),
    ("Barba.js", "motion", [r"\bbarba\b", r"data-barba="]),
    ("Swup", "motion", [r"\bswup\b"]),
    ("Animate.css", "motion", [r"animate(?:\.min)?\.css", r"animate__animated"]),
    ("Three.js", "3d", [r"three(?:\.module)?(?:\.min)?\.js", r"\bTHREE\.(?:Scene|WebGLRenderer)"]),
    ("Spline", "3d", [r"spline(?:tool)?\.(?:design|com)|@splinetool"]),
    ("Swiper", "slider", [r"swiper(?:-bundle)?(?:\.min)?\.(?:js|css)", r"class=\"[^\"]*\bswiper\b"]),
    ("Splide", "slider", [r"splide(?:\.min)?\.(?:js|css)", r"class=\"[^\"]*\bsplide\b"]),
    ("Slick", "slider", [r"slick(?:\.min)?\.(?:js|css)"]),
    ("Flickity", "slider", [r"flickity"]),
    ("Glide.js", "slider", [r"@glidejs|glide(?:\.min)?\.js"]),
    ("jQuery", "library", [r"jquery(?:[.-]\d[\w.]*)?(?:\.min)?\.js", r"\bjQuery\("]),
    ("Alpine.js", "library", [r"alpinejs|\bx-data="]),
    ("htmx", "library", [r"htmx(?:\.min)?\.js|\bhx-(?:get|post)="]),
    ("React", "framework", [r"react(?:-dom)?(?:\.production)?(?:\.min)?\.js", r"data-reactroot", r"__REACT_DEVTOOLS"]),
    ("Next.js", "framework", [r"/_next/static", r"__NEXT_DATA__"]),
    ("Nuxt", "framework", [r"/_nuxt/", r"__NUXT__"]),
    ("Vue", "framework", [r"vue(?:\.global|\.runtime)?(?:\.prod)?(?:\.min)?\.js", r"\bdata-v-[0-9a-f]{6,}"]),
    ("Svelte / SvelteKit", "framework", [r"svelte-[a-z0-9]{5,}", r"/_app/immutable/"]),
    ("Astro", "framework", [r"<astro-island", r"/_astro/"]),
    ("Gatsby", "framework", [r"___gatsby", r"/page-data/"]),
    ("Remix", "framework", [r"__remixContext"]),
    ("Tailwind CSS", "css", [r"tailwindcss|--tw-[a-z-]+:", r"class=\"[^\"]*\b(?:flex|grid) [^\"]*\b(?:px|py|mt|gap)-\d"]),
    ("Bootstrap", "css", [r"bootstrap(?:\.bundle)?(?:\.min)?\.(?:css|js)", r"class=\"[^\"]*\bcol-(?:sm|md|lg)-\d"]),
    ("Bulma", "css", [r"bulma(?:\.min)?\.css"]),
    ("WordPress", "cms", [r"/wp-content/", r"/wp-includes/", r"<meta[^>]+generator[^>]+WordPress"]),
    ("Elementor", "cms", [r"elementor"]),
    ("Divi", "cms", [r"et_pb_|/Divi/"]),
    ("Bricks", "cms", [r"/themes/bricks/|\bbrxe-"]),
    ("Oxygen", "cms", [r"/plugins/oxygen/|\bct-section\b"]),
    ("WooCommerce", "cms", [r"woocommerce"]),
    ("Webflow", "cms", [r"data-wf-page|data-wf-site|webflow\.js|assets\.website-files\.com"]),
    ("Framer", "cms", [r"framerusercontent\.com|data-framer-"]),
    ("Squarespace", "cms", [r"squarespace|static1\.squarespace\.com"]),
    ("Wix", "cms", [r"wixstatic\.com|_wixCssImports|wix-code"]),
    ("Shopify", "cms", [r"cdn\.shopify\.com|Shopify\.theme"]),
    ("Ghost", "cms", [r"<meta[^>]+generator[^>]+Ghost"]),
    ("Hugo", "cms", [r"<meta[^>]+generator[^>]+Hugo"]),
    ("Google Analytics / gtag", "analytics", [r"googletagmanager\.com/gtag|google-analytics\.com|\bgtag\("]),
    ("Google Tag Manager", "analytics", [r"googletagmanager\.com/gtm\.js|GTM-[A-Z0-9]{4,}"]),
    ("Meta Pixel", "analytics", [r"connect\.facebook\.net|fbq\("]),
    ("Plausible", "analytics", [r"plausible\.io/js"]),
    ("Fathom", "analytics", [r"usefathom\.com"]),
    ("Hotjar", "analytics", [r"hotjar\.com|\bhjid\b"]),
    ("Microsoft Clarity", "analytics", [r"clarity\.ms"]),
    ("Intercom", "widget", [r"widget\.intercom\.io|intercomSettings"]),
    ("Crisp", "widget", [r"client\.crisp\.chat"]),
    ("Tawk.to", "widget", [r"embed\.tawk\.to"]),
    ("HubSpot", "widget", [r"js\.hs-scripts\.com|hsforms"]),
    ("Calendly", "widget", [r"assets\.calendly\.com|calendly\.com/"]),
    ("reCAPTCHA", "widget", [r"recaptcha"]),
    ("Cloudflare Turnstile", "widget", [r"challenges\.cloudflare\.com/turnstile"]),
    ("Google Fonts", "fonts", [r"fonts\.googleapis\.com|fonts\.gstatic\.com"]),
    ("Adobe Fonts", "fonts", [r"use\.typekit\.net|p\.typekit\.net"]),
]

VERSION_RE = r"{name}[@/-]v?(\d+\.\d+(?:\.\d+)?)"
VERSION_KEYS = {"GSAP": "gsap", "Lenis": "lenis", "Swiper": "swiper", "jQuery": "jquery",
                "Three.js": "three", "Bootstrap": "bootstrap", "AOS": "aos", "Splide": "splide"}

SERIF_HINTS = ("serif", "garamond", "playfair", "fraunces", "lora", "merriweather", "georgia", "times",
               "libre baskerville", "dm serif", "cormorant", "instrument serif", "newsreader", "spectral",
               "eb garamond", "pp editorial", "tiempos", "canela", "gt sectra", "recoleta", "noto serif")
MONO_HINTS = ("mono", "code", "courier", "consolas", "menlo")
GENERIC = {"serif", "sans-serif", "monospace", "system-ui", "ui-sans-serif", "ui-serif", "ui-monospace",
           "-apple-system", "blinkmacsystemfont", "segoe ui", "roboto", "helvetica", "helvetica neue",
           "arial", "inherit", "initial", "cursive", "fantasy", "emoji", "apple color emoji",
           "segoe ui emoji", "noto color emoji", "segoe ui symbol"}


def haystack(page: Page) -> str:
    parts = [page.html]
    parts.extend(page.script_srcs)
    parts.extend(page.stylesheet_hrefs)
    parts.extend(t[:400_000] for _, t in page.js)
    parts.extend(t[:400_000] for _, t in page.css)
    return "\n".join(parts)


def detect_page(page: Page) -> List[dict]:
    hay = haystack(page)
    found = []
    for name, category, patterns in FINGERPRINTS:
        evidence = None
        for p in patterns:
            m = re.search(p, hay, re.I if name not in ("ScrollTrigger", "SplitText") else 0)
            if m:
                evidence = m.group(0)[:80]
                break
        if not evidence:
            continue
        item = {"name": name, "category": category, "evidence": evidence}
        key = VERSION_KEYS.get(name)
        if key:
            vm = re.search(VERSION_RE.format(name=re.escape(key)), hay, re.I)
            if vm:
                item["version"] = vm.group(1)
        found.append(item)
    return found


def font_families(page: Page) -> Dict[str, List[str]]:
    """Families loaded (Google Fonts, @font-face) and used (font-family declarations)."""
    loaded: List[str] = []
    for href in page.stylesheet_hrefs + [n.get("href") for n in page.tree.find_all("link")]:
        if "fonts.googleapis.com" in href:
            q = urllib.parse.parse_qs(urllib.parse.urlsplit(href).query)
            for fam in q.get("family", []):
                for f in fam.split("|"):
                    loaded.append(f.split(":")[0].replace("+", " ").strip())
    all_css = page.all_css()
    for ff in css.font_faces(all_css):
        fam = ff.get("font-family", "").strip().strip("\"'")
        if fam:
            loaded.append(fam)
    for m in re.finditer(r"@import\s+url\(['\"]?([^'\")]+fonts\.googleapis\.com[^'\")]+)", all_css):
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(m.group(1)).query)
        for fam in q.get("family", []):
            loaded.append(fam.split(":")[0].replace("+", " ").strip())
    used = Counter()
    roles: Dict[str, str] = {}
    root_props = css.themes(all_css).get(":root", {})
    for sel, val in css.declarations(all_css, "font-family") + css.declarations(all_css, "font"):
        val = css.resolve(val, root_props)
        m = re.search(r"(\"[^\"]+\"|'[^']+'|[A-Za-z][\w -]*)\s*(?:,|$)", val)
        first = (m.group(1) if m else val.split(",")[0]).strip().strip("\"'")
        if not first or first.lower() in GENERIC or first.startswith("var(") or re.match(r"^\d", first):
            continue
        used[first] += 1
        s = sel.lower()
        if re.search(r"\bh[12]\b|heading|display|title", s):
            roles.setdefault("display", first)
        elif re.search(r"^\s*(?:body|html|:root)\b", s):
            roles.setdefault("body", first)
    for name, val in root_props.items():
        if name.startswith("--font") or name.startswith("--wp--preset--font-family"):
            first = val.split(",")[0].strip().strip("\"'")
            if re.search(r"display|heading", name):
                roles.setdefault("display", first)
            elif re.search(r"body|base|text|sans", name):
                roles.setdefault("body", first)
    return {"loaded": sorted(set(loaded), key=str.lower), "used": [f for f, _ in used.most_common(6)],
            "roles": roles}


def classify_font(name: str) -> str:
    n = name.lower()
    if any(h in n for h in MONO_HINTS):
        return "monospace"
    if any(h in n for h in SERIF_HINTS) and "sans" not in n:
        return "serif"
    return "sans-serif"


def palette(page: Page) -> dict:
    """Theme guess and the most used colors."""
    all_css = page.all_css()
    themes = css.themes(all_css)
    root = themes.get(":root", {})
    counts = Counter()
    for v in css.color_values(all_css):
        c = color.try_parse(v)
        if c and c[3] > 0.5:
            counts[color.to_hex(c[:3] + (1.0,))] += 1
    for v in root.values():
        c = color.try_parse(v)
        if c and c[3] > 0.5:
            counts[color.to_hex(c[:3] + (1.0,))] += 1
    bg = None
    for name in ("--bg", "--background", "--color-bg", "--color-background", "--wp--preset--color--base"):
        if name in root and color.try_parse(root[name]):
            bg = color.parse(root[name])
            break
    if bg is None:
        for sel, val in css.declarations(all_css, "background-color") + css.declarations(all_css, "background"):
            if re.fullmatch(r"\s*(?:body|html|:root)(?:\s*,\s*(?:body|html))?\s*", sel):
                val = css.resolve(val, root)
                m = css.COLOR_TOKEN_RE.search(val)
                named = val.strip().split()[0].lower() if val.strip() else ""
                if m and color.try_parse(m.group(0)):
                    bg = color.parse(m.group(0))
                    break
                if named in color.NAMED and named != "transparent":
                    bg = color.parse(named)
                    break
    theme = "unknown" if bg is None else ("dark" if color.luminance(bg) < 0.2 else "light")
    accents = []
    for hexv, _ in counts.most_common(30):
        L, C, H = color.rgb_to_oklch(color.parse(hexv))
        if C >= 0.08 and 0.25 < L < 0.92:
            accents.append({"hex": hexv, "hue": color.describe_hue(H, C)})
    return {
        "theme": theme,
        "custom_properties": len(root),
        "distinct_colors": len(counts),
        "top_colors": [h for h, _ in counts.most_common(8)],
        "accent_candidates": accents[:3],
        "has_dark_variant": len(themes) > 1,
    }


def detect(site: Site) -> dict:
    tech: Dict[str, dict] = {}
    for page in site.pages:
        for item in detect_page(page):
            tech.setdefault(item["name"], item)
    first = site.pages[0] if site.pages else None
    generator = ""
    if first:
        for m in first.tree.find_all("meta"):
            if m.get("name").lower() == "generator":
                generator = m.get("content")
    by_cat: Dict[str, List[dict]] = {}
    for item in tech.values():
        by_cat.setdefault(item["category"], []).append(item)
    return {
        "target": site.target,
        "pages": [p.location for p in site.pages],
        "generator": generator,
        "technologies": by_cat,
        "fonts": font_families(first) if first else {},
        "palette": palette(first) if first else {},
        "observed": "markup, linked same-origin CSS and JS" if site.kind == "url" else "local files",
        "not_observed": "code loaded at runtime by other scripts, cross-origin bundles' contents, behavior",
    }


def render(result: dict) -> str:
    lines = [f"# Stack: {result['target']}", ""]
    if result.get("generator"):
        lines.append(f"Generator meta: {result['generator']}")
    order = ["cms", "framework", "css", "motion", "3d", "slider", "library", "fonts", "analytics", "widget"]
    labels = {"cms": "CMS / builder", "framework": "Framework", "css": "CSS", "motion": "Motion",
              "3d": "3D", "slider": "Sliders", "library": "Libraries", "fonts": "Font services",
              "analytics": "Analytics", "widget": "Widgets"}
    techs = result["technologies"]
    if not techs:
        lines.append("No known libraries detected (plain HTML/CSS, or everything is bundled and minified).")
    for cat in order:
        if cat in techs:
            items = ", ".join(t["name"] + (f" {t['version']}" if t.get("version") else "") for t in techs[cat])
            lines.append(f"{labels[cat]:<15} {items}")
    f = result.get("fonts") or {}
    if f.get("loaded") or f.get("used"):
        lines.append("")
        lines.append("Fonts loaded:   " + (", ".join(f.get("loaded") or []) or "none found"))
        lines.append("Fonts used:     " + (", ".join(f"{n} ({classify_font(n)})" for n in f.get("used") or []) or "none found"))
    p = result.get("palette") or {}
    if p:
        lines.append("")
        lines.append(f"Theme:          {p['theme']}" + ("  (has a dark/alt variant)" if p.get("has_dark_variant") else ""))
        lines.append(f"Colors:         {p['distinct_colors']} distinct literal colors, {p['custom_properties']} custom properties on :root")
        if p.get("accent_candidates"):
            lines.append("Accent guess:   " + ", ".join(f"{a['hex']} ({a['hue']})" for a in p["accent_candidates"]))
    lines.append("")
    lines.append(f"Observed: {result['observed']}. Not observed: {result['not_observed']}.")
    return "\n".join(lines)
