import csv
import json
import os
from datetime import datetime

CSV_FILE = 'weight_purchase_1780158036.csv'
JSON_FILE = 'eufy_data.json'

def convert_csv_to_json():
    if not os.path.exists(CSV_FILE):
        print(f"Error: {CSV_FILE} not found.")
        return

    data = []
    with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Ignore user Sharmla as requested
            if row.get('Family Members', '').strip().lower() == 'sharmla':
                continue
                
            try:
                dt = datetime.strptime(row['Time'], '%Y-%m-%d %H:%M:%S')
                timestamp = int(dt.timestamp())
                
                # Extract values, default to 0 if missing
                weight = float(row['WEIGHT (kg)']) if row.get('WEIGHT (kg)') else 0.0
                body_fat = float(row['BODY FAT %']) if row.get('BODY FAT %') else 0.0
                muscle_mass = float(row['MUSCLE MASS (kg)']) if row.get('MUSCLE MASS (kg)') else 0.0
                water = float(row['WATER']) if row.get('WATER') else 0.0
                bone_mass = float(row['BONE MASS (kg)']) if row.get('BONE MASS (kg)') else 0.0
                
                data.append({
                    "timestamp": timestamp,
                    "weight_kg": weight,
                    "body_fat": body_fat,
                    "muscle_mass": muscle_mass,
                    "water": water,
                    "bone_mass": bone_mass
                })
            except Exception as e:
                print(f"Error parsing row: {row}. Error: {e}")

    # Sort data oldest to newest (the API returns oldest first, and frontend expects it)
    data.sort(key=lambda x: x['timestamp'])

    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

    print(f"Successfully converted {len(data)} records to {JSON_FILE}")

if __name__ == '__main__':
    convert_csv_to_json()
