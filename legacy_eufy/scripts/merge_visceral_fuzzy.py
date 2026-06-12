import json
import csv
import os
from datetime import datetime

JSON_FILE = 'data/eufy_data.json'
CSV_FILE = 'backups/weight_purchase_1780158036.csv'

def merge_visceral_fat_fuzzy():
    if not os.path.exists(JSON_FILE):
        print("JSON not found")
        return
    with open(JSON_FILE, 'r') as f:
        json_data = json.load(f)
        
    csv_records = []
    with open(CSV_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get('Family Members', '').strip().lower() == 'sharmla':
                continue
            try:
                dt = datetime.strptime(row['Time'], '%Y-%m-%d %H:%M:%S')
                ts = int(dt.timestamp())
                vf = float(row.get('VISCERAL FAT', 0)) if row.get('VISCERAL FAT') else 0.0
                wt = float(row.get('WEIGHT (kg)', 0)) if row.get('WEIGHT (kg)') else 0.0
                csv_records.append({'ts': ts, 'vf': vf, 'wt': wt})
            except Exception:
                pass

    updated = 0
    for record in json_data:
        json_ts = record.get('timestamp')
        json_wt = record.get('weight_kg', 0)
        
        # Already has visceral fat > 0? (From our previous successful match)
        if record.get('visceral_fat', 0) > 0:
            continue
            
        # Find best match
        best_match = None
        min_diff = 100000
        
        for csv_rec in csv_records:
            time_diff = abs(csv_rec['ts'] - json_ts)
            # Match if within 24 hours AND weight matches exactly (or very closely)
            if time_diff < 86400 and abs(csv_rec['wt'] - json_wt) < 0.1:
                if time_diff < min_diff:
                    min_diff = time_diff
                    best_match = csv_rec
                    
        if best_match and best_match['vf'] > 0:
            record['visceral_fat'] = best_match['vf']
            updated += 1
            
    with open(JSON_FILE, 'w') as f:
        json.dump(json_data, f, indent=4)
        
    print(f"Updated an additional {updated} records with visceral fat.")

if __name__ == '__main__':
    merge_visceral_fat_fuzzy()
