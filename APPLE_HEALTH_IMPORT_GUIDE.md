# Apple Health Data Import Guide

This document outlines the process for manually importing your full Apple Health data set into the project's InfluxDB database. 

Because InfluxDB is a time-series database that uses the record timestamp, measurement name, and tags as a unique identifier, **importing the full data set multiple times is safe and will not destroy or duplicate existing records.** It simply upserts (overwrites or merges) the data points for those exact timestamps.

## Prerequisites
- You must have an iPhone with Apple Health data.
- The `health_ingest` docker container must be configured in `docker-compose.yml`.

## Step-by-Step Import Process

1. **Export Data from Apple Health:**
   - Open the **Health app** on your iPhone.
   - Tap your profile picture in the top right corner.
   - Scroll down to the bottom and tap **Export All Health Data**.
   - Confirm and wait for the export to generate (this can take a few minutes).
   - Once generated, AirDrop or save the resulting `export.zip` file to your computer.

2. **Move the File to the Project Directory:**
   - Move or copy the exported zip file into the project's dedicated ingestion folder:
     ```
     /Users/gary/syncdata/Sync/dev/eufy-scales/Apple_Health/
     ```
   - Ensure the file is exactly named **`export.zip`**. (If it exported with a date like `export 15Jun2026.zip`, rename it to `export.zip` so the ingestion script can find it).

3. **Run the Ingestion Container:**
   - Open your terminal and navigate to the project directory:
     ```bash
     cd /Users/gary/syncdata/Sync/dev/eufy-scales
     ```
   - Start the ingest container manually (it is set to `restart: "no"` by default):
     ```bash
     docker compose up health_ingest
     ```
   - The container will start `ingest.py`, detect the `/data/export.zip` file, extract the `export.xml`, and begin streaming the records in batches of 5,000 to the InfluxDB instance.
   - Wait for the console to output `Ingestion complete!` and then you can stop/remove the container.

4. **Verify:**
   - Refresh your Grafana or custom web dashboard to see the newly populated Apple Health data.
