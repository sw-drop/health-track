# Sleep Dashboard Development Notes

This document summarizes the custom visual work implemented for the Sleep Dashboard (built using Chart.js) to visualize Apple Health sleep phase data.

## Features Implemented

### 1. Stacked Bar Chart for Sleep Phases
- A stacked bar chart represents the duration of different sleep phases per night.
- Tracks **Deep**, **Core**, **REM**, and **Awake** times.
- Uses a specific visually-pleasing color scheme derived from "Example 1" of the user's preferred stacked bar chart examples.

### 2. Sleep Score Overlay (Line Chart)
- A **Sleep Score** is calculated and overlaid as a line chart directly on top of the stacked bars.
- **Coloring**: The line is styled a vibrant **Scarlet/Red** (`#FF2400`) rather than the default green.
- **Z-Index Fixes**: Chart.js `order` properties are used to enforce that the line always draws on top of the bars, preventing the bars from obscuring the score trend.
- **Dynamic Y-Axis Scaling**: Rather than hardcoding the right-hand Y-axis to `0-100`, the axis dynamically scales to fit the minimum and maximum scores visible in the current time frame, preventing a squashed line chart.

### 3. Dynamic Visual Scaling for Long Durations
To prevent visual clutter on long timeline views, the line's thickness and data points dynamically scale down as the viewed duration increases:
- **1 Week & 1 Month**: Standard line thickness (`3px`) and full-sized points (`4px`).
- **6 Months**: Line thickness remains, but point sizes are halved (`1.5px`) so they don't bleed into each other.
- **1 Year**: Line thickness is reduced (`2px`) and points are shrunk to tiny indicators (`0.5px`).
- **Max View**: The line is minimized (`1.5px`) and points are completely hidden (`0px`) to show a pure trend line without any dotted clutter.

### 4. Interactive Tooltips
- When clicking or hovering over a specific day's bar, a tooltip/modal displays the aggregated summary for that night.
- It calculates and displays the exact duration of each sleep phase (Deep/Core/REM/Awake) alongside the total Sleep Score.
