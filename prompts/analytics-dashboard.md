---
title: Analytics dashboard shell
category: Dashboard
tags: [dashboard, app shell, charts, dark mode, kpi]
stack: React, Tailwind CSS, a chart library (Recharts or Chart.js)
motion: subtle
description: A responsive app dashboard: collapsible sidebar, top bar with search and date range, KPI tiles with sparklines, a main chart, a sortable table and light/dark themes.
---
Build an analytics dashboard for [PRODUCT NAME], used by [USER ROLE] to monitor [WHAT THEY TRACK].

Stack: React, Tailwind CSS, [RECHARTS OR CHART.JS]. Design tokens as CSS variables with light and dark themes; dark is designed, not inverted.

LAYOUT
- App shell: left sidebar 248px (collapses to 64px icons; becomes a drawer below 1024px), top bar, scrollable main area.
- Sidebar: logo, navigation [NAV ITEMS], a workspace switcher at the bottom, the active item highlighted with an accent bar.
- Top bar: page title, global search (Cmd/Ctrl+K opens a command palette), date-range picker [DEFAULT RANGE], theme toggle, avatar menu.
- Main grid:
  1. KPI row: [4 KPIS WITH UNITS], each with value, change vs previous period (green up / red down, plus an arrow and text, never color alone) and a sparkline.
  2. Main chart: [MAIN METRIC] over time, with a series toggle and hover tooltip.
  3. Two side-by-side panels: [BREAKDOWN 1, E.G. BY CHANNEL] as a bar chart and [BREAKDOWN 2] as a ranked list.
  4. Data table: [TABLE COLUMNS], sortable headers, pagination, row hover, status pills, sticky header.
- Empty, loading (skeletons) and error states for every panel.

DATA
- Use realistic mock data generated in a single module [MOCK DATA SHAPE]; keep components data-agnostic so real APIs plug in.

MOTION
- Skeletons shimmer while loading; panels fade in (0.2s) when data arrives.
- Chart lines draw in once (0.6s). Number changes tween (0.3s).
- Sidebar collapse animates width with a 0.2s ease; nothing else moves.

COLORS AND TYPE
- Neutral surfaces with [ACCENT COLOR] for the primary series and focus; a categorical palette of up to 6 distinguishable colors for charts, checked in both themes.
- [FONT FAMILY] with tabular numerals for all figures.

QUALITY BAR
- prefers-reduced-motion: no shimmer animation (static skeleton), no draw-in.
- Keyboard: full navigation, visible focus, Escape closes menus and the palette, the table is navigable.
- Charts have text alternatives (summary sentence plus the data table toggle).
- Contrast AA in both themes for text, chart labels and gridlines that carry meaning.
- Layout holds at 1280, 1024 and 390 widths; no horizontal page scroll (tables scroll inside their panel).
