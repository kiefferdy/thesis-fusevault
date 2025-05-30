"""
Scalability Test for Digital Asset Management API.

This test evaluates how well the application scales by measuring:
1. Request performance
2. Concurrent request handling
3. Success rates
4. Response times

Usage:
    python scalability_test.py --host localhost --port 8000 --requests 100 --concurrency 10
"""

import argparse
import asyncio
import json
import os
import random
import time
import uuid
from datetime import datetime
import aiohttp
import numpy as np
import matplotlib.pyplot as plt


class ScalabilityTest:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}/api"
        self.results = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": [],
            "throughput": 0,
            "max_concurrent_requests": 0,
            "request_error_rates": {},
            "endpoint_performance": {}
        }
        
        # Tracking for in-progress requests
        self.concurrent_requests = 0
        self.max_concurrent = 0

    def generate_test_asset(self):
        """Generate a simple test asset with minimal complexity."""
        return {
            "asset_id": str(uuid.uuid4()),
            "wallet_address": f"0x{os.urandom(20).hex()}",
            "critical_metadata": {
                "document_type": random.choice(["document", "record", "contract"]),
                "created_at": datetime.now().isoformat()
            },
            "non_critical_metadata": {
                "tags": random.sample(["tag1", "tag2", "tag3"], k=2)
            }
        }

    async def upload_asset(self, session, semaphore):
        """Upload a single asset with performance tracking."""
        async with semaphore:
            # Track concurrent requests
            self.concurrent_requests += 1
            self.max_concurrent = max(self.max_concurrent, self.concurrent_requests)
            
            endpoint = f"{self.base_url}/upload/process"
            asset_data = self.generate_test_asset()
            start_time = time.time()
            
            try:
                async with session.post(endpoint, json=asset_data) as response:
                    response_time = time.time() - start_time
                    self.results["response_times"].append(response_time)
                    self.results["total_requests"] += 1
                    
                    # Track endpoint-specific performance
                    endpoint_key = "upload/process"
                    if endpoint_key not in self.results["endpoint_performance"]:
                        self.results["endpoint_performance"][endpoint_key] = {
                            "count": 0,
                            "success_count": 0,
                            "response_times": []
                        }
                    
                    self.results["endpoint_performance"][endpoint_key]["count"] += 1
                    self.results["endpoint_performance"][endpoint_key]["response_times"].append(response_time)
                    
                    if response.status == 200:
                        self.results["successful_requests"] += 1
                        self.results["endpoint_performance"][endpoint_key]["success_count"] += 1
                        return {"asset": asset_data, "response": await response.json(), "success": True}
                    else:
                        self.results["failed_requests"] += 1
                        error_key = f"Error-{response.status}"
                        self.results["request_error_rates"][error_key] = self.results["request_error_rates"].get(error_key, 0) + 1
                        return {"success": False}
            except Exception as e:
                response_time = time.time() - start_time
                self.results["response_times"].append(response_time)
                self.results["total_requests"] += 1
                self.results["failed_requests"] += 1
                
                error_key = f"Exception-{type(e).__name__}"
                self.results["request_error_rates"][error_key] = self.results["request_error_rates"].get(error_key, 0) + 1
                return {"success": False}
            finally:
                self.concurrent_requests -= 1

    async def run_test(self, total_requests=100, concurrency=10):
        """Run the scalability test with a fixed number of requests."""
        print(f"Starting scalability test with total requests: {total_requests}, concurrency: {concurrency}")
        
        # Initialize timer
        start_time = time.time()
        semaphore = asyncio.Semaphore(concurrency)
        
        # Set up a client session
        async with aiohttp.ClientSession() as session:
            # Create tasks for uploads
            tasks = []
            for _ in range(total_requests):
                task = asyncio.create_task(self.upload_asset(session, semaphore))
                tasks.append(task)
            
            # Wait for all tasks to complete
            await asyncio.gather(*tasks)
        
        # Record end time and calculate final metrics
        end_time = time.time()
        test_duration = end_time - start_time
        
        # Calculate throughput (requests per second)
        self.results["throughput"] = self.results["total_requests"] / test_duration
        self.results["test_duration"] = test_duration
        self.results["max_concurrent_requests"] = self.max_concurrent
        
        # Calculate percentiles for response times
        if self.results["response_times"]:
            response_times = sorted(self.results["response_times"])
            self.results["p50_response_time"] = np.percentile(response_times, 50)
            self.results["p90_response_time"] = np.percentile(response_times, 90)
            self.results["p95_response_time"] = np.percentile(response_times, 95)
            self.results["p99_response_time"] = np.percentile(response_times, 99)
            self.results["std_dev_response_time"] = np.std(response_times)
        
        # Calculate endpoint performance details
        for endpoint, data in self.results["endpoint_performance"].items():
            if data["count"] > 0:
                data["success_rate"] = data["success_count"] / data["count"]
                data["avg_response_time"] = sum(data["response_times"]) / data["count"]
        # Print results summary
        self.print_results_summary()        
        return self.results

    def print_results_summary(self):
        """Print a comprehensive summary of test results."""
        print("\n--- SCALABILITY TEST RESULTS ---")
        print(f"Total Requests: {self.results['total_requests']}")
        print(f"Successful Requests: {self.results['successful_requests']} ({self.results['successful_requests'] / max(1, self.results['total_requests']) * 100:.1f}%)")
        print(f"Failed Requests: {self.results['failed_requests']} ({self.results['failed_requests'] / max(1, self.results['total_requests']) * 100:.1f}%)")
        print(f"Test Duration: {self.results.get('test_duration', 0):.2f} seconds")
        print(f"Throughput: {self.results['throughput']:.2f} requests/second")
        print(f"Max Concurrent Requests: {self.results['max_concurrent_requests']}")
        if self.results["response_times"]:
            print(f"  Average: {sum(self.results['response_times']) / len(self.results['response_times']):.4f}")
            
        
        if self.results["request_error_rates"]:
            print("\nError Breakdown:")
            for error, count in self.results["request_error_rates"].items():
                print(f"  {error}: {count} ({count / max(1, self.results['total_requests']) * 100:.1f}%)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test scalability of the asset management API")
    parser.add_argument("--host", default="localhost", help="API host")
    parser.add_argument("--port", default=8000, type=int, help="API port")
    parser.add_argument("--requests", default=100, type=int, help="Total number of requests to make")
    parser.add_argument("--concurrency", default=10, type=int, help="Maximum concurrent requests")
    
    args = parser.parse_args()
    
    # Run the scalability test
    test = ScalabilityTest(args.host, args.port)
    asyncio.run(test.run_test(
        total_requests=args.requests,
        concurrency=args.concurrency
    ))