import os
import zipfile
import tempfile
import sys
from xml.etree.ElementTree import iterparse
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

INFLUX_URL = os.getenv("INFLUX_URL", "http://health_influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "my-super-secret-auth-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "my-org")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "health")

ZIP_FILE = "/data/export.zip"

def main():
    if not os.path.exists(ZIP_FILE):
        print(f"Error: {ZIP_FILE} not found. Please ensure it is mounted.")
        sys.exit(1)

    client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = client.write_api(write_options=SYNCHRONOUS)

    print("Extracting export.xml from zip...")
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(ZIP_FILE, 'r') as zip_ref:
            
            # The Apple Health export zip contains a directory 'apple_health_export'
            # Let's extract everything or find the exact file name.
            # We'll look for export.xml in the namelist
            export_xml_path_in_zip = None
            for name in zip_ref.namelist():
                if name.endswith("export.xml"):
                    export_xml_path_in_zip = name
                    break
            
            if not export_xml_path_in_zip:
                print("Error: Could not find export.xml inside the zip file.")
                sys.exit(1)

            print(f"Found {export_xml_path_in_zip}. Extracting...")
            zip_ref.extract(export_xml_path_in_zip, temp_dir)
            xml_path = os.path.join(temp_dir, export_xml_path_in_zip)
            
            print("Starting XML parsing...")
            count = 0
            points = []
            
            # Using iterparse to keep memory low
            for event, elem in iterparse(xml_path, events=('end',)):
                if elem.tag == 'Record':
                    try:
                        record_type = elem.get('type', '').replace('HKQuantityTypeIdentifier', '').replace('HKCategoryTypeIdentifier', '')
                        source = elem.get('sourceName', 'Unknown')
                        start_date = elem.get('startDate')
                        value_str = elem.get('value')
                        unit = elem.get('unit', '')

                        if not value_str or not start_date or not record_type:
                            elem.clear()
                            continue

                        try:
                            val = float(value_str)
                        except ValueError:
                            end_date = elem.get('endDate')
                            if start_date and end_date:
                                try:
                                    from datetime import datetime
                                    # Apple Health format: "2020-11-20 07:11:00 +0100"
                                    fmt = "%Y-%m-%d %H:%M:%S %z"
                                    start_dt = datetime.strptime(start_date, fmt)
                                    end_dt = datetime.strptime(end_date, fmt)
                                    val = (end_dt - start_dt).total_seconds() / 60.0
                                    unit = "min"
                                    
                                    # Differentiate states (e.g., SleepAnalysisAsleep vs SleepAnalysisInBed)
                                    clean_val = value_str.replace('HKCategoryValue', '').replace(record_type, '')
                                    if clean_val:
                                        record_type = f"{record_type}_{clean_val}"
                                except Exception:
                                    elem.clear()
                                    continue
                            else:
                                elem.clear()
                                continue
                            
                        point = Point("health_record") \
                            .tag("type", record_type) \
                            .tag("source", source) \
                            .tag("unit", unit) \
                            .field("value", val) \
                            .time(start_date)

                        points.append(point)
                        count += 1
                        
                        if len(points) >= 5000:
                            write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)
                            print(f"Inserted {count} records...")
                            points = []
                    except Exception as e:
                        print(f"Error processing record: {e}")
                    
                    # FREE MEMORY
                    elem.clear()
            
            # Write any remaining points
            if points:
                write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=points)
                print(f"Inserted {count} total records.")
                
    print("Ingestion complete!")

if __name__ == "__main__":
    main()
