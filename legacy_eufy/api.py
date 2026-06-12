import json
import logging
import os
import time
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from threading import Lock

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

DATA_FILE = "/data/eufy_data.json"
BACKUP_FILE = "/data/eufy_data_backups.jsonl"
PIN_CODE = "2364"

# Lock to prevent race conditions during read/writes
file_lock = Lock()

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def require_pin():
    """Check if the provided PIN header matches."""
    auth_header = request.headers.get("X-PIN-Code")
    if auth_header != PIN_CODE:
        return False
    return True

def _read_data():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, 'r') as f:
            content = f.read().strip()
            if content:
                return json.loads(content)
            return []
    except Exception as e:
        logging.error(f"Error reading data: {e}")
        return []

def _write_data(data):
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logging.error(f"Error writing data: {e}")
        raise

def _append_backup(action, original_record):
    """Appends the original record to the backup jsonl file before modification."""
    try:
        with open(BACKUP_FILE, 'a') as f:
            backup_entry = {
                "action": action,
                "original_record": original_record
            }
            f.write(json.dumps(backup_entry) + "\n")
    except Exception as e:
        logging.error(f"Error writing backup: {e}")

@app.route('/api/data', methods=['GET'])
def get_data():
    with file_lock:
        data = _read_data()
    return jsonify(data), 200

@app.route('/api/data/<int:timestamp>', methods=['DELETE'])
def delete_data(timestamp):
    if not require_pin():
        return jsonify({"error": "Unauthorized"}), 401
        
    with file_lock:
        data = _read_data()
        
        # Find the record
        record_idx = None
        for i, record in enumerate(data):
            if record.get("timestamp") == timestamp:
                record_idx = i
                break
                
        if record_idx is None:
            return jsonify({"error": "Record not found"}), 404
            
        # Backup the record before deletion
        _append_backup("DELETE", data[record_idx])
        
        # Delete and save
        del data[record_idx]
        _write_data(data)
        
    return jsonify({"message": "Record deleted successfully"}), 200

@app.route('/api/data/<int:timestamp>', methods=['PUT'])
def edit_data(timestamp):
    if not require_pin():
        return jsonify({"error": "Unauthorized"}), 401
        
    update_fields = request.json
    if not update_fields:
        return jsonify({"error": "Invalid payload"}), 400
        
    with file_lock:
        data = _read_data()
        
        # Find the record
        record_idx = None
        for i, record in enumerate(data):
            if record.get("timestamp") == timestamp:
                record_idx = i
                break
                
        if record_idx is None:
            return jsonify({"error": "Record not found"}), 404
            
        # Backup the record before modification
        _append_backup("EDIT", data[record_idx])
        
        # Update fields (e.g. weight_kg)
        for key, value in update_fields.items():
            if key != "timestamp": # Don't allow changing the primary key timestamp
                data[record_idx][key] = value
                
        _write_data(data)
        
    return jsonify({"message": "Record updated successfully"}), 200

@app.route('/api/data', methods=['POST'])
def add_data():
    if not require_pin():
        return jsonify({"error": "Unauthorized"}), 401
        
    new_record = request.json
    if not new_record or "weight_kg" not in new_record:
        return jsonify({"error": "Invalid payload"}), 400
        
    if "timestamp" not in new_record:
        new_record["timestamp"] = int(time.time())
    new_record["datetime"] = datetime.fromtimestamp(new_record["timestamp"]).isoformat()
    
    with file_lock:
        data = _read_data()
        data.append(new_record)
        data.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
        _write_data(data)
        
    return jsonify({"message": "Record added", "timestamp": new_record["timestamp"]}), 201

@app.route('/api/verify', methods=['POST'])
def verify_pin():
    if not require_pin():
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"success": True}), 200

if __name__ == '__main__':
    # Run the server on port 8086. net=host will expose it directly on the DietPi host.
    app.run(host='0.0.0.0', port=8086, debug=False)
