import os
import requests
import time

API_BASE_URL = "https://api.eufylife.com"

def debug():
    login_url = f"{API_BASE_URL}/v1/user/v2/email/login"
    headers = {
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "User-Agent": "EufyLife-iOS-3.3.7",
        "Category": "Health",
        "Language": "en",
        "Timezone": "UTC",
        "Country": "US",
        "Content-Type": "application/json"
    }
    payload = {
        "client_id": "eufy-app",
        "client_secret": "8FHf22gaTKu7MZXqz5zytw",
        "email": os.environ.get("EUFY_EMAIL"),
        "password": os.environ.get("EUFY_PASSWORD")
    }
    
    resp = requests.post(login_url, headers=headers, json=payload).json()
    token = resp["access_token"]
    user_id = resp["user_id"]
    
    headers = {
        "Host": "api.eufylife.com",
        "Accept": "*/*",
        "Uid": str(user_id),
        "User-Agent": "Eufylife-iOS-3.3.7-281",
        "Token": token
    }
    
    now = int(time.time())
    start = 1773382200 # March 13 2026
    
    print("Testing API parameters...")
    
    d1 = requests.get(f"{API_BASE_URL}/v1/device/data?start_time={start}&end_time={now}", headers=headers).json()
    print("start_time/end_time data:", len(d1.get("data", [])))
    
    d2 = requests.get(f"{API_BASE_URL}/v1/device/data?limit=1000", headers=headers).json()
    print("limit=1000 data:", len(d2.get("data", [])))
    
    d3 = requests.get(f"{API_BASE_URL}/v1/device/data?page=2", headers=headers).json()
    print("page=2 data:", len(d3.get("data", [])))
    
    d4 = requests.get(f"{API_BASE_URL}/v1/device/data?page_index=2", headers=headers).json()
    print("page_index=2 data:", len(d4.get("data", [])))

debug()
