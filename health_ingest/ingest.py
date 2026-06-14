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
                                p = p.field("speed", speed if speed else 0)
                                p = p.field("distance", pt.distance_3d(next_pt))
                                
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

def main():
    print("Starting Apple Health safe ingestion with K0rventen formatters...")
    while True:
        if os.path.exists(ZIP_PATH):
            print(f"Found {ZIP_PATH}, starting processing...")
            break
        print(f"Waiting for {ZIP_PATH}...")
        time.sleep(5)
        
    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)

    with tempfile.TemporaryDirectory() as temp_dir:
        print("Extracting export.xml and routes from zip...")
        with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
            
        export_xml_path = os.path.join(temp_dir, 'apple_health_export', 'export.xml')
        if not os.path.exists(export_xml_path):
            print("export.xml not found inside the zip!")
            return

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
                while elem.getprevious() is not None:
                    del elem.getparent()[0]

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

if __name__ == "__main__":
    main()
