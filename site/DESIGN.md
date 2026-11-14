---
name: KRect Web
description: A paper manual for putting windows in place.
colors:
  desk: "#e4eff6"
  paper: "#fff"
  ink: "#1d2935"
  muted: "#536674"
  blue: "#1472aa"
  blue-soft: "#e7f3fc"
  rule: "#d8e1e8"
typography:
  display:
    fontFamily: "SUIT, sans-serif"
    fontSize: "clamp(38px, 4.7vw, 65px)"
    fontWeight: 780
    lineHeight: 1.18
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "SUIT, sans-serif"
    fontSize: "clamp(30px, 3.3vw, 44px)"
    fontWeight: 780
    lineHeight: 1.18
    letterSpacing: "-0.035em"
  title:
    fontFamily: "SUIT, sans-serif"
    fontSize: "18px"
    fontWeight: 750
  body:
    fontFamily: "SUIT, sans-serif"
    fontSize: "16px"
    lineHeight: 1.7
  label:
    fontFamily: "SUIT, sans-serif"
    fontSize: "14px"
    lineHeight: 1.6
  japanese:
    fontFamily: 'SUIT, "Noto Sans CJK JP", "Noto Sans JP", "Hiragino Kaku Gothic ProN", Meiryo, sans-serif'
rounded:
  control: "6px"
  compact: "5px"
spacing:
  compact: "8px"
  control: "14px"
  body: "20px"
  rhythm: "24px"
  sheet-gap: "28px"
components:
  button-primary:
    backgroundColor: "{colors.blue}"
    textColor: "{colors.paper}"
    rounded: "{rounded.control}"
    padding: "14px 22px"
  button-primary-hover:
    backgroundColor: "#0c608f"
  button-text:
    backgroundColor: "transparent"
    textColor: "{colors.blue}"
    padding: "4px"
  choice-selected:
    backgroundColor: "{colors.blue-soft}"
    textColor: "{colors.blue}"
    rounded: "{rounded.control}"
  paper-sheet:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "3px 3px 6px 3px"
---

# Design System: KRect Web

## Overview

**Creative North Star: "A small paper manual for putting windows in place"**

White sheets sit on a cool blue desk. Dark ink, generous margins, and a single blue action color extend the existing KRect icon into a calm, practical web surface. Curled corners provide a small tactile cue without turning the page into a simulation of a book.

This document describes the web implementation in `template.html`, `assets/site.css`, `assets/site.js`, and the Korean, English, and Japanese locale files. It does not redefine the native Qt application's design system. The existing KRect icon, real app screenshot, and live Snap captures remain the visual link to that application. The surface strategy is recorded separately in [`../.impeccable/surfaces/site-template-html.md`](../.impeccable/surfaces/site-template-html.md).

**Key Characteristics:**

- Cool blue surroundings, white paper, and restrained ink typography.
- Broad sheets with small lifted corners and soft structural shadows.
- Locally hosted SUIT for Korean and English, with system glyph fallbacks for Japanese.
- Explicit controls, visible selection states, and short user-triggered motion.

## Colors

The palette is cool and low in saturation around a clear blue accent. Frontmatter values match the CSS custom properties and are normative; small illustration and state-specific colors remain local to their components.

### Primary

- **KRect Blue** (`blue`): primary download actions, emphasized headline lines, links, selected controls, focus outlines.
- **Soft Blue** (`blue-soft`): selected package and placement surfaces; it supports the stronger blue border or label.

### Neutral

- **Desk Blue** (`desk`): the page canvas and the exposed area beneath each curled corner.
- **White Paper** (`paper`): the main sheets.
- **Ink** (`ink`): headings and ordinary text.
- **Muted Ink** (`muted`): explanatory copy, captions, supporting labels, and inactive demo controls.
- **Paper Rule** (`rule`): separators and the quiet borders around package choices.

**The Selection Rule.** A selected control combines its color treatment with a semantic checked or pressed state; color alone does not carry selection.

## Typography

**Display and body font:** locally hosted SUIT Variable, with a sans-serif fallback. Its declared weight range is 100–900 and it uses `font-display: swap`. The Japanese page uses the frontmatter `japanese` stack to supply Japanese glyphs through available system fonts; no additional Japanese font is downloaded. The install command alone uses `ui-monospace, monospace`; shortcut labels use SUIT.

