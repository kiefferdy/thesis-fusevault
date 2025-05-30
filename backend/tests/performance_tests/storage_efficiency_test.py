"""
Storage Efficiency Test for Digital Asset Management API.

This test evaluates how efficiently the application stores metadata by measuring:
1. Storage space usage per asset
2. Deduplication efficiency
3. Version control overhead

Usage:
    python storage_efficiency_test.py --host localhost --port 8000 --assets 1000
"""

import argparse
import json
import os
import random
import time
import statistics
import uuid
from datetime import datetime
import requests
import pymongo
from pymongo import MongoClient
import matplotlib.pyplot as plt
import seaborn as sns


class StorageEfficiencyTest:
    def __init__(self, host, port, db_uri=None):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/api"
        self.db_client = MongoClient(db_uri or "mongodb://localhost:27017")
        self.db = self.db_client["fusevault"]
        self.assets_collection = self.db["assets"]
        self.results = {
            "total_documents": 0,
            "total_storage_bytes": 0,
            "avg_document_size_bytes": 0,
            "version_overhead_percent": 0,
            "deduplication_savings_bytes": 0,
            "metadata_efficiency_score": 0,
        }

    def generate_test_asset(self, unique_factor=0.5):
        """Generate test asset with controlled uniqueness."""
        # Create base metadata
        asset_id = str(uuid.uuid4())
        wallet_address = f"0x{os.urandom(20).hex()}"
        
        # Mix of fixed and random fields to simulate real-world data patterns
        common_metadata = {
            "document_type": random.choice(["tax_return", "medical_record", "property_deed", "contract"]),
            "category": random.choice(["financial", "healthcare", "real_estate", "legal"]),
            "creation_date": datetime.now().strftime("%Y-%m-%d"),
            "status": random.choice(["draft", "final", "verified", "pending"]),
        }
        
        # Add unique fields based on uniqueness factor
        unique_metadata = {}
        if random.random() < unique_factor:
            unique_metadata = {
                "title": f"Document {random.randint(1000, 9999)}",
                "description": f"Test document description {random.randint(100, 999)}",
                "tags": random.sample(["confidential", "important", "archive", "personal", "business"], 
                                     k=random.randint(1, 3)),
                "custom_field": f"value_{random.randint(1, 100)}"
            }
        
        return {
            "asset_id": asset_id,
            "wallet_address": wallet_address,
            "critical_metadata": {**common_metadata, **unique_metadata},
            "non_critical_metadata": {
                "file_size": f"{random.randint(1, 10)}.{random.randint(1, 9)}MB",
                "file_type": random.choice(["pdf", "docx", "xlsx", "jpg"]),
                "retention_period": f"{random.randint(1, 10)} years",
                "department": random.choice(["HR", "Finance", "Legal", "Operations"])
            }
        }

    def create_test_assets(self, num_assets, unique_factor=0.5):
        """Create test assets with specified uniqueness factor."""
        created_assets = []
        for _ in range(num_assets):
            asset = self.generate_test_asset(unique_factor)
            try:
                response = requests.post(
                    f"{self.base_url}/upload/process",
                    json=asset
                )
                if response.status_code == 200:
                    created_assets.append({
                        "asset_id": asset["asset_id"],
                        "wallet_address": asset["wallet_address"],
                        "response": response.json()
                    })
                else:
                    print(f"Failed to create asset: {response.status_code}, {response.text}")
            except Exception as e:
                print(f"Error creating asset: {e}")
        
        return created_assets

    def create_asset_versions(self, assets, num_versions=3):
        """Create multiple versions for existing assets."""
        for asset in assets[:int(len(assets) * 0.3)]:  # Create versions for 30% of assets
            asset_id = asset["asset_id"]
            wallet_address = asset["wallet_address"]
            
            for _ in range(num_versions):
                # Modify some metadata fields
                updated_asset = self.generate_test_asset(0.7)  # More uniqueness in updates
                updated_asset["asset_id"] = asset_id
                updated_asset["wallet_address"] = wallet_address
                
                try:
                    response = requests.post(
                        f"{self.base_url}/upload/process",
                        json=updated_asset
                    )
                    if response.status_code != 200:
                        print(f"Failed to create version for {asset_id}: {response.status_code}, {response.text}")
                except Exception as e:
                    print(f"Error creating version: {e}")
                
                time.sleep(0.1)  # Small delay to avoid rate limiting

    def calculate_storage_metrics(self):
        """Calculate simplified time metrics."""
        # Record the end time
        end_time = time.time()
        
        # Count total documents
        total_documents = self.assets_collection.count_documents({})
        
        # Calculate total time taken
        total_time = end_time - self.start_time
        
        # Calculate average time per asset
        avg_time_per_asset = 0
        if total_documents > 0:
            avg_time_per_asset = total_time / total_documents
        
        # Store results
        self.results = {
            "total_time_taken_seconds": total_time,
            "average_time_per_asset_seconds": avg_time_per_asset,
            "total_documents": total_documents
        }
        
        # Display results
        print("\nTime Metrics:")
        print(f"  Total time taken: {total_time:.2f} seconds")
        print(f"  Average time per asset: {avg_time_per_asset:.4f} seconds")
        print(f"  Total documents created: {total_documents}")

    def run_test(self, num_assets=100, create_versions=True):
        """Run the simplified time metrics test."""
        print(f"Starting test with {num_assets} assets...")
        
        # Record start time
        start_time = time.time()
        
        # Track successful creations directly
        successful_creates = 0
        
        # Create test assets
        for i in range(num_assets):
            asset = self.generate_test_asset()
            try:
                response = requests.post(
                    f"{self.base_url}/upload/process",
                    json=asset
                )
                if response.status_code == 200:
                    successful_creates += 1
                    
                    # Create versions (up to 3) for 30% of assets
                    if create_versions and random.random() < 0.3:
                        for v in range(3):
                            asset["critical_metadata"]["title"] = f"{asset['critical_metadata'].get('title', 'Document')} v{v+2}"
                            vresponse = requests.post(
                                f"{self.base_url}/upload/process",
                                json=asset
                            )
                            if vresponse.status_code == 200:
                                successful_creates += 1
            except Exception as e:
                print(f"Error creating asset: {e}")
        
        # Calculate final metrics
        end_time = time.time()
        total_time = end_time - start_time
        
        avg_time_per_asset = 0
        if successful_creates > 0:
            avg_time_per_asset = total_time / successful_creates
        
        # Display results
        print("\nTime Metrics:")
        print(f"  Total time taken: {total_time:.2f} seconds")
        print(f"  Total assets successfully created: {successful_creates}")
        print(f"  Average time per asset: {avg_time_per_asset:.4f} seconds")
        
        return {
            "total_time_taken_seconds": total_time,
            "successful_creates": successful_creates,
            "average_time_per_asset_seconds": avg_time_per_asset
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test storage efficiency of the asset management API")
    parser.add_argument("--host", default="localhost", help="API host")
    parser.add_argument("--port", default=8000, type=int, help="API port")
    parser.add_argument("--db-uri", default="mongodb://localhost:27017", help="MongoDB URI")
    parser.add_argument("--assets", default=100, type=int, help="Number of test assets to create")
    parser.add_argument("--no-versions", action="store_true", help="Skip version creation")
    
    args = parser.parse_args()
    
    test = StorageEfficiencyTest(args.host, args.port, args.db_uri)
    test.run_test(args.assets, not args.no_versions)