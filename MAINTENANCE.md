# Health Dashboard Maintenance Guide

This document outlines standard administrative tasks to keep the application running cleanly, manage space on the server (`Eadu`), and safeguard/manipulate user data in InfluxDB.

---

## 💾 1. Database Backups & Recovery

The active database runs on `Eadu` in a global container named `influxdb` (version 2.7). To perform backups without downtime, we execute the native InfluxDB backup tools inside the container and extract the results to the host SSD.

### How to Back Up Data
1. Retrieve your `INFLUX_TOKEN` from the `docker-compose.yml` or `.env` file in `/mnt/ssd/docker/health/`.
2. Run the backup command on `Eadu` to back up all buckets (including `health` and database metadata):
   ```bash
   # 1. Run backup inside the container
   ssh Eadu "docker exec influxdb influx backup --token <INFLUX_TOKEN> /var/lib/influxdb2/health_backup_\$(date +%Y%m%d)"
   
   # 2. Copy the backup directory out of the container to the host project folder
   ssh Eadu "docker cp influxdb:/var/lib/influxdb2/health_backup_\$(date +%Y%m%d) /mnt/ssd/docker/health/backups/"
   
   # 3. Clean up the temporary backup inside the container
   ssh Eadu "docker exec influxdb rm -rf /var/lib/influxdb2/health_backup_\$(date +%Y%m%d)"
   ```
This stores a self-contained backup folder under `/mnt/ssd/docker/health/backups/`.

### How to Restore Data
1. Copy the target backup directory back into the container:
   ```bash
   ssh Eadu "docker cp /mnt/ssd/docker/health/backups/health_backup_<YYYYMMDD> influxdb:/var/lib/influxdb2/"
   ```
2. Execute the restore utility:
   ```bash
   ssh Eadu "docker exec influxdb influx restore --token <INFLUX_TOKEN> /var/lib/influxdb2/health_backup_<YYYYMMDD>"
   ```
3. Remove the restored folder inside the container:
   ```bash
   ssh Eadu "docker exec influxdb rm -rf /var/lib/influxdb2/health_backup_<YYYYMMDD>"
   ```

---

## 🧹 2. Database Wiping & Resetting

If you ever need to perform a clean start (e.g., re-ingesting Apple Health data from scratch without risking duplicate edge cases):

### Reset the InfluxDB Bucket
Wiping a bucket deletes all its stored measurements but keeps your tokens, user configurations, and dashboard setups intact.
```bash
# 1. Delete the health bucket
ssh Eadu "docker exec influxdb influx bucket delete --name health --token <INFLUX_TOKEN> --org my-org"

# 2. Re-create the empty health bucket
ssh Eadu "docker exec influxdb influx bucket create --name health --token <INFLUX_TOKEN> --org my-org"
```

---

## 📝 3. Deleting Specific Data Records (Manual Pruning)

InfluxDB v2 is a time-series database and does not support traditional SQL delete queries. To prune specific erroneous records (like double-logged entries), use the InfluxDB REST API to delete data inside a targeted **time window** and **measurement**.

### Delete Command Template
Run this command on `Eadu` (or adjust local hostname/token if running elsewhere):
```bash
curl -X POST "http://localhost:8086/api/v2/delete?org=my-org&bucket=health" \
  -H "Authorization: Token <INFLUX_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "start": "YYYY-MM-DDTHH:MM:SSZ",
    "stop": "YYYY-MM-DDTHH:MM:SSZ",
    "predicate": "_measurement=\"<MEASUREMENT_NAME>\""
  }'
```
* **`start` / `stop`**: The exact RFC3339 UTC time window containing the targeted records. Use a tight, narrow window (e.g., a 10-second gap) to avoid deleting valid surrounding data.
* **`predicate`**: Filters which measurement is targeted (e.g. `_measurement="BodyMass"` or `_measurement="StepCount"`).

---

## 🗑️ 4. Server SSD Housekeeping & Disk Space Pruning

To keep the `Eadu` SSD (`/mnt/ssd`) clean and prevent disk pressure:

### Prune Old Apple Health Zip Exports
Ingested data is stored permanently in InfluxDB. Once the watchdog daemon successfully ingests and renames the export zip files under `/mnt/ssd/docker/health/Apple_Health/`, you do not need to keep old files.
* **To clean up all historical archived zip files**:
  ```bash
  ssh Eadu "rm /mnt/ssd/docker/health/Apple_Health/export_*.zip"
  ```
  *(Keep the latest archive if you want a safety copy, but they are safe to delete).*

### Docker Build & Log Pruning
* **Clean up unused docker builder layers and intermediate dangling images**:
  ```bash
  ssh Eadu "docker builder prune -f && docker image prune -f"
  ```
* **Clear docker log files**:
  While container logs are capped at `30MB` max in `docker-compose.yml`, you can truncate them manually if needed:
  ```bash
  ssh Eadu "truncate -s 0 /var/lib/docker/containers/*/*-json.log"
  ```

---

## 🔍 5. Troubleshooting & Ingestion Monitoring

### Check Container Status
Verify that both the web API and watchdog daemon are running:
```bash
ssh Eadu "docker ps | grep health"
```

### Check watchdog Ingestion Logs
Verify if the watchdog is actively sleeping or running:
```bash
ssh Eadu "docker logs health_ingest"
```
To stream logs in real-time while uploading:
```bash
ssh Eadu "docker logs -f health_ingest"
```
