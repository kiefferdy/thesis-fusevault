"""
Query Performance Comparison Test with Version History Testing

This script compares query response times across different storage approaches
and tests version history retrieval performance.

Usage:
    python query_test.py [--requests 20] [--test-history]
"""

import argparse
import time
import random
import statistics
import os
import requests
import pymongo
from pymongo import MongoClient
import matplotlib.pyplot as plt
import pandas as pd
from dotenv import load_dotenv


class QueryTest:
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
        self.transactions_collection = self.db["transactions"]
        
        # Results storage
        self.results = {
            "mongodb_query_times": [],
            "hybrid_query_times": [],
            "version_history_times": []
        }
    
    def fetch_existing_assets(self, limit=100):
        """Fetch IDs of existing assets from MongoDB."""
        print(f"Fetching up to {limit} existing assets from MongoDB...")
        
        try:
            # Query for current (non-deleted) assets
            assets = list(self.assets_collection.find(
                {"isCurrent": True, "isDeleted": False},
                {"assetId": 1, "walletAddress": 1}
            ).limit(limit))
            
            # Format the results
            test_assets = []
            for asset in assets:
                if "assetId" in asset and "walletAddress" in asset:
                    test_assets.append({
                        "asset_id": asset["assetId"],
                        "wallet_address": asset["walletAddress"]
                    })
            
            print(f"Found {len(test_assets)} existing assets")
            return test_assets
            
        except Exception as e:
            print(f"Error fetching assets from MongoDB: {e}")
            return []
    
    def fetch_assets_with_versions(self, min_versions=2, limit=20):
        """Find assets that have multiple versions for history testing."""
        print(f"Finding assets with at least {min_versions} versions...")
        
        try:
            # Use aggregation to find assets with multiple versions
            pipeline = [
                {"$group": {
                    "_id": "$assetId", 
                    "versions": {"$sum": 1},
                    "walletAddress": {"$first": "$walletAddress"}
                }},
                {"$match": {"versions": {"$gte": min_versions}}},
                {"$sort": {"versions": -1}},  # Sort by most versions first
                {"$limit": limit}
            ]
            
            assets_with_versions = list(self.assets_collection.aggregate(pipeline))
            
            # Format the results
            versioned_assets = []
            for asset in assets_with_versions:
                versioned_assets.append({
                    "asset_id": asset["_id"],
                    "wallet_address": asset["walletAddress"],
                    "version_count": asset["versions"]
                })
            
            print(f"Found {len(versioned_assets)} assets with {min_versions}+ versions")
            for i, asset in enumerate(versioned_assets):
                print(f"  {i+1}. Asset ID: {asset['asset_id']}, Versions: {asset['version_count']}")
                
            return versioned_assets
            
        except Exception as e:
            print(f"Error finding assets with versions: {e}")
            return []
    
    def benchmark_mongodb_query(self, asset_id, wallet_address):
        """Benchmark MongoDB-only query performance."""
        start_time = time.time()
        
        try:
            # Query MongoDB directly for the asset
            query = {"assetId": asset_id, "walletAddress": wallet_address, "isCurrent": True}
            result = self.assets_collection.find_one(query)
            
            query_time = time.time() - start_time
            return query_time, result is not None
        except Exception as e:
            print(f"Error in MongoDB query: {e}")
            return None, False
    
    def benchmark_hybrid_query(self, asset_id):
        """Benchmark hybrid (API) query performance."""
        start_time = time.time()
        
        try:
            # Use the retrieve API endpoint (which uses MongoDB + blockchain verification + IPFS if needed)
            response = requests.get(
                f"{self.base_url}/retrieve/{asset_id}",
                timeout=10
            )
            
            query_time = time.time() - start_time
            return query_time, response.status_code == 200
        except Exception as e:
            print(f"Error querying hybrid API: {e}")
            return None, False
    
    def benchmark_version_history_retrieval(self, asset_id):
        """Benchmark version history retrieval performance."""
        start_time = time.time()
        
        try:
            # Fetch version history through the API
            response = requests.get(
                f"{self.base_url}/transactions/asset/{asset_id}",
                timeout=10
            )
            
            query_time = time.time() - start_time
            success = response.status_code == 200
            
            # Get the number of versions if successful
            version_count = 0
            if success:
                data = response.json()
                # Count unique version numbers in transactions
                if "transactions" in data:
                    version_numbers = set()
                    for tx in data["transactions"]:
                        if "metadata" in tx and "versionNumber" in tx["metadata"]:
                            version_numbers.add(tx["metadata"]["versionNumber"])
                    version_count = len(version_numbers)
            
            return query_time, success, version_count
            
        except Exception as e:
            print(f"Error retrieving version history: {e}")
            return None, False, 0
    
    def run_benchmark(self, num_queries=20, test_history=False):
        """Run query benchmarks with existing assets."""
        print(f"Running query benchmarks ({num_queries} iterations)...")
        
        # Fetch existing assets
        test_assets = self.fetch_existing_assets(limit=max(100, num_queries * 2))
        
        if not test_assets:
            print("No existing assets found in MongoDB. Please create some assets first.")
            return
        
        # Select random assets to query (or use all if we have fewer than requested)
        test_subset = random.sample(test_assets, min(num_queries, len(test_assets)))
        
        # Lists to store results
        mongodb_times = []
        hybrid_times = []
        successful_pairs = 0  # Count pairs where both queries succeeded
        
        # Run the benchmarks for each asset
        for i, asset in enumerate(test_subset):
            asset_id = asset["asset_id"]
            wallet_address = asset["wallet_address"]
            
            print(f"Benchmarking queries for asset {i+1}/{len(test_subset)}: {asset_id}")
            
            # MongoDB query
            mongo_time, mongo_success = self.benchmark_mongodb_query(asset_id, wallet_address)
            
            # Hybrid query
            hybrid_time, hybrid_success = self.benchmark_hybrid_query(asset_id)
            
            # Only count results where both queries succeeded for the same asset
            if mongo_time is not None and mongo_success and hybrid_time is not None and hybrid_success:
                mongodb_times.append(mongo_time)
                hybrid_times.append(hybrid_time)
                successful_pairs += 1
                print(f"  MongoDB: {mongo_time:.6f}s | Hybrid: {hybrid_time:.6f}s | Ratio: {hybrid_time/mongo_time:.2f}x")
            else:
                print(f"  Skipping this asset (MongoDB success: {mongo_success}, Hybrid success: {hybrid_success})")
        
        # Store results
        self.results["mongodb_query_times"] = mongodb_times
        self.results["hybrid_query_times"] = hybrid_times
        
        print(f"\nCompleted benchmark with {successful_pairs} successful query pairs")
        
        # Run version history benchmarks if requested
        if test_history:
            self.run_version_history_benchmark()
        
        # Calculate and print statistics
        self.calculate_and_print_results()
        
        return self.results
    
    def run_version_history_benchmark(self, min_versions=2, num_tests=10):
        """Run version history retrieval benchmark."""
        print("\n--- RUNNING VERSION HISTORY RETRIEVAL TEST ---")
        
        # Find assets with multiple versions
        versioned_assets = self.fetch_assets_with_versions(min_versions, limit=num_tests)
        
        if not versioned_assets:
            print("No assets with multiple versions found. Skipping version history test.")
            return
        
        history_times = []
        version_counts = []
        
        # Benchmark each asset's version history retrieval
        for i, asset in enumerate(versioned_assets):
            asset_id = asset["asset_id"]
            version_count = asset["version_count"]
            
            print(f"Retrieving history for asset {i+1}/{len(versioned_assets)}: {asset_id} ({version_count} versions)")
            
            # Fetch version history
            query_time, success, actual_versions = self.benchmark_version_history_retrieval(asset_id)
            
            if success:
                history_times.append(query_time)
                version_counts.append(actual_versions)
                print(f"  Retrieval time: {query_time:.6f}s | Versions found: {actual_versions}")
            else:
                print(f"  Failed to retrieve history")
        
        # Store results
        self.results["version_history_times"] = history_times
        self.results["version_counts"] = version_counts
        
        print(f"\nCompleted version history benchmark with {len(history_times)} successful retrievals")
        
        # Analyze relationship between version count and retrieval time
        if len(history_times) > 1:
            # Calculate correlation
            df = pd.DataFrame({
                'versions': version_counts,
                'time': history_times
            })
            correlation = df['versions'].corr(df['time'])
            
            print(f"\nVersion History Analysis:")
            print(f"  Correlation between version count and retrieval time: {correlation:.4f}")
            
            # Group by version count and calculate average retrieval time
            if len(set(version_counts)) > 1:
                grouped = df.groupby('versions')['time'].mean()
                print("\n  Average retrieval time by version count:")
                for versions, avg_time in grouped.items():
                    print(f"    {versions} versions: {avg_time:.6f}s")
    
    def calculate_and_print_results(self):
        """Calculate and print query statistics."""
        # MongoDB statistics
        mongodb_times = self.results["mongodb_query_times"]
        hybrid_times = self.results["hybrid_query_times"]
        
        if not mongodb_times or not hybrid_times:
            print("Not enough successful queries to calculate statistics.")
            return
        
        # Calculate basic statistics
        mongo_avg = sum(mongodb_times) / len(mongodb_times)
        mongo_min = min(mongodb_times)
        mongo_max = max(mongodb_times)
        mongo_median = statistics.median(mongodb_times)
        mongo_stddev = statistics.stdev(mongodb_times) if len(mongodb_times) > 1 else 0
        
        hybrid_avg = sum(hybrid_times) / len(hybrid_times)
        hybrid_min = min(hybrid_times)
        hybrid_max = max(hybrid_times)
        hybrid_median = statistics.median(hybrid_times)
        hybrid_stddev = statistics.stdev(hybrid_times) if len(hybrid_times) > 1 else 0
        
        # Direct query-by-query comparison
        ratios = [h/m for h, m in zip(hybrid_times, mongodb_times)]
        avg_ratio = sum(ratios) / len(ratios)
        median_ratio = statistics.median(ratios)
        
        # Print results
        print("\n--- QUERY BENCHMARK RESULTS ---")
        print(f"MongoDB Queries ({len(mongodb_times)} successful):")
        print(f"  Average: {mongo_avg:.6f}s")
        print(f"  Min:     {mongo_min:.6f}s")
        print(f"  Max:     {mongo_max:.6f}s")
        
        print(f"\nHybrid Queries ({len(hybrid_times)} successful):")
        print(f"  Average: {hybrid_avg:.6f}s")
        print(f"  Min:     {hybrid_min:.6f}s")
        print(f"  Max:     {hybrid_max:.6f}s")
        
        print(f"  Average ratio: Hybrid is {avg_ratio:.2f}x slower than MongoDB-only")
        
        # Version history statistics
        history_times = self.results.get("version_history_times", [])
        if history_times:
            history_avg = sum(history_times) / len(history_times)
            history_min = min(history_times)
            history_max = max(history_times)
            
            print(f"\nVersion History Retrieval ({len(history_times)} successful):")
            print(f"  Average: {history_avg:.6f}s")
            print(f"  Min:     {history_min:.6f}s")
            print(f"  Max:     {history_max:.6f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query performance comparison test with version history testing")
    parser.add_argument("--requests", default=20, type=int, help="Number of queries to run")
    parser.add_argument("--test-history", action="store_true", help="Enable version history retrieval testing")
    
    args = parser.parse_args()
    
    # Run the test
    test = QueryTest()
    test.run_benchmark(args.requests, args.test_history)