# Apple Health Data Import Guide

This document outlines the process for importing your Apple Health data set into the project's InfluxDB database. 

---

## ⚡ Quick Summary (TL;DR)
1. **Export**: On your iPhone, open the **Health App** ➔ Tap your Profile Icon ➔ Tap **Export All Health Data** (saves as `export.zip`).
2. **Upload**: Copy `export.zip` to the server at `/mnt/ssd/docker/health/Apple_Health/` (either via **SFTP/File Manager drag-and-drop** or **rsync**).
3. **Ingest**: The background watchdog daemon (`health_ingest`) automatically checks this folder every **2 minutes**. It will import your data and rename the file to `export_DDMonYYYY.zip` when finished. No manual commands or container restarts are needed.

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

### Step 2: Upload the File to Eadu
You must transfer the `export.zip` to Eadu. Ensure the final filename on the server is exactly `export.zip` (lowercase).

Choose **one** of the following methods to upload the file:

#### Method A: SFTP Client (No Code / Visual)
1. Open your favorite SFTP client (e.g., **Cyberduck**, **FileZilla**, **Transmit**, or your OS File Manager).
2. Connect to the **Eadu** server.
3. Navigate to:
   ```
   /mnt/ssd/docker/health/Apple_Health/
   ```
4. Drag and drop your local `export.zip` file into this folder.

#### Method B: Terminal (Command Line)
Run the following command from your local machine's terminal (replacing `/path/to/local/export.zip` with the actual path to your downloaded zip):
```bash
rsync -avz --progress "/path/to/local/export.zip" Eadu:/mnt/ssd/docker/health/Apple_Health/export.zip
```

---

## Verification (Optional)

You do not need to do anything once the upload is complete. However, if you wish to verify the import:

### 1. Check if the File was Archived
Check the `Apple_Health` directory on Eadu after 2-3 minutes.
```bash
ssh Eadu "ls -la /mnt/ssd/docker/health/Apple_Health"
```
You should see your file has been renamed to a date-stamped filename (e.g., `export_02Jul2026.zip`), confirming the watchdog daemon successfully processed it.

### 2. Stream the Live Logs
To watch the extraction and database batch insertion progress in real-time:
```bash
ssh Eadu "docker logs -f health_ingest"
```
