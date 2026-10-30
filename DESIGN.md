---
name: "Arizona Election Explorer — Signal"
description: "A bold, clean, modern geographic data tool for source-linked Arizona election exploration."
colors:
  canvas: "#0b0f18"
  canvas-light: "#f3f5f9"
  surface: "#131b29"
  surface-light: "#ffffff"
  surface-raised: "#1d293c"
  surface-raised-light: "#eaf0f7"
  ink: "#f1f5ff"
  ink-light: "#101827"
  muted: "#a9b7cf"
  muted-light: "#526079"
  line: "#34435a"
  line-light: "#c9d2e0"
  control-line: "#7789a6"
  control-line-light: "#7d8ba2"
  chrome: "#0c1019"
  chrome-ink: "#f5f7fd"
  chrome-muted: "#b4c0d3"
  accent: "#d7ff3f"
  accent-ink: "#182100"
  selection: "#26331c"
  selection-light: "#f0f8d5"
  selection-edge: "#d7ff3f"
  selection-edge-light: "#597100"
  blue: "#4388ff"
  blue-light: "#1764f5"
  blue-text: "#85b3ff"
  blue-text-light: "#0747c4"
  blue-wash: "#142c52"
  blue-wash-light: "#eaf0ff"
  red: "#ff4869"
  red-light: "#ee304c"
  red-text: "#ff8da4"
  red-text-light: "#bb1734"
  red-wash: "#431e31"
  red-wash-light: "#ffedf0"
  neutral: "#8999b4"
  neutral-light: "#68758b"
  neutral-text: "#bcc8dd"
  neutral-text-light: "#47556e"
  map-dem: "#286bed"
  map-dem-light: "#1764f5"
  map-rep: "#e73158"
  map-rep-light: "#ee304c"
  map-other: "#66768f"
  map-other-light: "#68758b"
  map-base: "#111b2b"
  map-base-light: "#e9edf5"
  map-line: "#0b0f18"
  map-line-light: "#ffffff"
  map-quiet: "#243248"
  map-quiet-light: "#d3dce8"
  map-hatch: "#7186a7"
  map-hatch-light: "#8393aa"
  map-selected: "#d7ff3f"
  map-selected-light: "#152100"
  warning-bg: "#342b13"
  warning-bg-light: "#fff3ce"
  warning-ink: "#f9d883"
  warning-ink-light: "#70500a"
  warning-line: "#a68b42"
  warning-line-light: "#c6a34b"
  info-bg: "#21283c"
  info-bg-light: "#edf0f8"
  info-ink: "#c1c9e7"
  info-ink-light: "#3b4264"
  error-bg: "#312141"
  error-bg-light: "#f3eaff"
  error-ink: "#e4b5ff"
  error-ink-light: "#652991"
  focus: "#c49aff"
  focus-light: "#7334c5"
  track: "#31405a"
  track-light: "#dbe2ed"
  accent-hover: "#c3ef21"
  chrome-focus: "#e8ceff"
typography:
  display:
    fontFamily: "Manrope, sans-serif"
    fontSize: "47px"
    fontWeight: 800
    lineHeight: 1.16
    letterSpacing: "-0.03em"
  headline:
    fontFamily: "Manrope, sans-serif"
    fontSize: "42px"
    fontWeight: 800
    lineHeight: 1.16
    letterSpacing: "-0.03em"
  title:
    fontFamily: "Manrope, sans-serif"
    fontSize: "27px"
    fontWeight: 750
    lineHeight: 1.25
    letterSpacing: "-0.025em"
  subheading:
    fontFamily: "Manrope, sans-serif"
    fontSize: "18px"
    fontWeight: 700
    lineHeight: 1.4
    letterSpacing: "-0.015em"
  body:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.6
  table:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "14px"
  label:
    fontFamily: "DM Sans, sans-serif"
    fontSize: "13px"
  candidate-value:
    fontFamily: "Manrope, sans-serif"
    fontSize: "45px"
    fontWeight: 750
    lineHeight: 1.15
    letterSpacing: "-0.035em"
rounded:
  track: "2px"
  party: "3px"
  badge: "4px"
  office: "5px"
  control: "6px"
  theme-group: "7px"
  notice: "8px"
  panel: "12px"
