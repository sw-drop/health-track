# Apple Health Data Import Guide

This document outlines the process for importing your Apple Health data set into the project's InfluxDB database. 

The ingestion process is managed by an **automatic background watchdog daemon** (`health_ingest`) running on the server (`Eadu`). It polls for new data exports, processes them, and archives them automatically.

---

## How Ingestion Works

1. **Watchdog Daemon**: The `health_ingest` container runs continuously in the background and checks for a new `/data/export.zip` file every **120 seconds (2 minutes)**.
2. **Batch Processing**: When a new file is detected, it unzips it and streams the records in batches of 5,000 to the database (saving CPU and RAM).
3. **Automatic Archiving**:
   * **On Success**: The daemon renames the file to `export_ddmmmyyyy.zip` (e.g., `export_02Jul2026.zip`) to archive the file and prevent it from being processed again. If a file with that name already exists (e.g., multiple imports on the same day), it automatically appends a counter (e.g., `export_02Jul2026_1.zip`).
   * **On Failure**: If the upload is corrupt or the zip fails to extract, the daemon renames the file to `export_failed_ddmmmyyyy.zip` to prevent getting stuck in an infinite failure loop.
4. **Idempotence**: Importing the full data set multiple times is completely safe. InfluxDB uses timestamps and measurements as unique keys, so re-ingesting data simply performs an upsert (overwrite/merge) without creating duplicates.

---

## Step-by-Step Import Process

### Step 1: Export Data from Apple Health
1. Open the **Health app** on your iPhone.
2. Tap your profile picture in the top-right corner.
3. Scroll to the bottom and tap **Export All Health Data**.
4. Confirm and wait for the export to generate (this can take a few minutes).
5. Once completed, AirDrop, email, or save the resulting `export.zip` file to your computer.

### Step 2: Upload the File to the Server
Upload the `export.zip` file directly to the project's data directory on Eadu. 

Run the following command from your local machine (replacing `/path/to/local/export.zip` with the actual path to your downloaded zip):
```bash
rsync -avz --progress "/path/to/local/export.zip" Eadu:/mnt/ssd/docker/health/Apple_Health/export.zip
```
> [!IMPORTANT]
> The target filename on the server **must** be exactly `export.zip` for the daemon to detect it.

### Step 3: Wait for Ingestion
The background watchdog will automatically detect the file within 2 minutes of uploading. 

* The ingestion process typically takes **1 to 2 minutes** to parse and load ~2.4 million records.
* Once finished, the file on the server will automatically rename to `export_DDMonYYYY.zip`.

---

## Monitoring Ingestion Progress (Optional)

If you want to watch the progress of the import in real-time, run the following commands:

### 1. Stream the Logs
To watch the extraction and database batch insertion progress:
```bash
ssh Eadu "docker logs -f health_ingest"
```

### 2. Verify Ingestion Completed
To verify the file was renamed and archived:
```bash
ssh Eadu "ls -la /mnt/ssd/docker/health/Apple_Health"
```
You should see your file listed under its new archived name (e.g., `export_02Jul2026.zip`).
