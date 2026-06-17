import sys
import tokens as tk
import requests
import uuid

def test_endpoint(url, method="GET", json_data=None):
    print(f"Testing {url} with {method}")
    token = tk.manage_token_consultoria()
    headers = {
        "x-id-partner-request": str(uuid.uuid4()),
        "access_token": token,
        "accept": "*/*",
    }
    
    if method == "POST":
        if json_data is None:
            json_data = {}
        res = requests.post(url, headers=headers, json=json_data)
    else:
        res = requests.get(url, headers=headers)
        
    print(f"Status Code: {res.status_code}")
    print(f"Response: {res.text}")
    print("-" * 40)

if __name__ == "__main__":
    print("1. Performance Account")
    test_endpoint("https://api.btgpactual.com/iaas-profitability/api/v1/performance-report/account", "POST")
    print("2. Monthly Movements")
    test_endpoint("https://api.btgpactual.com/api-rm-reports/api/v1/operation-history/monthly", "GET")
    print("3. Daily Profitability by Product")
    test_endpoint("https://api.btgpactual.com/iaas-profitability/api/v1/profitability/daily/product", "POST")