spacing:
  "4": "4px"
  "6": "6px"
  "8": "8px"
  "10": "10px"
  "12": "12px"
  "14": "14px"
  "16": "16px"
  "18": "18px"
  "20": "20px"
  "22": "22px"
  "24": "24px"
  "26": "26px"
  "28": "28px"
  "32": "32px"
  "40": "40px"
  "44": "44px"
  "48": "48px"
  "60": "60px"
  "64": "64px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.accent-ink}"
    rounded: "{rounded.control}"
    padding: "10px 14px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-secondary:
    backgroundColor: "transparent"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 14px"
  select:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "10px 12px"
  navigation:
    backgroundColor: "{colors.chrome}"
    textColor: "{colors.chrome-muted}"
  status-badge:
    backgroundColor: "{colors.surface-raised}"
    textColor: "{colors.ink}"
    rounded: "{rounded.badge}"
    padding: "5px 8px"
  warning-notice:
    backgroundColor: "{colors.warning-bg}"
    textColor: "{colors.warning-ink}"
    rounded: "{rounded.notice}"
    padding: "15px 18px"
  theme-selected:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.accent-ink}"
    rounded: "{rounded.badge}"
    padding: "7px 12px"
  data-panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
  geography-panel:
    backgroundColor: "{colors.map-base}"
    textColor: "{colors.ink}"
    rounded: "{rounded.panel}"
  candidate-summary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    padding: "26px 28px 18px"
---

# Design System: Arizona Election Explorer

## Overview

**Creative North Star: "Signal"**

Signal is a bold, clean, modern geographic data tool. Confident Manrope headings and figures establish the hierarchy; DM Sans keeps dense records, sources and familiar controls easy to scan. Color acts as a precise signal for party data, navigation, selected geography, focus and source warnings.

The working material is flat and tonal: cool light surfaces or blue-black dark surfaces beneath a consistently dark masthead. Actual Arizona geography, readable tables and factual source context carry the visual identity. The same content and exploration state survive a theme change. This remains an independent, unofficial public information project.

**Key Characteristics:**

- Bold typographic hierarchy with tabular numeric alignment.
- Vivid party data, nonpartisan lime selection and distinct violet focus.
- Flat tonal regions with restrained borders and familiar controls.
- Equivalent map, table and detail exploration across themes and viewport sizes.
- Source limitations and reporting dates remain visible beside the figures they qualify.

This record captures the approved, implemented Signal design system. The authoritative token implementation is `frontend/src/styles.css`; component behavior lives in `frontend/src/`. Election counts and reporting dates come from the application's data sources.

## Colors

Cool blue-black and white grounds support vivid, narrowly assigned signals. Frontmatter keys without a suffix describe the default dark theme; `-light` keys give light-theme overrides. Shared values have one entry. At runtime the same unsuffixed CSS custom properties resolve either theme; do not copy the documentation suffix into a CSS variable name. CSS declares light values at `:root` and dark overrides at `:root[data-theme="dark"]`; the boot policy selects dark unless a remembered explicit light preference exists.

### Primary

- **Signal Lime** (`accent`, `accent-ink`, `accent-hover`): selected theme control, primary action, masthead destination underline and nonpartisan geographic selection. `selection` is the quieter selected-row ground; `selection-edge` supplies the stronger edge/marker in each theme.

### Secondary

- **Party Blue** (`blue`, `blue-text`, `blue-wash`): Democratic chart bars, readable party figures and party-chip grounds respectively.
- **Party Red** (`red`, `red-text`, `red-wash`): equivalent Republican roles. Chart fills are not text colors. Map fills use the independently tuned `map-dem`, `map-rep` and `map-other` roles.

### Tertiary

- **Focus Violet** (`focus`, `chrome-focus`): keyboard focus, with the brighter shared masthead treatment. Violet recovery surfaces use `error-bg` and `error-ink`.
- **Caution Amber** (`warning-bg`, `warning-ink`, `warning-line`): stale, incomplete or otherwise qualified source notices. `info-bg` and `info-ink` provide quiet report context without claiming verification.

### Neutral

- **Blue-black / Cool Paper** (`canvas`, `surface`, `surface-raised`): page, data region and raised tonal/header ground. Both themes use the dark `chrome` masthead with `chrome-ink` and `chrome-muted` text.
- **Reading Ink** (`ink`, `muted`): primary and supporting copy; `line` groups data and `control-line` keeps interactive boundaries legible.
- **Other / Unavailable** (`neutral`, `neutral-text`, `track`): non-major-party data, readable neutral labels and bar tracks.
- **Geographic Ground** (`map-base`, `map-line`, `map-quiet`, `map-hatch`, `map-selected`): map field, boundaries, inactive geography, not-contested hatching and selected outline. White geographic labels retain their dark stroke; text labels and table controls accompany color.

**The Role Separation Rule.** Lime identifies navigation or geographic selection; blue and red identify labeled party data. Registration colors never imply candidate choices.

**The Theme Continuity Rule.** Changing theme changes presentation only: preserve data, sorting, selected geography, focus, request lifecycle and update streams.

