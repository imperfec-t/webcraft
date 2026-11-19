---
title: Local service business site
category: Landing Page
tags: [local business, booking, trust, small business]
stack: HTML, CSS, minimal JS (or WordPress block theme)
motion: subtle
description: A fast, trust-first homepage for a local service business with the phone number up front, services, service area, reviews, booking form and opening hours.
---
Build a homepage for [BUSINESS NAME], a [SERVICE, E.G. PLUMBING / DENTAL CLINIC / CLEANING] business serving [SERVICE AREA]. Visitors usually arrive from a local search and want to call or book quickly.

Stack: plain HTML and CSS with minimal JS (or a WordPress block theme if [USES WORDPRESS: YES/NO] is yes). Fast on a mid-range phone is the priority.

SECTIONS
1. Header: logo [BUSINESS NAME], click-to-call phone [PHONE NUMBER] as a visible tel: link, "Book online" button. On mobile, a sticky bottom bar with Call and Book buttons.
2. Hero: headline "[SERVICE] in [SERVICE AREA]" style, with the main benefit [MAIN BENEFIT, E.G. SAME-DAY APPOINTMENTS]; supporting line; Call and Book buttons; one proof element: [RATING AND REVIEW COUNT] with the source.
3. Services: [3 TO 6 SERVICES] as cards with a short description, typical price range [PRICE RANGES IF PUBLIC] and a link.
4. Why choose us: [3 TO 4 CONCRETE REASONS, E.G. LICENSED, INSURED, YEARS IN BUSINESS].
5. Service area: list of [AREAS OR POSTCODES] and an embedded map (lazy-loaded, behind a click-to-load poster to avoid third-party weight).
6. Reviews: 3 real reviews [REVIEWS WITH NAMES] and a link to [REVIEW PLATFORM].
7. Booking form: name, phone, email, service (select), preferred date, message. Labels on every field, clear errors, success message, spam protection.
8. Opening hours and contact: [OPENING HOURS], address [ADDRESS], phone, email; the same phone number as the header.
9. Footer: licence or registration numbers [LICENCE NUMBERS], privacy policy, copyright year printed dynamically.

MOTION
- Minimal: cards fade up once (0.4s). No sliders, no video, no smooth-scroll library.

COLORS AND TYPE
- Background [BACKGROUND COLOR], text [TEXT COLOR], accent [ACCENT COLOR] on Call/Book buttons. One readable sans [FONT FAMILY], body 17 to 18px.

QUALITY BAR
- prefers-reduced-motion: no fades.
- LocalBusiness JSON-LD with name, address, phone, hours and area served; matching title "[SERVICE] in [SERVICE AREA] | [BUSINESS NAME]".
- Phone number identical everywhere and a real tel: link; form tested to deliver to [FORM RECIPIENT EMAIL].
- LCP under 2s on 4G; images WebP with dimensions; total JS under 30 KB.
- Large tap targets (48px), AA contrast, works at 320px.
