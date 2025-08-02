#!/usr/bin/env python3
"""
BigchainDB Setup and Test Script for FuseVault Comparison
"""

import subprocess
import time
import requests
import json
from pathlib import Path

def setup_bigchaindb():
    """Set up BigchainDB using Docker for testing"""
    
    print("Setting up BigchainDB for comparison testing...")
    print("=" * 50)
    
    # Create BigchainDB directory
    bdb_dir = Path("bigchaindb_test")
    bdb_dir.mkdir(exist_ok=True)
    
    print("1. Creating docker-compose.yml for BigchainDB...")
    
    # Create docker-compose file for BigchainDB
    docker_compose_content = """
version: '3.7'

services:
  bigchaindb:
    image: bigchaindb/bigchaindb:all-in-one
    container_name: bigchaindb_test
    ports:
      - "59984:9984"  # BigchainDB API port
      - "58080:8080"  # BigchainDB WebSocket port
    environment:
      BIGCHAINDB_DATABASE_BACKEND: localmongodb
      BIGCHAINDB_DATABASE_HOST: mongodb
      BIGCHAINDB_DATABASE_PORT: 27017
      BIGCHAINDB_DATABASE_NAME: bigchaindb
      BIGCHAINDB_SERVER_BIND: 0.0.0.0:9984
      BIGCHAINDB_WSSERVER_HOST: 0.0.0.0
      BIGCHAINDB_WSSERVER_PORT: 8080
    depends_on:
      - mongodb
      - tendermint
    volumes:
      - ./bigchaindb_data:/data
    command: bigchaindb start

  mongodb:
    image: mongo:4.4
    container_name: bigchaindb_mongodb
    ports:
      - "27018:27017"  # Different port to avoid conflicts
    volumes:
      - ./mongodb_data:/data/db
    command: mongod --replSet=bigchain-rs

  tendermint:
    image: tendermint/tendermint:v0.31.12
    container_name: bigchaindb_tendermint
    ports:
      - "26656:26656"
      - "26657:26657"
    volumes:
      - ./tendermint_data:/tendermint
    command: |
      sh -c "
        if [ ! -f /tendermint/config/genesis.json ]; then
          tendermint init
        fi
        tendermint node --consensus.create_empty_blocks=false
      "
"""
    
    compose_file = bdb_dir / "docker-compose.yml"
    with open(compose_file, 'w') as f:
        f.write(docker_compose_content.strip())
    
    print("2. Starting BigchainDB services...")
    print("   This may take a few minutes...")
    
    try:
        # Start services
        result = subprocess.run([
            'docker', 'compose', 'up', '-d'
        ], cwd=bdb_dir, capture_output=True, text=True, timeout=120)
        
        if result.returncode != 0:
            print(f"Error starting services: {result.stderr}")
            return False
        
        print("3. Waiting for BigchainDB to be ready...")
        
        # Wait for BigchainDB to be ready
        max_retries = 30
        for i in range(max_retries):
            try:
                response = requests.get('http://localhost:59984/', timeout=5)
                if response.status_code == 200:
                    print("✓ BigchainDB is ready!")
                    print(f"  Available at: http://localhost:59984/")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            print(f"  Waiting... ({i+1}/{max_retries})")
            time.sleep(10)
        
        print("X BigchainDB failed to start within timeout")
        return False
        
    except subprocess.TimeoutExpired:
        print("X Docker compose timed out")
        return False
    except Exception as e:
        print(f"X Error: {e}")
        return False

def test_bigchaindb_connection():
    """Test if BigchainDB is working"""
    
    print("\n" + "=" * 50)
    print("Testing BigchainDB Connection")
    print("=" * 50)
    
    try:
        # Test root endpoint
        response = requests.get('http://localhost:59984/', timeout=10)
        print(f"Root endpoint: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Version: {data.get('software', 'unknown')}")
            print(f"Public Key: {data.get('public_key', 'unknown')[:20]}...")
            return True
        else:
            print(f"Error: HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"Connection error: {e}")
        return False

def install_bigchaindb_driver():
    """Install BigchainDB Python driver"""
    
    print("\n" + "=" * 50)
    print("Installing BigchainDB Python Driver")
    print("=" * 50)
    
    try:
        result = subprocess.run([
            'pip', 'install', 'bigchaindb-driver'
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✓ BigchainDB driver installed successfully")
            return True
        else:
            print(f"X Installation failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"X Error installing driver: {e}")
        return False

def stop_bigchaindb():
    """Stop BigchainDB services"""
    
    print("\nStopping BigchainDB services...")
    bdb_dir = Path("bigchaindb_test")
    compose_file = bdb_dir / "docker-compose.yml"
    
    if compose_file.exists():
        try:
            subprocess.run([
                'docker', 'compose', 'down'
            ], cwd=bdb_dir, timeout=30)
            print("✓ BigchainDB services stopped")
        except Exception as e:
            print(f"Error stopping services: {e}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='BigchainDB Setup for FuseVault Comparison')
    parser.add_argument('--setup', action='store_true', help='Set up BigchainDB')
    parser.add_argument('--test', action='store_true', help='Test BigchainDB connection')
    parser.add_argument('--install-driver', action='store_true', help='Install BigchainDB Python driver')
    parser.add_argument('--stop', action='store_true', help='Stop BigchainDB services')
    
    args = parser.parse_args()
    
    if args.setup:
        success = setup_bigchaindb()
        if success:
            print("\nBigchainDB setup complete!")
            print("Next steps:")
            print("1. Run: python setup_bigchaindb.py --install-driver")
            print("2. Run: python setup_bigchaindb.py --test")
            print("3. Run benchmark comparison tests")
        else:
            print("\nBigchainDB setup failed")
    
    elif args.test:
        if test_bigchaindb_connection():
            print("\nBigchainDB is ready for testing!")
        else:
            print("\nBigchainDB connection failed")
    
    elif args.install_driver:
        install_bigchaindb_driver()
    
    elif args.stop:
        stop_bigchaindb()
    
    else:
        print("BigchainDB Setup Script")
        print("Usage:")
        print("  python setup_bigchaindb.py --setup          # Set up BigchainDB")
        print("  python setup_bigchaindb.py --install-driver # Install Python driver")
        print("  python setup_bigchaindb.py --test           # Test connection")
        print("  python setup_bigchaindb.py --stop           # Stop services")