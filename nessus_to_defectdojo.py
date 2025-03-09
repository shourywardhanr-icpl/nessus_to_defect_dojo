#!/usr/bin/env python3
import os
import requests
import json
import argparse
import sys
from datetime import datetime

def get_api_key(defect_dojo_url, username, password):
    """Get API key from DefectDojo using credentials"""
    auth_url = f"{defect_dojo_url}/api/v2/api-token-auth/"
    data = {
        "username": username,
        "password": password
    }
    
    try:
        response = requests.post(auth_url, json=data)
        response.raise_for_status()
        return response.json().get("token")
    except requests.exceptions.RequestException as e:
        print(f"Error getting API key: {e}")
        sys.exit(1)

def get_products(defect_dojo_url, api_key):
    """Get list of products from DefectDojo"""
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.get(f"{defect_dojo_url}/api/v2/products/", headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting products: {e}")
        sys.exit(1)

def get_or_create_product(defect_dojo_url, api_key, product_name):
    """Get a product by name or create it if it doesn't exist"""
    products = get_products(defect_dojo_url, api_key)
    
    # Search for product by name
    for product in products.get("results", []):
        if product.get("name") == product_name:
            print(f"Found existing product: {product_name} (ID: {product['id']})")
            return product["id"]
    
    # If product doesn't exist, create it
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "name": product_name,
        "description": f"Automatically created for Nessus import on {datetime.now().strftime('%Y-%m-%d')}",
        "prod_type": 1  # Default product type
    }
    
    try:
        response = requests.post(f"{defect_dojo_url}/api/v2/products/", headers=headers, json=data)
        response.raise_for_status()
        product_id = response.json().get("id")
        print(f"Created new product: {product_name} (ID: {product_id})")
        return product_id
    except requests.exceptions.RequestException as e:
        print(f"Error creating product: {e}")
        sys.exit(1)

def get_or_create_engagement(defect_dojo_url, api_key, product_id, engagement_name):
    """Get an engagement by name and product ID or create it if it doesn't exist"""
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "application/json"
    }
    
    # Get engagements for this product
    try:
        response = requests.get(
            f"{defect_dojo_url}/api/v2/engagements/?product={product_id}", 
            headers=headers
        )
        response.raise_for_status()
        engagements = response.json()
        
        # Search for engagement by name
        for engagement in engagements.get("results", []):
            if engagement.get("name") == engagement_name:
                print(f"Found existing engagement: {engagement_name} (ID: {engagement['id']})")
                return engagement["id"]
    except requests.exceptions.RequestException as e:
        print(f"Error getting engagements: {e}")
        sys.exit(1)
    
    # If engagement doesn't exist, create it
    today = datetime.now().strftime("%Y-%m-%d")
    
    data = {
        "name": engagement_name,
        "product": product_id,
        "target_start": today,
        "target_end": today,
        "status": "In Progress",
        "engagement_type": "Interactive"
    }
    
    try:
        response = requests.post(f"{defect_dojo_url}/api/v2/engagements/", headers=headers, json=data)
        response.raise_for_status()
        engagement_id = response.json().get("id")
        print(f"Created new engagement: {engagement_name} (ID: {engagement_id})")
        return engagement_id
    except requests.exceptions.RequestException as e:
        print(f"Error creating engagement: {e}")
        sys.exit(1)

def import_nessus_scan(defect_dojo_url, api_key, engagement_id, scan_file_path, scan_type):
    """Import a Nessus scan file into DefectDojo"""
    headers = {
        "Authorization": f"Token {api_key}"
    }
    
    data = {
        "engagement": engagement_id,
        "scan_type": scan_type,
        "active": True,
        "verified": False,
        "close_old_findings": False,
        "skip_duplicates": True
    }
    
    files = {
        "file": open(scan_file_path, "rb")
    }
    
    try:
        response = requests.post(
            f"{defect_dojo_url}/api/v2/import-scan/", 
            headers=headers, 
            data=data, 
            files=files
        )
        response.raise_for_status()
        print(f"Successfully imported: {os.path.basename(scan_file_path)}")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error importing scan: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        return None
    finally:
        files["file"].close()

def extract_product_name_from_filename(filename):
    """Extract a product name from the Nessus filename"""
    # This is a simple example - adjust the logic based on your filename patterns
    basename = os.path.basename(filename)
    # Remove extension and use first part as product name
    parts = basename.split('_')
    if len(parts) > 1:
        return parts[0]
    return basename.split('.')[0]

def main():
    parser = argparse.ArgumentParser(description="Import Nessus scan reports into DefectDojo")
    parser.add_argument("-d", "--directory", default="/home/shoury/nessus_reports", 
                        help="Directory containing Nessus reports")
    parser.add_argument("-u", "--url", default="http://localhost:8080", 
                        help="DefectDojo URL")
    parser.add_argument("-un", "--username", required=True, 
                        help="DefectDojo username")
    parser.add_argument("-p", "--password", required=True, 
                        help="DefectDojo password")
    parser.add_argument("--product-name", 
                        help="Override product name (otherwise extracted from filenames)")
    parser.add_argument("--engagement-name", default="Nessus Automated Import", 
                        help="Engagement name to use")
    parser.add_argument("--scan-type", default="Web Application Test", 
                        help="Scan type to use for imports")
    
    args = parser.parse_args()
    
    # Verify directory exists
    if not os.path.isdir(args.directory):
        print(f"Error: Directory {args.directory} does not exist")
        sys.exit(1)
    
    # Get API key
    api_key = get_api_key(args.url, args.username, args.password)
    
    # Process each Nessus file
    nessus_files = [
        os.path.join(args.directory, f) for f in os.listdir(args.directory) 
        if f.endswith('.nessus')
    ]
    
    if not nessus_files:
        print(f"No .nessus files found in {args.directory}")
        sys.exit(1)
    
    # If product name is not specified, extract from first file
    product_name = args.product_name
    if not product_name:
        product_name = extract_product_name_from_filename(nessus_files[0])
    
    # Get or create product
    product_id = get_or_create_product(args.url, api_key, product_name)
    
    # Get or create engagement
    engagement_id = get_or_create_engagement(args.url, api_key, product_id, args.engagement_name)
    
    # Import each file
    scan_type = args.scan_type
    print(f"Using scan type: {scan_type}")
    
    for nessus_file in nessus_files:
        print(f"Importing: {nessus_file}")
        result = import_nessus_scan(args.url, api_key, engagement_id, nessus_file, scan_type)
        if result:
            print(f"Import successful! Test ID: {result.get('test', {}).get('id')}")
    
    print(f"Import complete. Imported {len(nessus_files)} files to product ID {product_id}, engagement ID {engagement_id}")

if __name__ == "__main__":
    main()
