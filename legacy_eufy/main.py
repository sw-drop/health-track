import os
import json
import time
import logging
from datetime import datetime
import requests
import schedule

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

API_BASE_URL = "https://api.eufylife.com"
CLIENT_ID = "eufy-app"
CLIENT_SECRET = "8FHf22gaTKu7MZXqz5zytw"
USER_AGENT_VERSION = "3.3.7"

EUFY_EMAIL = os.environ.get("EUFY_EMAIL")
EUFY_PASSWORD = os.environ.get("EUFY_PASSWORD")
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/data/eufy_data.json")

def login():
    login_url = f"{API_BASE_URL}/v1/user/v2/email/login"
    headers = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "User-Agent": f"EufyLife-iOS-{USER_AGENT_VERSION}",
        "Category": "Health",
        "Language": "en",
        "Timezone": "UTC",
        "Country": "US",
        "Content-Type": "application/json",
    }
    
    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "email": EUFY_EMAIL,
        "password": EUFY_PASSWORD,
    }
    
    logging.info("Attempting to login to EufyLife...")
    response = requests.post(login_url, headers=headers, json=payload)
    response.raise_for_status()
    
    data = response.json()
    if data.get("res_code") == 1:
        logging.info("Login successful.")
        return data["access_token"], data["user_id"]
    else:
        logging.error(f"Login failed: {data}")
        raise Exception(f"Login failed: {data.get('message')}")

def fetch_device_data(access_token, user_id):
    url = f"{API_BASE_URL}/v1/device/data"
    headers = {
        "Host": "api.eufylife.com",
        "Accept": "*/*",
        "Uid": str(user_id),
        "Accept-Encoding": "gzip, deflate",
        "User-Agent": f"Eufylife-iOS-{USER_AGENT_VERSION}-281",
        "Accept-Language": "en-US,en;q=0.9",
        "Token": access_token,
    }
    
    logging.info("Fetching device data...")
    all_data = []
    offset = 0
    
    while True:
        response = requests.get(f"{url}?offset={offset}", headers=headers)
        response.raise_for_status()
        
        data = response.json()
        if data.get("res_code") == 1:
            records = data.get("data", [])
            all_data.extend(records)
            page_size = data.get("page_size", 308)
            
            if len(records) < page_size or len(records) == 0:
                break
            offset += page_size
        elif isinstance(data, list):
            all_data.extend(data)
            break
        else:
            logging.error(f"Failed to fetch data: {data}")
            break
            
    logging.info(f"Fetched {len(all_data)} total records across all pages.")
    return all_data

def parse_scale_data(device_data):
    results = []
    for record in device_data:
        scale_data = record.get("scale_data", {})
        if not scale_data:
            continue
            
        update_time = record.get("update_time") or record.get("create_time")
        
        parsed = {
            "timestamp": update_time,
            "datetime": datetime.fromtimestamp(update_time).isoformat() if update_time else None,
            "customer_id": record.get("customer_id"),
        }
        
        # Convert weight from decigrams to kg
        weight_dg = scale_data.get("weight")
        if weight_dg:
            parsed["weight_kg"] = round(weight_dg / 10.0, 2)
            
        fields = ["body_fat", "muscle_mass", "bmi", "water", "bone_mass", "visceral_fat", "protein_ratio", "bmr", "body_age"]
        for f in fields:
            if f in scale_data:
                parsed[f] = scale_data[f]
                
        results.append(parsed)
        
    # Sort by timestamp descending
    results.sort(key=lambda x: x.get("timestamp", 0), reverse=True)
    return results

def job():
    if not EUFY_EMAIL or not EUFY_PASSWORD:
        logging.error("EUFY_EMAIL and EUFY_PASSWORD environment variables are required.")
        return
        
    try:
        access_token, user_id = login()
        device_data = fetch_device_data(access_token, user_id)
        parsed_data = parse_scale_data(device_data)
        
        # Save to JSON
        with open(OUTPUT_FILE, 'w') as f:
            json.dump(parsed_data, f, indent=4)
            
        logging.info(f"Successfully saved {len(parsed_data)} records to {OUTPUT_FILE}")
        
    except Exception as e:
        logging.error(f"Error during job execution: {e}")

if __name__ == "__main__":
    logging.info("Starting Eufy data export script...")
    
    # Run immediately on start
    job()
    
    # Then schedule to run every 6 hours
    schedule.every(6).hours.do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(60)