## Typography

**Display Font:** Manrope, with sans-serif fallback.  
**Body Font:** DM Sans, with sans-serif fallback.

The pairing is confident and direct: tight Manrope headings and large figures above quiet DM Sans records. Both families are local assets in `frontend/public/fonts/`, normal styles at weights 400–800, with their OFL license files and swap loading. CSS requests intermediate weights such as 750 and 550; font synthesis is disabled, so do not claim separate supplied font files for those weights.

### Hierarchy

- **Display:** catalog heading; uses the frontmatter display role, then steps to 42px at 1200px, 34px at 560px and 31px at 350px.
- **Headline:** standard page heading; steps to 32px at 560px.
- **Title / Subheading:** section and panel hierarchy. Shared panel subheadings use Manrope; data labels stay DM Sans.
- **Candidate value:** leading candidate shares use the dedicated figure role; 38px at 1200px and 39px at 560px. Figures remain adjacent to names, party labels and vote counts.
- **Body:** normal copy uses the frontmatter body role. The methodology article keeps 16px text with 1.75 line-height and a 72ch reading measure, including on mobile.
- **Table / Label:** 14px table text; 13px supporting labels; 12px table headers, metadata and badges; 11px compact party identifiers. These are explicit roles, not a license to shrink ordinary prose.

Use tabular lining numerals for tables, values and definition-list figures. Long candidate and source names wrap rather than truncating essential identification.

## Layout

The desktop shell is centered at a maximum width of 1440px, with 48px horizontal gutters; main content has 32px top and 64px bottom padding. At 1200px gutters become 32px; at 560px they become 20px, with main padding 26px above and 40px below. Reused spacing values in frontmatter are observed measurements, not runtime CSS custom properties.

The catalog pairs a 196px office directory with the chronological archive and a 40px gap. At 900px the directory becomes 160px with a 24px gap; at 560px a labeled native office select replaces it. Year selects fill mobile width. Category tabs remain visible, with roving keyboard focus and no hidden menu dependency.

Exploration pairs a 392px map column with the table and a 24px gap, narrows the map to 340px at 1200px, then stacks at 900px. Main results/participation tables retain a 730px minimum width and readable text inside a contained, labeled, keyboard-focusable horizontal scroll region. Geographic identifiers become sticky at 900px. The document itself does not scroll horizontally. Selected details span the working area. Historical result details retain their two-column data arrangement, which collapses on mobile. Early-voting county details render only after selection: their four returned-ballot metrics form one row on desktop, two columns at 900px and below, and one column at 560px and below. Closing the selection removes the detail region.

Two leading candidate records sit side by side on wide screens and stack at 560px. Summary statistics move below them at 900px. The full remainder stays available through a native disclosure. Participation metrics become a compact mobile sequence without changing definitions or implying candidate results. Early-voting participation and freshness notices align heading and body baselines above 900px, then stack at 900px and below. The early-voting Sources & coverage heading and attribution share a horizontal baseline on desktop and wrap naturally on smaller screens; the existing site footer retains its alignment.

Methodology uses a 232px sticky contents column, a 60px gap and an article column up to 740px; at 900px it becomes a single column with collapsible contents, initially collapsed on small screens. Preserve the complete article. The masthead wraps navigation below brand/theme controls at 900px; at 350px the theme group takes its own row.

## Elevation & Depth

There are no shipping card shadows. Grouping comes from tonal fields, thin borders, separator rules and typography. The stylesheet's unused `--shadow` declaration is not an elevation system and is intentionally excluded from tokens. Selected office controls use an explicit edge, not a glow. The shared masthead is dark in both themes.

**The Flat Surface Rule.** Use tonal grounds and restrained borders to group data. Do not add decorative card shadows or lifted hover effects.

## Shapes

Controls have small, practical corners; badges and party labels are tighter; bounded map, table, snapshot and detail regions have the larger panel corner. Exact reused radii are normative in frontmatter. Flat result summaries use top/bottom rules rather than rounded cards. One-pixel borders define controls and data regions. The archive's circular arrow is a navigational affordance, not a general container shape. Geographic SVG paths keep real boundaries; inactive districts use diagonal hatching and text.

## Components

### Buttons and theme choice

Direct, familiar controls: ordinary buttons use surface ground, a control border, control radius and 10px by 14px padding; secondary buttons are transparent. Primary buttons use lime, dark accent ink and weight 650, with the documented hover color. Disabled buttons use 0.5 opacity and a not-allowed cursor. Baseline button/select minimum height is 44px; compact desktop contexts have their own measured sizes.