Heavy, tightly spaced display type gives the page a compact visual anchor. Body copy is lighter, with open line spacing and measured widths. The Korean default, English, and Japanese pages share the same hierarchy and layout. Japanese changes glyph fallback and uses `word-break: normal` for the hero introduction; the other locales retain the introduction's `keep-all` behavior.

### Hierarchy

- **Display:** the frontmatter display role is the desktop hero title. At widths up to 720px it becomes `clamp(35px, 9vw, 52px)`; headline wrapping is balanced.
- **Headline:** the frontmatter headline role introduces the Snap, native-feature, and download paper sheets. The FAQ heading is smaller, at 30px on desktop and 27px on mobile.
- **Title:** feature terms use the title role; the smaller compatibility heading is 17px.
- **Body:** paragraphs use the body role; feature definitions use a slightly tighter 1.65 line height. The hero introduction is 20px, reducing to 18px at 1000px and 17px at 720px, with a 29ch measure and Korean word preservation.
- **Label:** the frontmatter label role describes supporting text. Navigation uses 15px/650 on desktop; primary buttons use 17px/750. Compact demo controls and captions have their own smaller scale and must remain secondary.

## Layout

The centered content area is at most 1200px wide, with 64px total outer space. This becomes 40px at widths up to 1000px and 28px at widths up to 720px. The header is 104px high on desktop and 83px on mobile. Paper sheets are separated by the sheet-gap token, reduced to 20px on mobile.

The page has four paper sheets: cover, Snap usage and evidence, native features, and download. Desktop paper sections use two columns. The cover pairs equal columns with a 34px gap and `76px 58px 0` padding; its bottom facts row spans both columns. The Snap sheet uses `0.9fr 1.1fr` columns with a 64px gap, placing guidance beside two vertically stacked captures. Snap, feature, and download sheets share `70px 64px` padding; feature and download gaps are 76px and 80px respectively. At 1000px these three sections tighten to `54px 40px` with 40px gaps. At 720px they become single-column sheets with `38px 26px 48px` padding, so Snap evidence follows the guidance; the cover uses `34px 26px 0` and places the demo below the copy. At 1300px and above the cover has a 650px minimum height.

The FAQ rests directly on the desk, with an 860px maximum width and divider-separated disclosures. The footer also rests on the desk. On mobile the footer wraps and its links take a full row; the header keeps GitHub and links to the two other languages while hiding its extra download shortcut. Package choices stack at the intermediate breakpoint and return to a compact pair within the full-width mobile form.

These are observed web layouts, not requirements for native Qt screens. Maintain all three languages when changing widths or copy: the page is generated as complete documents at `/`, `/en/`, and `/ja/`, not switched through a client-side text replacement. The Japanese website does not imply a Japanese native app UI; the app currently supports Korean and English.

## Elevation & Depth

Depth is structural and soft. Sheets use the shared `--shadow` value, separating paper from the blue desk without a visible outline. The monitor, its two illustrated windows, and the real app screenshot have their own smaller local shadows. Paper folds use a clipped gradient and drop shadow to expose the desk below. These gradients describe the pinned paper material; they are not a general accent treatment.

**The Paper Rule.** Main section surfaces stay quiet at rest. The fold responds to hover and keyboard focus; the whole sheet does not tilt or float.

Exact shadows, easing, durations, focus outlines, and breakpoints are in the site-scoped [sidecar](.impeccable/design.json). The frontmatter intentionally carries no motion or shadow token group.

## Shapes

Paper has nearly square, subtly asymmetric corners. Controls use the control radius; illustrated windows and the install command use the compact radius. The monitor frame is more rounded (12px), while the screenshot uses 7px. These local radii describe distinct objects rather than a universal card style.

The page-curl target occupies a 68px square at the lower right of the first three sheets, reducing to 52px on mobile. A triangular clipped span forms the fold. Layout symbols are simple CSS window outlines and filled regions; external-link and download icons are inline SVG. Shortcut arrows remain meaningful keyboard notation, not decorative icons.

## Components

### Buttons and links

