# k0rventen Apple Health Ingestion Work

This document captures the modifications and architecture adapted from the `k0rventen/apple-health-grafana` repository to handle parsing and ingesting Apple Health data for this project. 

It serves as context for any future AI sessions or developers iterating on the ingestion pipeline.

## Overview
The ingestion system (located in `./health_ingest/`) uses a Python background process (`ingest.py`) to parse massive Apple Health `export.xml` files efficiently using `lxml.etree.iterparse()`. This ensures the script doesn't run out of memory when parsing multi-gigabyte XML files.

## Formatters (`formatters.py`)
We heavily adapted the k0rventen formatters to handle specific Apple Health identifiers:
- **`AppleStandHourFormatter`**: Converts `HKCategoryValueAppleStandHourStood` strings into binary integers (0 or 1).
- **`SleepAnalysisFormatter`**: Crucially, this was updated to support modern iOS 16+ sleep stage granularities. 
  - Translates `HKCategoryValueSleepAnalysisAsleepDeep`, `Core`, `REM`, and `Awake` into numerical states (`0` through `4`).
  - **Minute-by-Minute Tracking**: Instead of just logging start/stop times, the formatter expands sleep records into a dense minute-by-minute array (`SleepAnalysisTimes-<device>`). This enables highly granular tracking of sleep state transitions in InfluxDB.
  - Also outputs a summary duration record (`SleepAnalysis`) with `start` and `stop` timestamps.

## Ingestion Loop (`ingest.py`)
- The script actively polls for the existence of `/data/export.zip`.
- Once found, it unzips it into a temporary directory and streams the XML using `etree.iterparse`.
- Points are translated to InfluxDB `Point` objects and synchronously written to the database in batches of `5000` to optimize memory and I/O.
- **Workout Routes**: Added support for extracting and parsing `workout-routes` `.gpx` files, mapping latitude, longitude, elevation, and dynamically calculated speed/distance metrics.

## Notes for Future Chats
- If the Apple Health XML schema changes (e.g., new sleep phases or datatype strings introduced in future iOS updates), you will need to add new keys to the `sleep_states_lookup` dictionaries in `formatters.py`.
- Because InfluxDB manages records by timestamp, you can safely re-run full historical exports to backfill data without needing to diff the files first.
