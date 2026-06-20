#!/usr/bin/env python3
"""
Debug script to test login token issue
"""

import sys
sys.path.insert(0, '/opt/tcm-ai')

import json
import requests
from pprint import pprint

def test_login():
    """Test the login endpoint"""
    url = "http://localhost:8000/api/auth/login"
    data = {
        "username": "doctor",
        "password": "doctor123"
    }
    
    print("Sending login request...")
    response = requests.post(url, json=data)
    print(f"Status code: {response.status_code}")
    print("Headers:")
    pprint(dict(response.headers))
    print("\nResponse JSON:")
    if response.headers.get('content-type', '').startswith('application/json'):
        pprint(response.json())
    else:
        print(response.text)
    
    # Check for session cookie
    print("\nCookies:")
    for cookie in response.cookies:
        print(f"  {cookie.name}: {cookie.value}")

if __name__ == "__main__":
    test_login()