Primary actions are blue, solid, and gently rounded, with a minimum height of 52px. The hero action has space between its text and SVG arrow; the download action fills the form width and centers its label. Hover darkens the blue.

The header download link is outlined. Content links use blue and a heavier weight; ordinary links underline on hover. Copy is a small text button with a 44px minimum target. All links, buttons, inputs, and summary controls share a 3px blue `:focus-visible` outline with a 5px offset.

### Package controls and free download

Package choices are native radio controls inside bordered labels. The checked label gains a blue border and soft-blue fill; its title and technical subtitle remain distinct.

The download action directly retrieves the selected Ubuntu package for free. There is no price selection or payment step. Supporting text keeps the absence of an account or payment requirement clear.

The installation command follows the selected Ubuntu package. Copy confirmation lasts two seconds; clipboard failure asks the user to select and copy manually. Without JavaScript, direct download links remain available and interactive-only controls are hidden.

### Paper-curl navigation

Each curl is a real, labeled anchor: cover to Snap (`#snap`), Snap to features (`#features`), then features to download (`#download`). The small text link below the hero action also reaches Snap. The curl span shifts from `translate(-3px, -3px)` to `translate(-11px, -11px)` on hover or focus over 0.55 seconds. This is a link with a small lifted-corner response, not a page-turn transition. The fourth, download sheet has no curl.

### Snap guidance and live captures

The Snap sheet pairs a three-step ordered list with two unchanged live captures. Its blue, heavy list markers establish sequence without becoming separate badges. The list uses 24px left padding, `28px 0` margins, and 1.7 line height; each item adds 6px of left padding and 14px of bottom spacing. Smaller paragraphs explain cancellation and the requirement to keep KRect running in the tray.

The landscape and portrait Snap-bar captures each retain their 648 × 120 source proportions, fill the available column width, and link to the full image. They are evidence, not interactive web controls or redrawn illustrations. Each figure has 28px of bottom spacing and a muted 14px caption with 1.6 line height, separated from the image by 12px. A final environment note sits below a paper-rule border with 16px top padding. Preserve the captures' actual KDE appearance and the caption identifying Plasma 5.27 / X11; the existing native app screenshot remains explicitly captioned as version 0.2.0 even while Snap is introduced as 0.3.0.

### Window-placement illustration

A framed desktop contains a reference window, a blue active window, and a bottom panel. Five explicit buttons select left, right, third, center, or maximize, update the pressed state, and announce the matching shortcut through a polite live region. The illustration is labeled as a browser model; it does not control the visitor's desktop.

The desktop container uses layout/paint containment and clipping. Changes to the active window's position and size are bounded within it and transition for 0.7 seconds; maximizing leaves the illustrated bottom panel clear. There is no autoplay. Reduced-motion preference removes these transitions and the curl transition, and changes smooth scrolling to immediate scrolling while preserving every action.

### App evidence, disclosures, and navigation

The real app screenshot is linked to its full image and accompanied by an environment-specific caption. Preserve the supplied KRect icon, app screenshot, and Snap captures instead of reinterpreting the native UI through the web palette. The five FAQs use native `details` and `summary`, with visible focus and readable paragraph measures. Header and footer navigation remain ordinary links. Every page's header offers links to the two other languages, labeled in those languages with `lang` and `hreflang` attributes, and a skip link reaches the main content.

## Do's and Don'ts

### Do:

- **Do** keep the paper-and-desk material, KRect icon, and blue action color coherent across all three website languages.
- **Do** preserve semantic selection, keyboard focus, labeled corner links, and reduced-motion behavior.
- **Do** keep the illustrative demo distinct from the real app screenshot and live Snap captures through their existing labels and captions.
- **Do** keep package selection, the free download destination, and the installation command consistent.

### Don't:

- **Don't** apply this web document as a replacement for the native Qt application's design identity.
- **Don't** turn a corner link into an automatic animation or imply a full page-turn interaction that the code does not provide.
- **Don't** replace the locally hosted SUIT type, Japanese glyph fallbacks, or existing KRect assets with unrelated branding.
- **Don't** use decorative Unicode arrows where the page uses inline SVG; retain actual shortcut notation as text.