Theme choice is an explicit Light/Dark pressed-button group in the masthead, with a 7px group radius and 4px inner button radius. A selected option uses lime. The default is dark; valid explicit choices persist under `az-election-theme` and synchronize across tabs. Storage failure leaves the current tab usable. A polite status announces the selection. Theme controls do not own the router or data lifecycle.

### Inputs / Fields

The implemented fields are labeled native selects, not a custom search input. Use surface ground, readable ink, control outline and 6px corners. Office/year controls preserve their labels and normal keyboard interaction. Focus uses the same visible violet outline as other controls.

### Navigation

The dark masthead has pale text, muted inactive destinations and a lime underline on the current destination. Category tabs use a stronger selection underline and semantic selected state. The office directory uses a quiet selected ground and edge. Mobile keeps top navigation visible and replaces only the office directory with its equivalent native select.

### Status badges and notices

Compact, slightly rounded badges combine text with an inline icon; verified, provider, unofficial and incomplete meanings remain distinct. Amber notices precede qualified figures; informational and error notices use their semantic surfaces. Keep source publication dates distinct from retrieval/connection state. Background checking or refresh failure retains the last successful records. Loading uses static tonal skeletons plus a textual status; it does not invent figures.

### Data regions and candidate overview

Map/table/detail regions share tonal grounds, panel corners and thin boundaries. The candidate overview is a flat ruled region: two named leading candidates, labeled party chips, independently scaled share bars, votes and a separate contest-total/official-turnout context. The native disclosure reveals every remaining candidate. Provider wording remains source-specific. Missing shares have explicit unavailable text; no missing bar is presented as zero.

### Early-voting context and source disclosures

The statewide summary labels its actual retrieval timestamp with “Retrieved:” using the existing date formatter; it does not repeat publication or stale information there. The freshness warning retains refresh-failure and stale context. Calculations, API requests, caching and the live-update lifecycle retain their existing behavior.

The returned-ballot registration map keeps a compact caution with only its first sentence bold. A native “How colors are assigned” disclosure retains the complete color semantics, including Other, tied and missing breakdowns. Census boundary vintage and the map-or-table selection instruction remain quiet supporting text.

Selected county details keep the registration-versus-candidate-support clarification and the source’s Other-to-Independents meaning. The initially collapsed native “Definitions, coverage & reporting dates” disclosure retains each metric’s definition, coverage and partial-coverage qualifier, actual source-report date with its supplied precision, retrieval timestamp and stale indicator. Metrics without available values stay out of the selected county summary; their source definitions remain available when supplied. The county table omits the removed long N/A, partial-coverage and candidate-results paragraph.

The early-voting ending consists only of “Sources & coverage” and “Participation reports from civicAPI, which collects counts from state election offices.” The civicAPI name links to its early-vote source. Keep this approved compact attribution without a source register, report-date rows, help copy or a centered footer; source dates and coverage remain available in the county disclosure. This is an early-voting surface pattern within Signal.

### Linked geography, tables and details

SVG map shapes support Enter/Space activation and pressed state, backed by labeled legends and table controls. Selection links map outline, table row and inline detail; violet focus stays distinct from lime selection. Not-contested districts are hatched and inactive. Tables use semantic headers, announced sorting and an equivalent selection path for tiny geography. Selection moves focus to detail and announces a short summary; closing returns it to the initiating control. Initially open House details use the currently selected district's surviving table button when no origin was recorded.

Shared focus is a 3px violet outline with 4px offset; the masthead has its own brighter violet. Scroll containers bring the outline inside with a negative offset. Map focus additionally strengthens the selection stroke. Where motion is allowed, links, buttons and map shapes use 150ms ease-out color/background/filter feedback. Reduced-motion users receive no such transitions. There are no decorative entry effects or animated counts.

## Do's and Don'ts

### Do:

- **Do** use the actual semantic CSS variables so both themes retain their separately tuned text, chart, map and control roles.
- **Do** retain explicit source dates, verification labels, stale warnings and unavailable-value text beside the relevant data.
- **Do** preserve keyboard activation, visible focus, an equivalent table path and focus return after closing geographic details.
- **Do** preserve full candidate disclosure and the complete methodology article.
- **Do** keep mobile table text readable and scroll the labeled table region while geographic names remain visible.

### Don't:

- **Don't** use lime as a party color or blue/red as a neutral selection signal.
- **Don't** infer candidate support from party registration or turn missing data into zero.
- **Don't** replace actual geography with decorative imagery or add shipping raster assets to express this system.
- **Don't** make theme changes reset exploration, refetch election data or remount the live dashboard.
- **Don't** add decorative entry motion, animated counts, flip effects, glass or physical-material ornament.
