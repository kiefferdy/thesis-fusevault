#!/usr/bin/env python3
"""
Diagnostic tool for backend connectivity issues.
This script helps troubleshoot connections between frontend and backend.
"""

import os
import sys
import socket
import time
import json
import http.client
import urllib.parse
from contextlib import closing

# Define colors for output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

def success(msg):
    print(f"{GREEN}✓ {msg}{RESET}")

def warning(msg):
    print(f"{YELLOW}⚠ {msg}{RESET}")

def error(msg):
    print(f"{RED}✗ {msg}{RESET}")

def info(msg):
    print(f"{BOLD}{msg}{RESET}")

def check_port_available(host, port):
    """Check if a port is open on the host."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(1)
        result = sock.connect_ex((host, port))
        return result == 0

def make_http_request(host, port, path, method="GET"):
    """Make an HTTP request and return response details."""
    conn = http.client.HTTPConnection(host, port, timeout=5)
    try:
        conn.request(method, path)
        response = conn.getresponse()
        data = response.read().decode('utf-8')
        headers = dict(response.getheaders())
        return {
            "status": response.status,
            "reason": response.reason,
            "data": data,
            "headers": headers
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        conn.close()

def check_cors_headers(headers):
    """Check if CORS headers are properly set."""
    cors_headers = {
        "Access-Control-Allow-Origin": headers.get("Access-Control-Allow-Origin"),
        "Access-Control-Allow-Credentials": headers.get("Access-Control-Allow-Credentials"),
        "Access-Control-Allow-Methods": headers.get("Access-Control-Allow-Methods"),
        "Access-Control-Allow-Headers": headers.get("Access-Control-Allow-Headers")
    }
    
    if not cors_headers["Access-Control-Allow-Origin"]:
        error("CORS headers not found. This will cause browser issues.")
        return False
    
    origins = cors_headers["Access-Control-Allow-Origin"].split(",")
    origins = [o.strip() for o in origins]
    
    if "*" in origins:
        warning("CORS is set to allow all origins (*). This is not recommended for production.")
    elif "http://localhost:5173" not in origins and "http://127.0.0.1:5173" not in origins:
        warning(f"CORS may not allow Vite dev server (localhost:5173). Current allowed origins: {origins}")
    
    if cors_headers["Access-Control-Allow-Credentials"] != "true":
        error("CORS does not allow credentials. Session cookies won't work.")
        return False
    
    success("CORS headers look properly configured")
    return True

def diagnose_backend(host="localhost", port=8000):
    """Run diagnostics on the backend server."""
    print(f"\n{BOLD}Running Backend Diagnostics{RESET}\n")
    
    # Check if the server is running
    info("Checking if server is running...")
    if not check_port_available(host, port):
        error(f"Backend server is not running on {host}:{port}")
        return False
    success(f"Backend server is running on {host}:{port}")
    
    # Make a request to the nonce endpoint
    info("\nTesting nonce endpoint...")
    nonce_response = make_http_request(host, port, "/auth/nonce/0x0000000000000000000000000000000000000000")
    
    if "error" in nonce_response:
        error(f"Failed to connect to nonce endpoint: {nonce_response['error']}")
        return False
    
    if nonce_response["status"] != 200:
        error(f"Nonce endpoint returned status {nonce_response['status']}: {nonce_response['reason']}")
        print(f"Response: {nonce_response['data']}")
        return False
    
    success(f"Nonce endpoint returned status {nonce_response['status']}: {nonce_response['reason']}")
    try:
        nonce_data = json.loads(nonce_response["data"])
        print(f"Nonce data: {json.dumps(nonce_data, indent=2)}")
    except:
        warning(f"Could not parse nonce response as JSON: {nonce_response['data']}")
    
    # Check CORS headers
    info("\nChecking CORS headers...")
    options_response = make_http_request(host, port, "/auth/nonce/0x0000000000000000000000000000000000000000", method="OPTIONS")
    
    if "error" in options_response:
        error(f"Failed to test CORS headers: {options_response['error']}")
    elif options_response["status"] >= 400:
        error(f"OPTIONS request failed with status {options_response['status']}")
        print(f"Response: {options_response['data']}")
    else:
        check_cors_headers(options_response["headers"])
    
    print("\n" + "-" * 50)
    info("Diagnostic Summary")
    print("-" * 50)
    print(f"Backend is running on: {host}:{port}")
    print(f"API is responding: {'Yes' if nonce_response.get('status') == 200 else 'No'}")
    
    frontend_urls = [
        "http://localhost:5173",  # Vite dev
        "http://localhost:3000",  # React dev
    ]
    print(f"\nTry accessing your API from the browser at: {host}:{port}/auth/nonce/0x0000000000000000000000000000000000000000")
    print("\nEnvironment variables to set in frontend .env:")
    for url in frontend_urls:
        print(f"VITE_API_URL={url.replace('localhost', host)}")
    
    return True

if __name__ == "__main__":
    diagnose_backend()