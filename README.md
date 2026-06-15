# Apple Health & Eufy Dashboard

A custom health dashboard that visualizes Apple Health data (which also contains synchronized Eufy scale data), featuring an interactive UI with tracking charts, sleep timelines, and secure data obfuscation.

## Project Architecture

This application consists of several main Docker containers running on a server (`Eadu`):

1. **Python Ingestion Worker (`health_ingest`)**
   - A background container that processes Apple Health XML exports (`export.zip`).
   - Uses `etree.iterparse` to stream the massive XML file efficiently.
   - Mathematically interpolates raw sleep blocks into minute-by-minute sleep states (`SleepAnalysisTimes`).
   - Inserts all health records securely into InfluxDB.

2. **Python API Backend (`health_api`)**
   - Runs `api.py` serving a REST API to query InfluxDB.
   - Dynamically calculates daily sleep scores, duration, and consistency on the fly.
   - Returns JSON data formatted for Chart.js.

3. **Nginx Frontend (`health_dashboard`)**
   - Serves the static HTML, CSS, and Vanilla JS files from the `html/` directory.
   - Uses a minimalist **Scandi aesthetic** (clean off-white background, pill-shaped buttons, airy spacing, and soft sage green accents).
   - Acts as a reverse proxy, securely routing all `/api/*` requests to the Python API.

## Deployment & Data Ingestion

This repository lives locally, but the live application runs remotely on `Eadu`. 

**Deploying Code:**
Use the deployment script to push code changes:
```bash
./deploy.sh "commit message"
```
This script will commit your code to Git, rsync it to the server, and restart the containers.

**Ingesting Data (Important!):**
Do **not** use `deploy.sh` to transfer Apple Health data, as it will commit the massive zip file to the Git repository. Instead, manually transfer the file and trigger ingestion:

```bash
# 1. Safely wipe the existing data in the health bucket (if required to prevent duplicates)
# 2. Rsync the data directly to the volume without git
rsync -avz "Apple_Health/export 15Jun2026.zip" Eadu:/mnt/ssd/docker/eufy/Apple_Health/export.zip

# 3. Trigger the background worker
ssh Eadu 'docker start health_ingest'
```

## UI Features & Data Visualization

The dashboard visualizes core metrics imported from Apple Health, such as:
- **Sleep & Rest**: Sleep scoring, timelines, and phase analysis.
- **Vitals & Activity**: Heart Rate, Step Count, Energy Burned, etc.
- **Body Measurements**: Weight, Body Fat % (synced from Eufy).

### Missing Data & Chart Rendering
- **Chronological X-Axis**: The charts utilize the `chartjs-adapter-date-fns` library to enforce a strict `time` scale instead of a `category` scale, ensuring gaps in data are proportionally rendered.
- **Span Gaps**: The frontend charts are configured with Chart.js's `spanGaps: true`. This allows line charts to connect smoothly across missing data points rather than plunging to zero.

### Cloudflare Caching & Cache-Busting
Because Cloudflare aggressively caches frontend assets (`app.js`, `styles.css`), frontend changes will not immediately take effect on the live environment without cache-busting.
- When making modifications to frontend code, always increment the version string in `html/index.html` (e.g., `<script src="app.js?v=10"></script>`).

## Directory Structure

- `/html`: Contains the frontend UI (`index.html`, `app.js`, `styles.css`).
- `/health_api`: Flask API backend that queries InfluxDB.
- `/health_ingest`: Python worker to parse Apple Health `.zip` files and insert into InfluxDB.
- `/Apple_Health`: Directory for staging Apple Health exports.
- `nginx.conf`: Nginx unified routing and reverse proxy rules.
- `deploy.sh`: Deployment script to sync files and rebuild Docker containers on `Eadu`.
- `docker-compose.yml`: Container orchestration definitions.
