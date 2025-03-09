import requests
import json
import time
import os
import urllib3

# Suppress SSL warnings (optional, not recommended for production)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Nessus API credentials
NESSUS_URL = "https://localhost:8834"
ACCESS_KEY = "694e6aad410518919ce9d4b6fc491b4eb2bc6507888ffcbf659e417e9dbaa8a8" 
SECRET_KEY = "d0f6ed5ff2b60d13cb48d6f8e0851bd8540a9ad7fab85b7ad1fd841ac5a2860f"
SAVE_PATH = "./nessus_reports/"  # Directory to store reports

# Create save directory if not exists
if not os.path.exists(SAVE_PATH):
    os.makedirs(SAVE_PATH)

# Headers for authentication
HEADERS = {
    "X-ApiKeys": f"accessKey={ACCESS_KEY}; secretKey={SECRET_KEY}",
    "Content-Type": "application/json",
}

def get_scans():
    """Fetch list of all available scans."""
    url = f"{NESSUS_URL}/scans"
    response = requests.get(url, headers=HEADERS, verify=False)
    
    if response.status_code == 200:
        scans = response.json().get("scans", [])
        return scans
    else:
        print("Error fetching scans:", response.text)
        return []

def download_scan(scan_id, scan_name):
    """Download scan report in Nessus format."""
    export_url = f"{NESSUS_URL}/scans/{scan_id}/export"
    data = {"format": "nessus"}  # Changed from 'json' to 'nessus'
    
    export_response = requests.post(export_url, headers=HEADERS, json=data, verify=False)
    
    if export_response.status_code == 200:
        file_id = export_response.json().get("file")
        print(f"Export initiated for {scan_name} (Scan ID: {scan_id}), File ID: {file_id}")
        
        # Wait for file to be ready
        while True:
            status_url = f"{NESSUS_URL}/scans/{scan_id}/export/{file_id}/status"
            status_response = requests.get(status_url, headers=HEADERS, verify=False)
            if status_response.json().get("status") == "ready":
                break
            time.sleep(2)

        # Download the scan result
        download_url = f"{NESSUS_URL}/scans/{scan_id}/export/{file_id}/download"
        result_response = requests.get(download_url, headers=HEADERS, verify=False)

        if result_response.status_code == 200:
            file_path = os.path.join(SAVE_PATH, f"{scan_name.replace(' ', '_')}.nessus")
            with open(file_path, "wb") as file:
                file.write(result_response.content)
            print(f"Scan {scan_name} saved as {file_path}")
        else:
            print(f"Error downloading scan {scan_name}: {result_response.text}")
    else:
        print(f"Error exporting scan {scan_name}: {export_response.text}")

def main():
    """Main function to fetch and save Nessus scans."""
    print("Fetching available scans...")
    scans = get_scans()
    
    if not scans:
        print("No scans found.")
        return
    
    for scan in scans:
        download_scan(scan["id"], scan["name"])

if __name__ == "__main__":
    main()

