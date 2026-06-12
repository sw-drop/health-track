import json

filepath = 'data/eufy_data.json'

with open(filepath, 'r') as f:
    data = json.load(f)

# Sort ascending by timestamp
data.sort(key=lambda x: x.get('timestamp', 0))

metrics_to_fix = ['body_fat', 'muscle_mass', 'bone_mass', 'bmi', 'water', 'visceral_fat', 'protein_ratio', 'bmr', 'body_age']
fixed_count = 0

for i, record in enumerate(data):
    if record.get('body_fat') == 0.0:
        print(f"Fixing record at timestamp {record.get('timestamp')}")
        
        for metric in metrics_to_fix:
            if metric not in record or record[metric] == 0.0:
                # Find previous valid
                prev_val = None
                for j in range(i-1, -1, -1):
                    if data[j].get(metric) and data[j].get(metric) > 0.0:
                        prev_val = data[j].get(metric)
                        break
                
                # Find next valid
                next_val = None
                for j in range(i+1, len(data)):
                    if data[j].get(metric) and data[j].get(metric) > 0.0:
                        next_val = data[j].get(metric)
                        break
                
                # Compute average
                if prev_val is not None and next_val is not None:
                    avg_val = round((prev_val + next_val) / 2.0, 1)
                    record[metric] = avg_val
                elif prev_val is not None:
                    record[metric] = prev_val
                elif next_val is not None:
                    record[metric] = next_val
                    
        fixed_count += 1

# Sort descending back to original format
data.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

with open(filepath, 'w') as f:
    json.dump(data, f, indent=4)

print(f"Fixed {fixed_count} records.")
