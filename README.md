# Eufy Scales Dashboard

A health dashboard that pulls and visualizes data from Eufy smart scales, featuring an interactive UI with tracking charts, manual entry capabilities, and secure data obfuscation for casual viewing.

## Project Architecture

This application consists of two main Docker containers running on a DietPi server (`Eadu`):

1. **Python API Backend (`eufy-export`)**
   - Connects to Bluetooth/Eufy APIs to pull down live scale data.
   - Runs `api.py` serving a REST API to retrieve and securely modify the scale records.
   - Uses host networking (`network_mode: host`) to directly interface with local BLE adapters.
   - Stores the live health data securely in the `/data/eufy_data.json` file.

2. **Nginx Frontend (`eufy-dashboard`)**
   - Serves the static HTML, CSS, and JS files from the `html/` directory.
   - Also uses host networking, natively listening on port `8085`.
   - Acts as a reverse proxy: it serves the web UI at `/` and securely routes all API requests (`/api/*`) internally to the Python API running on port `8086`.

## Deployment Pipeline (Important!)

This repository lives locally, but the live application runs on the remote DietPi server (`Eadu`). To push changes to the server and restart the application, a deployment script is provided.

**How to deploy changes:**
Simply run the deployment script from the project root:
```bash
./deploy.sh
```

This script will automatically:
1. `rsync` all code changes to `Eadu:/docker/eufy/` (safely ignoring your live `data/` directory).
2. Connect to the server via SSH.
3. Rebuild and restart the Docker containers.

## UI Features & Data Visualization

The dashboard visualizes four core health metrics:
- **Weight**: Main chart tracking long-term trends.
- **Body Fat %**: Tracking overall composition.
- **BMI (Body Mass Index)**: Auto-calculated dynamically based on weight and a fixed height profile (1.8542 m / 6'1").
- **Visceral Fat**: Level rating scale.

*Note: Outdated metrics (such as Muscle Mass and Bone Mass) have been removed from the UI to ensure a focused dashboard.*

### Missing Data & Chart Rendering
- Incomplete records (e.g., records created with only weight data or missing visceral/body fat) have missing parameters set to `null` (not `0` or `0.0`) in the database.
- The frontend charts are configured with Chart.js's `spanGaps: true`. This allows line charts to connect smoothly across missing data points rather than plunging to zero or causing Y-axis scaling issues.

### Cloudflare Caching & Cache-Busting
Because Cloudflare aggressively caches frontend assets (`app.js`, `styles.css`), frontend changes will not immediately take effect on the live environment without cache-busting.
- When making modifications to frontend code, always increment the version string in `html/index.html` (e.g., `<script src="app.js?v=10"></script>` and `<link rel="stylesheet" href="styles.css?v=3">`).

## UI Data Obfuscation

For privacy when showing the dashboard to others, the main charts and text indicators do **not** display true absolute weights by default. Instead, they display a relative offset (e.g. `+18.4 kg`).
- To reveal the true weights, click the **Edit Data** button and enter the authorized PIN (`2364`).
- The UI will verify the PIN with the backend, un-obfuscate the charts, and open the data management table.

## Data Management & Manual Entries

When the Bluetooth BLE interface is down, or for backfilling historical logs, data records can be added manually.
- Click **Edit Data**, enter the PIN, and use the **Add Record** row at the top of the data table.
- **Backdating**: The manual entry interface uses a `datetime-local` input, allowing you to backdate records to any specific date and time rather than defaulting to the current time.
- **Automatic Calculations**: If Weight is entered, BMI is computed automatically based on the height profile (1.8542 m).

### Remote Database & Server Timezones
- The live database resides on the DietPi server at `Eadu:/docker/eufy/data/eufy_data.json`.
- The DietPi server system clock operates in **UTC**, while historical exports (like CSV backups) or user input devices might operate in **BST** (British Summer Time) or other local zones.
- When merging datasets, a fuzzy-matching script (`scripts/merge_visceral_fuzzy.py`) is used to pair records within an hour window to reconcile timezone discrepancies.

## Directory Structure

- `/html`: Contains the frontend UI (`index.html`, `app.js`, `styles.css`).
- `/data`: Mounted live data folder containing `eufy_data.json` and backup database logs. (Note: `./data` is excluded from the deploy sync to prevent overwriting live data).
- `/scripts`: Utility scripts for database maintenance:
  - `import_csv.py`: Imports historical data from CSV files.
  - `merge_visceral_fuzzy.py`: Fuzzy-matches and merges missing visceral fat or body fat metrics into live records using a 1-hour timezone tolerance.
  - `fix_data.py`: Smoothes outlier data.
- `/backups`: Local directory for historical database and CSV backups.
- `nginx.conf`: Nginx unified routing and reverse proxy rules.
- `deploy.sh`: Deployment script to sync files and rebuild Docker containers on `Eadu`.
