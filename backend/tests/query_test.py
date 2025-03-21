"""
Query Performance Comparison Test using .env configuration

This script compares query response times across different storage approaches
without creating new test assets. It uses existing assets in your MongoDB database
and reads connection details from your .env file.

Usage:
    python query_test.py [--requests 20]
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
        self.wallet_address = os.getenv("WALLET_ADDRESS", "")
        
        # Set up API base URL
        self.base_url = f"http://{self.api_host}:{self.api_port}/api"
        
        # Connect to MongoDB
        print(f"Connecting to MongoDB: {self.mongodb_uri.split('@')[1] if '@' in self.mongodb_uri else self.mongodb_uri}")
        self.db_client = MongoClient(self.mongodb_uri)
        self.db = self.db_client[self.db_name]
        self.assets_collection = self.db["assets"]
        
        # Results storage
        self.results = {
            "mongodb_query_times": [],
            "full_stack_query_times": []  # Renamed from hybrid_query_times
        }
    
    def fetch_existing_assets(self, limit=100):
        """Fetch IDs of existing assets from MongoDB."""
        print(f"Fetching up to {limit} existing assets from MongoDB...")
        
        try:
            # If wallet address is available in .env, filter by it
            query = {"isCurrent": True, "isDeleted": False}
            if self.wallet_address:
                print(f"Using wallet address from .env: {self.wallet_address}")
                query["walletAddress"] = self.wallet_address
            
            # Query for current (non-deleted) assets
            assets = list(self.assets_collection.find(
                query,
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
    
    def benchmark_full_stack_query(self, asset_id):
        """Benchmark full stack (MongoDB + IPFS + Blockchain) query performance."""
        start_time = time.time()
        
        try:
            # Use the retrieve API endpoint (which uses MongoDB + blockchain verification + IPFS if needed)
            response = requests.get(
                f"{self.base_url}/retrieve/{asset_id}",
                timeout=30  # Increased timeout for blockchain operations
            )
            
            query_time = time.time() - start_time
            return query_time, response.status_code == 200
        except Exception as e:
            print(f"Error querying full stack API: {e}")
            return None, False
    
    def run_benchmark(self, num_queries=20):
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
        full_stack_times = []
        successful_pairs = 0  # Count pairs where both queries succeeded
        
        # Run the benchmarks for each asset
        for i, asset in enumerate(test_subset):
            asset_id = asset["asset_id"]
            wallet_address = asset["wallet_address"]
            
            print(f"Benchmarking queries for asset {i+1}/{len(test_subset)}: {asset_id}")
            
            # MongoDB query
            mongo_time, mongo_success = self.benchmark_mongodb_query(asset_id, wallet_address)
            
            # Full stack query (MongoDB + IPFS + Blockchain)
            full_stack_time, full_stack_success = self.benchmark_full_stack_query(asset_id)
            
            # Only count results where both queries succeeded for the same asset
            if mongo_time is not None and mongo_success and full_stack_time is not None and full_stack_success:
                mongodb_times.append(mongo_time)
                full_stack_times.append(full_stack_time)
                successful_pairs += 1
                print(f"  MongoDB: {mongo_time:.6f}s | MongoDB+IPFS+Blockchain: {full_stack_time:.6f}s | Ratio: {full_stack_time/mongo_time:.2f}x")
            else:
                print(f"  Skipping this asset (MongoDB success: {mongo_success}, Full Stack success: {full_stack_success})")
                if not full_stack_success:
                    print("  - The full stack query might fail due to IPFS authentication issues or blockchain timeout")
        
        # Store results
        self.results["mongodb_query_times"] = mongodb_times
        self.results["full_stack_query_times"] = full_stack_times
        
        print(f"\nCompleted benchmark with {successful_pairs} successful query pairs")
        
        # Calculate and print statistics
        self.calculate_and_print_results()
        
        return self.results
    
    def calculate_and_print_results(self):
        """Calculate and print query statistics."""
        # MongoDB statistics
        mongodb_times = self.results["mongodb_query_times"]
        full_stack_times = self.results["full_stack_query_times"]
        
        if not mongodb_times or not full_stack_times:
            print("Not enough successful queries to calculate statistics.")
            return
        
        # Calculate basic statistics
        mongo_avg = sum(mongodb_times) / len(mongodb_times)
        mongo_min = min(mongodb_times)
        mongo_max = max(mongodb_times)
        mongo_median = statistics.median(mongodb_times)
        mongo_stddev = statistics.stdev(mongodb_times) if len(mongodb_times) > 1 else 0
        
        full_stack_avg = sum(full_stack_times) / len(full_stack_times)
        full_stack_min = min(full_stack_times)
        full_stack_max = max(full_stack_times)
        full_stack_median = statistics.median(full_stack_times)
        full_stack_stddev = statistics.stdev(full_stack_times) if len(full_stack_times) > 1 else 0
        
        # Direct query-by-query comparison
        ratios = [f/m for f, m in zip(full_stack_times, mongodb_times)]
        avg_ratio = sum(ratios) / len(ratios)
        median_ratio = statistics.median(ratios)
        
        # Print results
        print("\n--- QUERY BENCHMARK RESULTS ---")
        print(f"MongoDB Queries ({len(mongodb_times)} successful):")
        print(f"  Average: {mongo_avg:.6f}s")
        print(f"  Min:     {mongo_min:.6f}s")
        print(f"  Max:     {mongo_max:.6f}s")
        print(f"  Median:  {mongo_median:.6f}s")
        print(f"  StdDev:  {mongo_stddev:.6f}s")
        
        print(f"\nMongoDB + IPFS + Blockchain Queries ({len(full_stack_times)} successful):")
        print(f"  Average: {full_stack_avg:.6f}s")
        print(f"  Min:     {full_stack_min:.6f}s")
        print(f"  Max:     {full_stack_max:.6f}s")
        print(f"  Median:  {full_stack_median:.6f}s")
        print(f"  StdDev:  {full_stack_stddev:.6f}s")
        
        print(f"\nPerformance Comparison:")
        print(f"  Average ratio: Full stack is {avg_ratio:.2f}x slower than MongoDB-only")
        print(f"  Median ratio: Full stack is {median_ratio:.2f}x slower than MongoDB-only")
        print(f"  Overhead: {(full_stack_avg - mongo_avg):.6f}s per query")

        # Optional: Create visualization
        try:
            plt.figure(figsize=(12, 6))
            
            # Plot individual query times
            plt.subplot(1, 2, 1)
            plt.scatter(range(len(mongodb_times)), mongodb_times, label='MongoDB Only')
            plt.scatter(range(len(full_stack_times)), full_stack_times, label='MongoDB + IPFS + Blockchain')
            plt.xlabel('Query Number')
            plt.ylabel('Response Time (s)')
            plt.title('Query Response Times')
            plt.legend()
            
            # Plot average comparison
            plt.subplot(1, 2, 2)
            plt.bar(['MongoDB Only', 'MongoDB + IPFS + Blockchain'], [mongo_avg, full_stack_avg])
            plt.ylabel('Average Response Time (s)')
            plt.title('Average Query Performance')
            
        except Exception as e:
            print(f"Could not create visualization: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Query performance comparison test using .env config")
    parser.add_argument("--requests", default=20, type=int, help="Number of queries to run")
    
    args = parser.parse_args()
    
    # Run the test
    test = QueryTest()
    test.run_benchmark(args.requests)