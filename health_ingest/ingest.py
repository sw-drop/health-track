import os
import zipfile
import tempfile
import time
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import xml.etree.ElementTree as etree
from datetime import datetime
import glob
import gpxpy

from formatters import (
    parse_date_as_timestamp, 
    parse_float_with_try, 
    AppleStandHourFormatter, 
    SleepAnalysisFormatter
)

ZIP_PATH = '/data/export.zip'
INFLUX_URL = os.environ.get('INFLUX_URL', 'http://influxdb:8086')
INFLUX_TOKEN = os.environ.get('INFLUX_TOKEN', 'my-super-secret-auth-token')
INFLUX_ORG = os.environ.get('INFLUX_ORG', 'my-org')
INFLUX_BUCKET = os.environ.get('INFLUX_BUCKET', 'health')

def dict_to_point(d: dict) -> Point:
    p = Point(d["measurement"])
    for k, v in d.get("tags", {}).items():
        if v is not None:
            p = p.tag(str(k), str(v))
    for k, v in d.get("fields", {}).items():
        if v is not None:
            p = p.field(str(k), v)
    
    t = d["time"]
    if isinstance(t, int):
        p = p.time(t, WritePrecision.S)
    else:
        p = p.time(t)
    return p

def format_record(record: dict) -> list:
    measurement = record.get("type", "Record").replace("HKQuantityTypeIdentifier", "").replace("HKCategoryTypeIdentifier", "").replace("HKDataType", "")
    
    if measurement == "AppleStandHour":
        return AppleStandHourFormatter(record)
    if measurement == "SleepAnalysis":
        return SleepAnalysisFormatter(record)
        
    date = parse_date_as_timestamp(record.get("startDate", "2024-01-01T01:01:01"))
    value = parse_float_with_try(record.get("value", 1))
    unit = record.get("unit", "unit")
    device = record.get("sourceName", "unknown")

    return [{
        "measurement": measurement,
        "time": date,
        "fields": {"value": value},
        "tags": {"unit": unit, "device": device},
    }]

def format_workout(record: dict) -> dict:
    measurement = record.get("workoutActivityType", "Workout").replace("HKWorkoutActivityType", "")
    date = parse_date_as_timestamp(record.get("startDate", "2024-01-01T01:01:01"))
    value = parse_float_with_try(record.get("duration", 0))
    unit = record.get("durationUnit", "unit")
    device = record.get("sourceName", "unknown")

    return {
        "measurement": measurement,
        "time": date,
        "fields": {"value": value},
        "tags": {"unit": unit, "device": device},
    }

def process_workout_routes(write_api, extract_dir):
    routes_path = os.path.join(extract_dir, "apple_health_export", "workout-routes")
    if not os.path.exists(routes_path):
        print("No workout routes found, skipping...")
        return
        
    gpx_files = glob.glob(os.path.join(routes_path, "*.gpx"))
    print(f"Loading {len(gpx_files)} workout routes...")
    
    points = []
    for route_file in gpx_files:
        with open(route_file, "r") as f:
            try:
                gpx = gpxpy.parse(f)
                for track in gpx.tracks:
                    slug_name = track.name.replace(" ", "-").replace(":", "-").lower() if track.name else "unknown"
                    for segment in track.segments:
                        pts = segment.points
                        for i in range(len(pts)):
                            pt = pts[i]
                            next_pt = pts[i+1] if i+1 < len(pts) else None
                            
                            p = Point("workout-routes").tag("workout", slug_name)
                            p = p.field("latitude", pt.latitude).field("longitude", pt.longitude).field("elevation", pt.elevation)
                            
                            if next_pt:
                                speed = pt.speed_between(next_pt)
                                p = p.field("speed", float(speed) if speed is not None else 0.0)
                                p = p.field("distance", float(pt.distance_3d(next_pt) or 0.0))
                                
                            p = p.time(pt.time)
                            points.append(p)
                            
                            if len(points) >= 5000:
                                write_api.write(bucket=INFLUX_BUCKET, record=points)
                                points = []
            except Exception as e:
                print(f"Error parsing {route_file}: {e}")
                
    if points:
        write_api.write(bucket=INFLUX_BUCKET, record=points)
    print("Workout routes processed.")

def ingest_file(zip_path, write_api) -> bool:
    with tempfile.TemporaryDirectory() as temp_dir:
        print("Extracting export.xml and routes from zip...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            
        export_xml_path = os.path.join(temp_dir, 'apple_health_export', 'export.xml')
        if not os.path.exists(export_xml_path):
            print("export.xml not found inside the zip!")
            return False

        process_workout_routes(write_api, temp_dir)

        points = []
        count = 0
        total_records = 0
        sources = set()

        print("Parsing export.xml via iterparse...")
        context = etree.iterparse(export_xml_path, events=('end',))
        
        for event, elem in context:
            if elem.tag in ['Record', 'Workout']:
                try:
                    attribs = dict(elem.attrib)
                    sources.add(attribs.get('sourceName', 'unknown'))
                    
                    if elem.tag == 'Record':
                        recs = format_record(attribs)
                        for r in recs:
                            points.append(dict_to_point(r))
                    elif elem.tag == 'Workout':
                        rec = format_workout(attribs)
                        points.append(dict_to_point(rec))
                except Exception as e:
                    pass

                count += 1
                elem.clear()

            if len(points) >= 5000:
                write_api.write(bucket=INFLUX_BUCKET, record=points)
                total_records += len(points)
                print(f"Inserted {total_records} records...")
                points = []

        if points:
            write_api.write(bucket=INFLUX_BUCKET, record=points)
            total_records += len(points)

        print(f"Inserted {total_records} total records.")
        
        print(f"Pushing {len(sources)} sources to data-sources measurement...")
        source_points = []
        for s in sources:
            source_points.append(Point("data-sources").tag("device", s).field("value", 1))
        if source_points:
            write_api.write(bucket=INFLUX_BUCKET, record=source_points)

        print("Ingestion complete!")
        return True

def rename_processed_file(zip_path, success=True):
    dir_name = os.path.dirname(zip_path)
    base_name = "export" if success else "export_failed"
    date_str = datetime.now().strftime("%d%b%Y")
    new_name = f"{base_name}_{date_str}.zip"
    new_path = os.path.join(dir_name, new_name)
    
    counter = 1
    while os.path.exists(new_path):
        new_name = f"{base_name}_{date_str}_{counter}.zip"
        new_path = os.path.join(dir_name, new_name)
        counter += 1
        
    print(f"Renaming {zip_path} to {new_path}...")
    try:
        os.rename(zip_path, new_path)
        print("Rename complete.")
    except Exception as e:
        print(f"Error renaming file: {e}")

def main():
    print("Starting Apple Health automatic ingestion daemon...")
    print(f"Watching for {ZIP_PATH} (checking every 120 seconds)...")
    
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)

    while True:
        if os.path.exists(ZIP_PATH):
            print(f"Found {ZIP_PATH}, starting processing...")
            # Wait 5 seconds to let writing finish
            time.sleep(5)
            
            success = False
            try:
                success = ingest_file(ZIP_PATH, write_api)
            except Exception as e:
                print(f"Ingestion crashed with error: {e}")
                
            rename_processed_file(ZIP_PATH, success=success)
            print(f"Sleeping before next check... Watching for {ZIP_PATH}...")
        
        time.sleep(120)

if __name__ == "__main__":
    main()
