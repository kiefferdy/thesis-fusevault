"""
Integrity Verification and Recovery Performance Test

This script tests the system's ability to detect metadata tampering and the performance
of recovery mechanisms. It performs the following:

1. Creates test assets with known metadata
2. Directly modifies metadata in MongoDB to simulate tampering
3. Measures the system's ability to detect tampering via the API
4. Evaluates recovery performance when tampering is detected

Usage:
    python integrity_recovery_test.py [--assets 5] [--tampering-types all]
"""

# NOT YET WORKING RECOVERY FAILS

import argparse
import json
import os
import random
import statistics
import time
import uuid
from datetime import datetime
import pymongo
import requests
from pymongo import MongoClient
from dotenv import load_dotenv
import matplotlib.pyplot as plt
import pandas as pd


class IntegrityRecoveryTest:
    def __init__(self):
        # Load environment variables
        load_dotenv()
        
        # Get connection details from .env
        self.mongodb_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        self.db_name = os.getenv("MONGO_DB_NAME", "fusevault")
        self.api_host = os.getenv("API_HOST", "localhost")
        self.api_port = os.getenv("API_PORT", "8000")
        
        # Set up API base URL
        self.base_url = f"http://{self.api_host}:{self.api_port}/api"
        
        # Connect to MongoDB
        print(f"Connecting to MongoDB: {self.mongodb_uri.split('@')[1] if '@' in self.mongodb_uri else self.mongodb_uri}")
        self.db_client = MongoClient(self.mongodb_uri)
        self.db = self.db_client[self.db_name]
        self.assets_collection = self.db["assets"]
        
        # Store test data
        self.test_assets = []
        self.tampered_assets = []
        
        # Results storage
        self.results = {
            "tests_run": 0,
            "tampering_detected": 0,
            "recovery_attempted": 0,
            "recovery_successful": 0,
            "detection_times": [],
            "recovery_times": [],
            "tampering_types": {},
        }
        
    def create_test_asset(self):
        """Create a test asset with known metadata."""
        asset_id = f"integrity-test-{uuid.uuid4()}"
        wallet_address = "0x" + os.urandom(20).hex()
        
        # Generate metadata with fields we can tamper with later
        critical_metadata = {
            "title": f"Integrity Test Document {random.randint(1000, 9999)}",
            "document_type": random.choice(["tax_record", "medical_record", "property_deed", "contract"]),
            "document_id": f"DOC-{random.randint(10000, 99999)}",
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "sensitive_value": random.randint(1000, 9999),
            "test_marker": "ORIGINAL_VALUE"  # This will be our tampering target
        }
        
        non_critical_metadata = {
            "description": "This is a test document for integrity verification",
            "tags": ["test", "integrity", "verification"],
            "department": random.choice(["Finance", "HR", "Legal", "Operations"]),
            "retention_period": f"{random.randint(1, 7)} years"
        }
        
        # Create asset via API
        asset_data = {
            "asset_id": asset_id,
            "wallet_address": wallet_address,
            "critical_metadata": critical_metadata,
            "non_critical_metadata": non_critical_metadata
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/upload/process",
                json=asset_data,
                timeout=300
            )
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"Created test asset: {asset_id}")
                
                # Store created asset for testing
                self.test_assets.append({
                    "asset_id": asset_id,
                    "wallet_address": wallet_address,
                    "document_id": response_data.get("document_id"),
                    "original_metadata": critical_metadata.copy(),
                    "response": response_data
                })
                
                return True
            else:
                print(f"Failed to create test asset: {response.status_code}, {response.text}")
                return False
                
        except Exception as e:
            print(f"Error creating test asset: {e}")
            return False
    
    def tamper_with_metadata(self, asset, tampering_type):
        """Directly modify metadata in MongoDB to simulate tampering."""
        if not asset:
            return False
            
        asset_id = asset["asset_id"]
        
        try:
            # Find the current version of the asset
            query = {"assetId": asset_id, "isCurrent": True}
            original_doc = self.assets_collection.find_one(query)
            
            if not original_doc:
                print(f"Could not find asset for tampering: {asset_id}")
                return False
                
            # Store original document for reference
            asset["original_doc"] = original_doc
            
            # Prepare update based on tampering type
            update_data = None
            
            if tampering_type == "modify_critical":
                # Change a value in critical metadata
                update_data = {
                    "$set": {
                        "criticalMetadata.test_marker": "TAMPERED_VALUE",
                        "criticalMetadata.sensitive_value": 99999
                    }
                }
                tampering_description = "Modified critical metadata fields"
                
            elif tampering_type == "delete_critical_field":
                # Remove a field from critical metadata
                update_data = {
                    "$unset": {
                        "criticalMetadata.test_marker": ""
                    }
                }
                tampering_description = "Deleted a critical metadata field"
                
            elif tampering_type == "add_critical_field":
                # Add a new field to critical metadata
                update_data = {
                    "$set": {
                        "criticalMetadata.injected_field": "INJECTED_VALUE"
                    }
                }
                tampering_description = "Added unauthorized field to critical metadata"
                
            elif tampering_type == "modify_blockchain_ref":
                # Tamper with blockchain reference
                update_data = {
                    "$set": {
                        "ipfsHash": "QmTampered" + os.urandom(10).hex()
                    }
                }
                tampering_description = "Modified IPFS hash reference"
                
            elif tampering_type == "fake_deletion":
                # Set deletion status inconsistently
                # Don't modify isDeleted in MongoDB, which would be detected by our deletion check
                update_data = {
                    "$set": {
                        "criticalMetadata.isDeleted": True,
                        "nonCriticalMetadata.deletionDate": datetime.now().strftime("%Y-%m-%d")
                    }
                }
                tampering_description = "Added fake deletion markers to metadata"
            
            if update_data:
                # Perform the tampering
                result = self.assets_collection.update_one(query, update_data)
                
                if result.modified_count > 0:
                    print(f"Successfully tampered with asset {asset_id}: {tampering_description}")
                    
                    # Store tampering details
                    asset["tampering_type"] = tampering_type
                    asset["tampering_description"] = tampering_description
                    self.tampered_assets.append(asset)
                    
                    return True
                else:
                    print(f"Failed to tamper with asset {asset_id}")
                    return False
            else:
                print(f"Invalid tampering type: {tampering_type}")
                return False
                
        except Exception as e:
            print(f"Error tampering with asset {asset_id}: {e}")
            return False
    
    def verify_asset_integrity(self, asset):
        """Test if the system detects tampering when retrieving the asset."""
        if not asset:
            return None
            
        asset_id = asset["asset_id"]
        
        try:
            # Time the verification process
            start_time = time.time()
            
            # Retrieve asset through API (which should verify integrity)
            response = requests.get(
                f"{self.base_url}/retrieve/{asset_id}?auto_recover=false",  # Disable auto-recovery to measure detection only
                timeout=300
            )
            
            detection_time = time.time() - start_time
            
            # Process response
            if response.status_code == 200:
                data = response.json()
                asset["verification_response"] = data
                
                # Check if tampering was detected
                verification = data.get("verification", {})
                tampering_detected = not verification.get("verified", True)
                recovery_needed = verification.get("recovery_needed", False)
                
                # Store result
                result = {
                    "asset_id": asset_id,
                    "tampering_type": asset.get("tampering_type"),
                    "tampering_detected": tampering_detected,
                    "recovery_needed": recovery_needed,
                    "detection_time": detection_time,
                    "verification_message": verification.get("message")
                }
                
                # Update test statistics
                if tampering_detected:
                    self.results["tampering_detected"] += 1
                    self.results["detection_times"].append(detection_time)
                    
                    tampering_type = asset.get("tampering_type", "unknown")
                    if tampering_type not in self.results["tampering_types"]:
                        self.results["tampering_types"][tampering_type] = {
                            "detected": 0, "total": 0
                        }
                    self.results["tampering_types"][tampering_type]["detected"] += 1
                    self.results["tampering_types"][tampering_type]["total"] += 1
                else:
                    tampering_type = asset.get("tampering_type", "unknown")
                    if tampering_type not in self.results["tampering_types"]:
                        self.results["tampering_types"][tampering_type] = {
                            "detected": 0, "total": 0
                        }
                    self.results["tampering_types"][tampering_type]["total"] += 1
                
                return result
            else:
                print(f"Error verifying asset {asset_id}: {response.status_code}, {response.text}")
                return None
                
        except Exception as e:
            print(f"Exception verifying asset {asset_id}: {e}")
            return None
    
    def test_recovery_performance(self, asset):
        """Test performance of recovery when tampering is detected."""
        if not asset:
            return None
            
        asset_id = asset["asset_id"]
        
        try:
            # Time the recovery process
            start_time = time.time()
            
            # Retrieve asset through API with auto-recovery enabled
            response = requests.get(
                f"{self.base_url}/retrieve/{asset_id}?auto_recover=true",
                timeout=300
            )
            
            recovery_time = time.time() - start_time
            
            # Process response
            if response.status_code == 200:
                data = response.json()
                asset["recovery_response"] = data
                
                # Check if recovery was performed successfully
                verification = data.get("verification", {})
                recovery_successful = verification.get("recovery_successful", False)
                new_version_created = verification.get("new_version_created", False)
                
                # Store result
                result = {
                    "asset_id": asset_id,
                    "tampering_type": asset.get("tampering_type"),
                    "recovery_time": recovery_time,
                    "recovery_successful": recovery_successful,
                    "new_version_created": new_version_created,
                    "recovery_message": verification.get("message")
                }
                
                # Update test statistics
                self.results["recovery_attempted"] += 1
                self.results["recovery_times"].append(recovery_time)
                
                if recovery_successful:
                    self.results["recovery_successful"] += 1
                
                return result
            else:
                print(f"Error during recovery for asset {asset_id}: {response.status_code}, {response.text}")
                return None
                
        except Exception as e:
            print(f"Exception during recovery for asset {asset_id}: {e}")
            return None
    
    def cleanup_test_assets(self):
        """Clean up test assets after testing."""
        if not self.test_assets:
            return
            
        print("\nCleaning up test assets...")
        
        for asset in self.test_assets:
            asset_id = asset["asset_id"]
            wallet_address = asset["wallet_address"]
            
            try:
                # Delete the asset through API
                delete_data = {
                    "asset_id": asset_id,
                    "wallet_address": wallet_address,
                    "reason": "Test cleanup"
                }
                
                response = requests.post(
                    f"{self.base_url}/delete",
                    json=delete_data,
                    timeout=300
                )
                
                if response.status_code == 200:
                    print(f"Successfully deleted test asset: {asset_id}")
                else:
                    print(f"Failed to delete test asset {asset_id}: {response.status_code}")
                    
            except Exception as e:
                print(f"Error deleting test asset {asset_id}: {e}")
    
    def run_test(self, num_assets=5, tampering_types=None):
        """Run the integrity verification and recovery test."""
        # Define available tampering types
        all_tampering_types = [
            "modify_critical", 
            "delete_critical_field", 
            "add_critical_field", 
            "modify_blockchain_ref",
            "fake_deletion"
        ]
        
        # Determine which tampering types to test
        if tampering_types == "all":
            tampering_types = all_tampering_types
        elif not tampering_types:
            tampering_types = ["modify_critical"]  # Default
        
        print(f"\n=== INTEGRITY VERIFICATION AND RECOVERY TEST ===")
        print(f"Testing {num_assets} assets with tampering types: {', '.join(tampering_types)}")
        
        # Create test assets
        print("\nCreating test assets...")
        for i in range(num_assets):
            self.create_test_asset()
            time.sleep(1)  # Small delay between creations
        
        if not self.test_assets:
            print("Failed to create any test assets. Aborting test.")
            return
            
        # Allow time for blockchain transactions to complete
        print("Waiting for blockchain transactions to complete...")
        time.sleep(10)
        
        # Apply different tampering methods to test assets
        print("\nApplying tampering to test assets...")
        assets_per_type = max(1, num_assets // len(tampering_types))
        
        for i, asset in enumerate(self.test_assets):
            tampering_type = tampering_types[min(i // assets_per_type, len(tampering_types) - 1)]
            self.tamper_with_metadata(asset, tampering_type)
        
        # Test tampering detection
        print("\nTesting tampering detection...")
        verification_results = []
        
        for asset in self.tampered_assets:
            self.results["tests_run"] += 1
            result = self.verify_asset_integrity(asset)
            if result:
                verification_results.append(result)
                print(f"Asset {asset['asset_id']} tampering detected: {result['tampering_detected']} ({result['detection_time']:.4f}s)")
        
        # Test recovery performance
        print("\nTesting recovery performance...")
        recovery_results = []
        
        for asset in self.tampered_assets:
            result = self.test_recovery_performance(asset)
            if result:
                recovery_results.append(result)
                print(f"Asset {asset['asset_id']} recovery successful: {result['recovery_successful']} ({result['recovery_time']:.4f}s)")
        
        # Calculate and display results
        self.calculate_and_display_results()
        
        # Cleanup
        self.cleanup_test_assets()
        
        return self.results
    
    def calculate_and_display_results(self):
        """Calculate and display test results."""
        print("\n=== INTEGRITY VERIFICATION AND RECOVERY TEST RESULTS ===")
        
        # Basic counts
        print(f"\nTampering Detection:")
        print(f"  Tests run: {self.results['tests_run']}")
        detection_rate = self.results['tampering_detected'] / max(1, self.results['tests_run']) * 100
        print(f"  Tampering detected: {self.results['tampering_detected']} ({detection_rate:.1f}%)")
        
        # Detection by tampering type
        print("\nDetection by Tampering Type:")
        for tampering_type, stats in self.results["tampering_types"].items():
            detection_rate = stats['detected'] / max(1, stats['total']) * 100
            print(f"  {tampering_type}: {stats['detected']}/{stats['total']} ({detection_rate:.1f}%)")
        
        # Detection performance
        if self.results["detection_times"]:
            avg_detection = sum(self.results["detection_times"]) / len(self.results["detection_times"])
            min_detection = min(self.results["detection_times"])
            max_detection = max(self.results["detection_times"])
            print(f"\nDetection Performance:")
            print(f"  Average detection time: {avg_detection:.4f}s")
            print(f"  Min detection time: {min_detection:.4f}s")
            print(f"  Max detection time: {max_detection:.4f}s")
        
        # Recovery statistics
        print(f"\nRecovery Performance:")
        recovery_rate = self.results['recovery_successful'] / max(1, self.results['recovery_attempted']) * 100
        print(f"  Recovery attempts: {self.results['recovery_attempted']}")
        print(f"  Successful recoveries: {self.results['recovery_successful']} ({recovery_rate:.1f}%)")
        
        if self.results["recovery_times"]:
            avg_recovery = sum(self.results["recovery_times"]) / len(self.results["recovery_times"])
            min_recovery = min(self.results["recovery_times"])
            max_recovery = max(self.results["recovery_times"])
            print(f"  Average recovery time: {avg_recovery:.4f}s")
            print(f"  Min recovery time: {min_recovery:.4f}s")
            print(f"  Max recovery time: {max_recovery:.4f}s")
        
        # Detection vs. Recovery time comparison
        if self.results["detection_times"] and self.results["recovery_times"]:
            recovery_overhead = (avg_recovery / avg_detection) - 1
            print(f"\nRecovery Overhead:")
            print(f"  Recovery takes {recovery_overhead * 100:.1f}% longer than detection alone")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test integrity verification and recovery performance")
    parser.add_argument("--assets", type=int, default=5, help="Number of test assets to create")
    parser.add_argument("--tampering-types", default="all", 
                        help="Comma-separated list of tampering types to test, or 'all'")
    
    args = parser.parse_args()
    
    # Parse tampering types
    if args.tampering_types == "all":
        tampering_types = "all"
    else:
        tampering_types = [t.strip() for t in args.tampering_types.split(",")]
    
    # Run the test
    test = IntegrityRecoveryTest()
    test.run_test(args.assets, tampering_types)