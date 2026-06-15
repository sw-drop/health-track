# Implementation Plan: Dashboard Remaining Tabs Wiring & Styling

This document outlines the planned frontend styling and layout changes for the remaining dashboard metrics. This plan has been parked to prioritize data import verification.

## Proposed Changes

### 1. Metric-Specific Styling & Formatting (app.js)
Currently, all charts use a uniform sage green color and generic line/bar logic. We will map specific metrics to distinct, visually pleasing muted tones that fit the Scandi aesthetic.
- **Vitals (Heart Rate, etc.)**: Muted Terracotta/Blush.
- **Activity (Steps, Energy)**: Muted Slate Blue/Steel.
- **Sleep/Mobility**: Soft Lavender/Plum.
- **Body**: Warm Sand/Taupe.

#### [MODIFY] `html/app.js`
- Define a `COLOR_PALETTE` mapping metric categories to specific Chart.js gradients and colors.
- Update `isBar` logic to correctly render `AppleStandHour` states and binary metrics as bar charts instead of line charts.
- Implement Chart.js linear gradients for the line charts (fading to transparent at the bottom) for a premium look.

### 2. Tab Layout & Responsive Grid (styles.css)
- Add subtle glassmorphism and backdrop-filters to the sticky header.
- Add micro-animations (scale on hover, soft shadow transitions) to the chart panels.
- Add a custom animated skeleton loader for when charts are fetching data.

#### [MODIFY] `html/styles.css`
- Add hover transitions and micro-animations to `.panel`.
- Improve the visual hierarchy of `.panel-value-container`.
- Ensure responsive behavior on mobile screens.

### 3. Cache Busting (index.html)
To ensure the changes propagate immediately behind Cloudflare:
#### [MODIFY] `html/index.html`
- Increment the cache-busting version strings for `app.js` and `styles.css`.

## Verification Plan
1. Deploy the changes using `./deploy.sh`.
2. Wait for Cloudflare cache to invalidate (via our version bumps).
3. Verify the dashboard visually on the browser.
