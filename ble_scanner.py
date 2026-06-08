import asyncio
import logging
import json
import os
import time
from datetime import datetime
from bleak import BleakScanner
from eufylife_ble_client.client import EufyLifeBLEDevice

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/data/eufy_data.json")
EUFY_MAC_PREFIXES = ["C0:E4", "88:0F", "D4:2F", "C8:47"] # common prefixes, but we can also match by name

def append_to_json(weight_kg, final=False):
    # Only save final stabilized weight readings
    if not final:
        return
        
    logging.info(f"Received FINAL weight reading: {weight_kg} kg")
    
    # Load existing data
    data = []
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r') as f:
                data = json.load(f)
        except Exception as e:
            logging.error(f"Error loading {OUTPUT_FILE}: {e}")
            
    # Check if we already added a reading in the last 60 seconds to avoid duplicates
    now = int(time.time())
    if data and data[0].get("timestamp"):
        if now - data[0].get("timestamp") < 60:
            logging.info("Duplicate reading within 60s, skipping.")
            return

    new_record = {
        "timestamp": now,
        "datetime": datetime.fromtimestamp(now).isoformat(),
        "customer_id": "ble-proxy",
        "weight_kg": weight_kg
    }
    
    # Insert at top (newest first)
    data.insert(0, new_record)
    
    try:
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        logging.info("Successfully saved new reading to dashboard JSON!")
    except Exception as e:
        logging.error(f"Error saving to {OUTPUT_FILE}: {e}")

import json
import datetime

def state_updated_callback(state):
    if state is None:
        return
        
    logging.info(f"Scale update: weight {state.weight_kg} kg (Final: {state.final_weight_kg})")
    
    if state.final_weight_kg:
        logging.info(f"Final weight recorded: {state.final_weight_kg} kg")
        # Write to JSON
        try:
            data_file = "/data/eufy_data.json"
            history = []
            try:
                with open(data_file, 'r') as f:
                    content = f.read().strip()
                    if content:
                        history = json.loads(content)
            except (FileNotFoundError, json.JSONDecodeError):
                pass
                
            # Create a new entry
            import time
            new_entry = {
                "timestamp": int(time.time()),
                "weight_kg": state.final_weight_kg,
            }
            if state.heart_rate:
                new_entry["heart_rate"] = state.heart_rate
            
            # Check if this exact timestamp already exists (prevent duplicates within 1 min)
            is_dup = False
            if history:
                last_entry = history[-1]
                if "timestamp" in last_entry:
                    if int(time.time()) - last_entry["timestamp"] < 60:
                        is_dup = True
            
            if not is_dup:
                history.append(new_entry)
                with open(data_file, 'w') as f:
                    json.dump(history, f, indent=4)
                logging.info(f"Appended new weigh-in to {data_file}")
            else:
                logging.info("Duplicate weigh-in ignored.")
        except Exception as e:
            logging.error(f"Error saving data: {e}")

weigh_in_lock = asyncio.Lock()

async def scan_loop():
    logging.info("Starting TRUE continuous passive BLE Scanner on hci1...")
    
    discovery_queue = asyncio.Queue()

    def detection_callback(device, adv_data):
        name = device.name or adv_data.local_name or ""
        
        # Temporary debug: log all signals to see what's broadcasting
        if device.rssi > -100:
            logging.info(f"[DEBUG SCAN] {device.address} ({name}) RSSI: {device.rssi}")
            
        if "eufy" in name.lower() or "smart scale" in name.lower() or device.address.startswith("BC:0F:B7"):
            logging.info(f"Raw Eufy Packet Received: {device.address} RSSI: {device.rssi} dBm | Name: {name}")
            
            # Prevent connection stealing from a distance!
            # If the scale is too far away to reliably hold a connection, ignore it completely
            # so the user's phone can connect without interference.
            if device.rssi < -80:
                logging.info(f"Ignoring weak signal ({device.rssi} dBm). Leaving scale free for phone app.")
                return
                
            if not weigh_in_lock.locked():
                try:
                    discovery_queue.put_nowait((device, adv_data))
                except asyncio.QueueFull:
                    pass

    scanner = BleakScanner(detection_callback, adapter="hci1", scanning_mode="active")
    
    # Run the scanner
    asyncio.create_task(scanner.start())
    logging.info("Scanner started successfully on hci1. Listening indefinitely...")
    
    while True:
        try:
            device, adv_data = await discovery_queue.get()
            async with weigh_in_lock:
                name = device.name or adv_data.local_name or "eufy T9120"
                model = name.strip()
                from eufylife_ble_client.client import MODELS
                if model not in MODELS:
                    for k in MODELS.keys():
                        if k in model or model in k:
                            model = k
                            break
                
                logging.info(f"Connecting to {model} [{device.address}] to read weight...")
                eufy_device = EufyLifeBLEDevice(model)
                eufy_device.register_callback(state_updated_callback)
                eufy_device.set_ble_device_and_advertisement_data(device, adv_data)
                
                try:
                    await eufy_device.connect()
                except Exception as e:
                    if "Characteristic with UUID None" in str(e):
                        logging.info("Scale connected! (Ignored missing battery characteristic). Waiting 15s for weight...")
                    else:
                        raise e
                        
                # We are connected, the scale will now stream GATT notifications
                await asyncio.sleep(15)
                try:
                    await eufy_device.disconnect()
                except:
                    pass
                logging.info("Disconnecting. Waiting for next weigh-in...")
                
        except Exception as e:
            logging.error(f"Error during weigh-in connection: {e}")
            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(scan_loop())
