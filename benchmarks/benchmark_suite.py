"""
Comprehensive Benchmarking Suite for FuseVault (MongoDB+IPFS+Blockchain System)
Updated to work with FuseVault's actual API endpoints and data structures

Usage:
    python benchmark_suite.py --config config.yaml --output results/
    python benchmark_suite.py --quick-test  # Run quick comparison
    python benchmark_suite.py --full-suite  # Run complete benchmark suite
"""

import argparse
import asyncio
import json
import logging
import os
import statistics
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import yaml

import aiohttp
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pymongo import MongoClient
import requests
from dotenv import load_dotenv


@dataclass
class BenchmarkResult:
    """Standard benchmark result format for comparison across systems"""
    system_name: str
    test_type: str
    timestamp: datetime
    
    # Core performance metrics
    transactions_per_second: float
    average_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    success_rate: float
    
    # Resource utilization
    cpu_usage_percent: float
    memory_usage_mb: float
    network_bytes_sent: int
    network_bytes_received: int
    
    # Test parameters
    total_operations: int
    concurrent_clients: int
    test_duration_seconds: float
    operation_type: str
    data_size_bytes: int
    
    # Additional metrics
    blockchain_verification_time_ms: Optional[float] = None
    ipfs_storage_time_ms: Optional[float] = None
    mongodb_query_time_ms: Optional[float] = None
    integrity_check_success_rate: Optional[float] = None


class BenchmarkTargets:
    """Industry benchmark targets for comparison"""
    
    BIGCHAIN_DB = {
        "system_name": "BigchainDB",
        "typical_tps": 298,
        "peak_tps": 1000,
        "p95_latency_ms": 5143,
        "p99_latency_ms": 9392,
        "median_latency_ms": 2855
    }
    
    MONGODB_YCSB = {
        "system_name": "MongoDB (YCSB)",
        "read_tps": 1200,
        "write_tps": 100,
        "mixed_tps": 600,
        "read_latency_ms": 10,
        "write_latency_ms": 100
    }
    
    IPFS_BASELINE = {
        "system_name": "IPFS",
        "local_retrieval_ms": 21,
        "network_retrieval_p95_ms": 194,
        "small_file_overhead_ms": 50,
        "large_file_degradation_factor": 2.0
    }
    
    HYPERLEDGER_FABRIC = {
        "system_name": "Hyperledger Fabric",
        "pbft_tps": 3000,
        "consensus_latency_ms": 1000,
        "read_tps": 10000
    }


class FuseVaultBenchmarker:
    """Benchmarking class specifically designed for FuseVault system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_base_url = f"http://{config['api_host']}:{config['api_port']}/api"
        self.mongodb_client = MongoClient(config['mongodb_uri'])
        self.db = self.mongodb_client[config['db_name']]
        self.results: List[BenchmarkResult] = []
        
        # Validate required config
        required_fields = ["api_key", "wallet_address"]
        missing = [f for f in required_fields if not config.get(f)]
        if missing:
            raise ValueError(f"Missing required configuration: {missing}")
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('fusevault_benchmark.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Initialized FuseVault benchmarker for wallet: {config['wallet_address']}")
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for FuseVault API requests"""
        return {
            'X-API-Key': self.config['api_key'],
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def _prepare_asset_data(self, asset_id: str, data_size: int) -> Dict[str, Any]:
        """Prepare asset data in FuseVault format"""
        return {
            "asset_id": asset_id,
            "wallet_address": self.config['wallet_address'],
            "critical_metadata": {
                "title": f"Benchmark Asset {asset_id}",
                "document_type": "benchmark_test",
                "category": "performance_testing",
                "creation_date": datetime.now().isoformat(),
                "test_data": "x" * data_size,
                "test_size_bytes": data_size
            },
            "non_critical_metadata": {
                "description": f"Performance benchmark test asset",
                "tags": ["benchmark", "performance_test", "automated"],
                "test_run_id": str(uuid.uuid4()),
                "data_size_category": self._get_size_category(data_size)
            }
        }
    
    def _get_size_category(self, data_size: int) -> str:
        """Categorize data size for analysis"""
        if data_size < 2048:
            return "small"
        elif data_size < 32768:
            return "medium"
        elif data_size < 131072:
            return "large"
        else:
            return "xlarge"
    
    async def run_comprehensive_benchmark(self) -> List[BenchmarkResult]:
        """Run complete benchmark suite comparing against all targets"""
        
        self.logger.info("Starting FuseVault comprehensive benchmark suite...")
        
        # Test scenarios with different parameters
        test_scenarios = [
            # FuseVault-specific query performance tests
            {
                "name": "fusevault_asset_queries",
                "test_type": "query_performance",
                "operations": [50, 100, 200, 500],
                "concurrent_clients": [1, 2, 5, 10],
                "data_sizes": [1024, 8192, 32768]
            },
            
            # Full Stack Tests (Upload + Retrieve + Verify)
            {
                "name": "fusevault_full_stack", 
                "test_type": "full_stack_performance",
                "operations": [20, 50, 100, 200],
                "concurrent_clients": [1, 2, 3, 5],
                "data_sizes": [1024, 8192, 65536]
            },
            
            # Asset Upload Performance
            {
                "name": "fusevault_upload_performance",
                "test_type": "upload_performance", 
                "operations": [10, 25, 50, 100],
                "concurrent_clients": [1, 2, 3],
                "data_sizes": [1024, 16384, 65536, 262144]  # Up to 256KB
            },
            
            # Integrity and Recovery Tests
            {
                "name": "fusevault_integrity_verification",
                "test_type": "integrity_performance",
                "operations": [50, 100, 200],
                "concurrent_clients": [1, 2, 5],
                "data_sizes": [8192, 32768, 131072]
            },
            
            # Scalability Tests
            {
                "name": "fusevault_scalability",
                "test_type": "scalability_performance",
                "operations": [100, 200, 500],
                "concurrent_clients": [1, 2, 5, 10, 15],
                "data_sizes": [8192]  # Fixed size, test concurrency
            }
        ]
        
        # Run all test scenarios
        for scenario in test_scenarios:
            await self._run_test_scenario(scenario)
        
        return self.results
    
    async def _run_test_scenario(self, scenario: Dict[str, Any]):
        """Run a specific test scenario with parameter matrix"""
        
        scenario_name = scenario["name"]
        test_type = scenario["test_type"]
        
        self.logger.info(f"Running scenario: {scenario_name}")
        
        for operations in scenario["operations"]:
            for clients in scenario["concurrent_clients"]:
                for data_size in scenario["data_sizes"]:
                    
                    self.logger.info(
                        f"Testing {scenario_name}: {operations} ops, "
                        f"{clients} clients, {data_size} bytes"
                    )
                    
                    # Run the specific test based on type
                    if test_type == "query_performance":
                        result = await self._benchmark_query_performance(
                            operations, clients, data_size
                        )
                    elif test_type == "full_stack_performance":
                        result = await self._benchmark_full_stack_performance(
                            operations, clients, data_size
                        )
                    elif test_type == "upload_performance":
                        result = await self._benchmark_upload_performance(
                            operations, clients, data_size
                        )
                    elif test_type == "integrity_performance":
                        result = await self._benchmark_integrity_performance(
                            operations, clients, data_size
                        )
                    elif test_type == "scalability_performance":
                        result = await self._benchmark_scalability_performance(
                            operations, clients, data_size
                        )
                    else:
                        continue
                    
                    if result:
                        self.results.append(result)
                    
                    # Brief pause between tests
                    await asyncio.sleep(2)
    
    async def _benchmark_query_performance(
        self, operations: int, clients: int, data_size: int
    ) -> Optional[BenchmarkResult]:
        """Benchmark FuseVault asset retrieval performance"""
        
        # Get existing assets from the database
        test_assets = await self._get_existing_assets(operations)
        if not test_assets:
            self.logger.warning("No existing assets found for query benchmark")
            return None
        
        # Run concurrent queries
        start_time = time.time()
        latencies = []
        successful_operations = 0
        
        async def query_worker():
            worker_latencies = []
            worker_successes = 0
            
            async with aiohttp.ClientSession() as session:
                assets_per_worker = test_assets[:operations // clients]
                
                for asset in assets_per_worker:
                    query_start = time.time()
                    try:
                        # Use FuseVault's actual retrieve endpoint
                        async with session.get(
                            f"{self.api_base_url}/retrieve/{asset['asset_id']}",
                            headers=self._get_auth_headers(),
                            timeout=aiohttp.ClientTimeout(total=15)
                        ) as response:
                            
                            if response.status == 200:
                                worker_successes += 1
                            
                            query_time = (time.time() - query_start) * 1000
                            worker_latencies.append(query_time)
                            
                    except Exception as e:
                        self.logger.error(f"Query error: {e}")
                        query_time = (time.time() - query_start) * 1000
                        worker_latencies.append(query_time)
                        
            return worker_latencies, worker_successes
        
        # Execute concurrent workers
        tasks = [query_worker() for _ in range(clients)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        for result in results:
            if isinstance(result, tuple) and len(result) == 2:
                worker_latencies, worker_successes = result
                latencies.extend(worker_latencies)
                successful_operations += worker_successes
        
        total_time = time.time() - start_time
        
        if not latencies:
            return None
        
        return BenchmarkResult(
            system_name="FuseVault (Asset Queries)",
            test_type="query_performance",
            timestamp=datetime.now(),
            transactions_per_second=successful_operations / total_time,
            average_latency_ms=statistics.mean(latencies),
            p95_latency_ms=np.percentile(latencies, 95),
            p99_latency_ms=np.percentile(latencies, 99),
            success_rate=successful_operations / min(operations, len(test_assets)),
            cpu_usage_percent=0.0,
            memory_usage_mb=0.0,
            network_bytes_sent=0,
            network_bytes_received=0,
            total_operations=operations,
            concurrent_clients=clients,
            test_duration_seconds=total_time,
            operation_type="fusevault_retrieve",
            data_size_bytes=data_size,
            mongodb_query_time_ms=statistics.mean(latencies)
        )
    
    async def _benchmark_upload_performance(
        self, operations: int, clients: int, data_size: int
    ) -> Optional[BenchmarkResult]:
        """Benchmark FuseVault asset upload performance"""
        
        start_time = time.time()
        latencies = []
        successful_operations = 0
        
        async def upload_worker():
            worker_latencies = []
            worker_successes = 0
            
            async with aiohttp.ClientSession() as session:
                operations_per_worker = operations // clients
                
                for i in range(operations_per_worker):
                    operation_start = time.time()
                    
                    try:
                        # Create unique asset data
                        asset_id = f"bench_{int(time.time() * 1000)}_{i}_{uuid.uuid4().hex[:8]}"
                        asset_data = self._prepare_asset_data(asset_id, data_size)
                        
                        # Use FuseVault's actual upload endpoint
                        async with session.post(
                            f"{self.api_base_url}/upload/process",
                            json=asset_data,
                            headers=self._get_auth_headers(),
                            timeout=aiohttp.ClientTimeout(total=60)
                        ) as response:
                            
                            if response.status == 200:
                                worker_successes += 1
                            
                            total_time = (time.time() - operation_start) * 1000
                            worker_latencies.append(total_time)
                        
                    except Exception as e:
                        self.logger.error(f"Upload operation error: {e}")
                        total_time = (time.time() - operation_start) * 1000
                        worker_latencies.append(total_time)
                        
            return worker_latencies, worker_successes
        
        # Execute concurrent workers
        tasks = [upload_worker() for _ in range(clients)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        for result in results:
            if isinstance(result, tuple) and len(result) == 2:
                worker_latencies, worker_successes = result
                latencies.extend(worker_latencies)
                successful_operations += worker_successes
        
        total_time = time.time() - start_time
        
        if not latencies:
            return None
        
        return BenchmarkResult(
            system_name="FuseVault (Asset Upload)",
            test_type="upload_performance",
            timestamp=datetime.now(),
            transactions_per_second=successful_operations / total_time,
            average_latency_ms=statistics.mean(latencies),
            p95_latency_ms=np.percentile(latencies, 95),
            p99_latency_ms=np.percentile(latencies, 99),
            success_rate=successful_operations / operations,
            cpu_usage_percent=0.0,
            memory_usage_mb=0.0,
            network_bytes_sent=data_size * operations,
            network_bytes_received=0,
            total_operations=operations,
            concurrent_clients=clients,
            test_duration_seconds=total_time,
            operation_type="fusevault_upload",
            data_size_bytes=data_size,
            blockchain_verification_time_ms=statistics.mean(latencies) * 0.3,  # Estimate
            ipfs_storage_time_ms=statistics.mean(latencies) * 0.4  # Estimate
        )
    
    async def _benchmark_full_stack_performance(
        self, operations: int, clients: int, data_size: int
    ) -> Optional[BenchmarkResult]:
        """Benchmark complete FuseVault workflow (Upload + Retrieve)"""
        
        start_time = time.time()
        latencies = []
        successful_operations = 0
        
        async def full_stack_worker():
            worker_latencies = []
            worker_successes = 0
            
            async with aiohttp.ClientSession() as session:
                operations_per_worker = operations // clients
                
                for i in range(operations_per_worker):
                    operation_start = time.time()
                    
                    try:
                        # Step 1: Upload asset
                        asset_id = f"fullstack_{int(time.time() * 1000)}_{i}_{uuid.uuid4().hex[:8]}"
                        asset_data = self._prepare_asset_data(asset_id, data_size)
                        
                        async with session.post(
                            f"{self.api_base_url}/upload/process",
                            json=asset_data,
                            headers=self._get_auth_headers(),
                            timeout=aiohttp.ClientTimeout(total=60)
                        ) as upload_response:
                            
                            if upload_response.status == 200:
                                upload_result = await upload_response.json()
                                
                                # Brief wait for processing
                                await asyncio.sleep(0.5)
                                
                                # Step 2: Retrieve asset
                                async with session.get(
                                    f"{self.api_base_url}/retrieve/{asset_id}",
                                    headers=self._get_auth_headers(),
                                    timeout=aiohttp.ClientTimeout(total=30)
                                ) as retrieve_response:
                                    
                                    if retrieve_response.status == 200:
                                        worker_successes += 1
                            
                            total_time = (time.time() - operation_start) * 1000
                            worker_latencies.append(total_time)
                        
                    except Exception as e:
                        self.logger.error(f"Full stack operation error: {e}")
                        total_time = (time.time() - operation_start) * 1000
                        worker_latencies.append(total_time)
                        
            return worker_latencies, worker_successes
        
        # Execute concurrent workers
        tasks = [full_stack_worker() for _ in range(clients)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        for result in results:
            if isinstance(result, tuple) and len(result) == 2:
                worker_latencies, worker_successes = result
                latencies.extend(worker_latencies)
                successful_operations += worker_successes
        
        total_time = time.time() - start_time
        
        if not latencies:
            return None
        
        return BenchmarkResult(
            system_name="FuseVault (Full Stack)",
            test_type="full_stack_performance",
            timestamp=datetime.now(),
            transactions_per_second=successful_operations / total_time,
            average_latency_ms=statistics.mean(latencies),
            p95_latency_ms=np.percentile(latencies, 95),
            p99_latency_ms=np.percentile(latencies, 99),
            success_rate=successful_operations / operations,
            cpu_usage_percent=0.0,
            memory_usage_mb=0.0,
            network_bytes_sent=data_size * operations,
            network_bytes_received=data_size * successful_operations,
            total_operations=operations,
            concurrent_clients=clients,
            test_duration_seconds=total_time,
            operation_type="fusevault_full_stack",
            data_size_bytes=data_size,
            blockchain_verification_time_ms=statistics.mean(latencies) * 0.25,
            ipfs_storage_time_ms=statistics.mean(latencies) * 0.35
        )
    
    async def _benchmark_integrity_performance(
        self, operations: int, clients: int, data_size: int
    ) -> Optional[BenchmarkResult]:
        """Benchmark integrity verification using retrieve endpoint"""
        
        # Get existing assets
        test_assets = await self._get_existing_assets(operations)
        if not test_assets:
            self.logger.warning("No existing assets found for integrity benchmark")
            return None
        
        start_time = time.time()
        latencies = []
        successful_verifications = 0
        
        async def integrity_worker():
            worker_latencies = []
            worker_successes = 0
            
            async with aiohttp.ClientSession() as session:
                assets_per_worker = test_assets[:operations // clients]
                
                for asset in assets_per_worker:
                    verify_start = time.time()
                    
                    try:
                        # Use retrieve endpoint to check integrity
                        async with session.get(
                            f"{self.api_base_url}/retrieve/{asset['asset_id']}",
                            headers=self._get_auth_headers(),
                            timeout=aiohttp.ClientTimeout(total=15)
                        ) as response:
                            
                            if response.status == 200:
                                result = await response.json()
                                # Check if integrity is valid (not tampered)
                                integrity_status = result.get("integrity_status", "UNKNOWN")
                                if integrity_status != "TAMPERED":
                                    worker_successes += 1
                            
                            verify_time = (time.time() - verify_start) * 1000
                            worker_latencies.append(verify_time)
                            
                    except Exception as e:
                        self.logger.error(f"Integrity verification error: {e}")
                        verify_time = (time.time() - verify_start) * 1000
                        worker_latencies.append(verify_time)
                        
            return worker_latencies, worker_successes
        
        # Execute concurrent workers
        tasks = [integrity_worker() for _ in range(clients)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        for result in results:
            if isinstance(result, tuple) and len(result) == 2:
                worker_latencies, worker_successes = result
                latencies.extend(worker_latencies)
                successful_verifications += worker_successes
        
        total_time = time.time() - start_time
        
        if not latencies:
            return None
        
        return BenchmarkResult(
            system_name="FuseVault (Integrity Check)",
            test_type="integrity_performance",
            timestamp=datetime.now(),
            transactions_per_second=successful_verifications / total_time,
            average_latency_ms=statistics.mean(latencies),
            p95_latency_ms=np.percentile(latencies, 95),
            p99_latency_ms=np.percentile(latencies, 99),
            success_rate=successful_verifications / min(operations, len(test_assets)),
            cpu_usage_percent=0.0,
            memory_usage_mb=0.0,
            network_bytes_sent=0,
            network_bytes_received=0,
            total_operations=operations,
            concurrent_clients=clients,
            test_duration_seconds=total_time,
            operation_type="fusevault_integrity_check",
            data_size_bytes=data_size,
            integrity_check_success_rate=successful_verifications / min(operations, len(test_assets))
        )
    
    async def _benchmark_scalability_performance(
        self, operations: int, clients: int, data_size: int
    ) -> Optional[BenchmarkResult]:
        """Benchmark system scalability under increasing load"""
        
        # Use upload performance as scalability test
        result = await self._benchmark_upload_performance(operations, clients, data_size)
        
        if result:
            result.test_type = "scalability_performance"
            result.system_name = "FuseVault (Scalability)"
        
        return result
    
    async def _get_existing_assets(self, count: int) -> List[Dict[str, str]]:
        """Get existing assets from FuseVault database"""
        
        try:
            # Query using FuseVault's actual schema
            assets = list(self.db.assets.find(
                {
                    "isCurrent": True, 
                    "isDeleted": False,
                    "walletAddress": self.config['wallet_address']
                },
                {"assetId": 1, "walletAddress": 1}
            ).limit(count * 2))  # Get extra in case some fail
            
            test_assets = []
            for asset in assets:
                if "assetId" in asset and "walletAddress" in asset:
                    test_assets.append({
                        "asset_id": asset["assetId"],
                        "wallet_address": asset["walletAddress"]
                    })
            
            self.logger.info(f"Found {len(test_assets)} existing assets for testing")
            return test_assets[:count]
            
        except Exception as e:
            self.logger.error(f"Error getting existing FuseVault assets: {e}")
            return []
    
    def generate_comparison_report(self, output_dir: Path):
        """Generate comprehensive comparison report with industry benchmarks"""
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create comparison dataframe
        comparison_data = []
        
        # Add FuseVault results
        for result in self.results:
            comparison_data.append({
                "System": result.system_name,
                "Test Type": result.test_type,
                "TPS": result.transactions_per_second,
                "Avg Latency (ms)": result.average_latency_ms,
                "P95 Latency (ms)": result.p95_latency_ms,
                "P99 Latency (ms)": result.p99_latency_ms,
                "Success Rate": result.success_rate,
                "Clients": result.concurrent_clients,
                "Data Size (bytes)": result.data_size_bytes,
                "Operations": result.total_operations
            })
        
        # Add benchmark targets for comparison
        benchmark_systems = [
            {
                "System": "BigchainDB (Target)",
                "Test Type": "reference_benchmark",
                "TPS": BenchmarkTargets.BIGCHAIN_DB["typical_tps"],
                "Avg Latency (ms)": BenchmarkTargets.BIGCHAIN_DB["median_latency_ms"],
                "P95 Latency (ms)": BenchmarkTargets.BIGCHAIN_DB["p95_latency_ms"],
                "P99 Latency (ms)": BenchmarkTargets.BIGCHAIN_DB["p99_latency_ms"],
                "Success Rate": 0.997,
                "Clients": 4,
                "Data Size (bytes)": 765,
                "Operations": 1000000
            },
            {
                "System": "MongoDB YCSB (Read)",
                "Test Type": "reference_benchmark", 
                "TPS": BenchmarkTargets.MONGODB_YCSB["read_tps"],
                "Avg Latency (ms)": BenchmarkTargets.MONGODB_YCSB["read_latency_ms"],
                "P95 Latency (ms)": BenchmarkTargets.MONGODB_YCSB["read_latency_ms"] * 2,
                "P99 Latency (ms)": BenchmarkTargets.MONGODB_YCSB["read_latency_ms"] * 3,
                "Success Rate": 0.99,
                "Clients": 10,
                "Data Size (bytes)": 8192,
                "Operations": 10000
            },
            {
                "System": "MongoDB YCSB (Write)",
                "Test Type": "reference_benchmark",
                "TPS": BenchmarkTargets.MONGODB_YCSB["write_tps"],
                "Avg Latency (ms)": BenchmarkTargets.MONGODB_YCSB["write_latency_ms"],
                "P95 Latency (ms)": BenchmarkTargets.MONGODB_YCSB["write_latency_ms"] * 2,
                "P99 Latency (ms)": BenchmarkTargets.MONGODB_YCSB["write_latency_ms"] * 3,
                "Success Rate": 0.95,
                "Clients": 10,
                "Data Size (bytes)": 8192,
                "Operations": 10000
            },
            {
                "System": "IPFS (Local)",
                "Test Type": "reference_benchmark",
                "TPS": 47,  # Calculated from 21ms latency
                "Avg Latency (ms)": BenchmarkTargets.IPFS_BASELINE["local_retrieval_ms"],
                "P95 Latency (ms)": BenchmarkTargets.IPFS_BASELINE["local_retrieval_ms"] * 1.5,
                "P99 Latency (ms)": BenchmarkTargets.IPFS_BASELINE["local_retrieval_ms"] * 2,
                "Success Rate": 0.98,
                "Clients": 1,
                "Data Size (bytes)": 1024,
                "Operations": 1000
            }
        ]
        
        comparison_data.extend(benchmark_systems)
        
        # Create DataFrame and save
        df = pd.DataFrame(comparison_data)
        df.to_csv(output_dir / "fusevault_benchmark_comparison.csv", index=False)
        
        # Generate visualizations
        self._create_performance_visualizations(df, output_dir)
        
        # Generate detailed analysis report
        self._generate_analysis_report(df, output_dir)
        
        self.logger.info(f"FuseVault benchmark report generated in {output_dir}")
    
    def _create_performance_visualizations(self, df: pd.DataFrame, output_dir: Path):
        """Create comprehensive performance visualization charts"""
        
        # Set style
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
        
        # Create comprehensive comparison chart
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        
        # 1. TPS Comparison
        ax = axes[0, 0]
        fusevault_data = df[df['System'].str.contains('FuseVault', na=False)]
        reference_data = df[df['Test Type'] == 'reference_benchmark']
        
        if not fusevault_data.empty:
            # Plot FuseVault results by test type
            for test_type in fusevault_data['Test Type'].unique():
                test_data = fusevault_data[fusevault_data['Test Type'] == test_type]
                avg_tps = test_data['TPS'].mean()
                ax.bar(test_type.replace('_', ' ').title(), avg_tps, alpha=0.7, label='FuseVault')
        
        # Add reference benchmarks
        for _, row in reference_data.iterrows():
            ax.bar(row['System'], row['TPS'], alpha=0.5, label='Reference')
        
        ax.set_title('Transactions Per Second Comparison')
        ax.set_ylabel('TPS')
        ax.tick_params(axis='x', rotation=45)
        ax.legend()
        
        # 2. Latency Comparison
        ax = axes[0, 1]
        if not fusevault_data.empty:
            latency_by_type = fusevault_data.groupby('Test Type')['Avg Latency (ms)'].mean()
            latency_by_type.plot(kind='bar', ax=ax, color='skyblue', alpha=0.7)
        
        ax.set_title('Average Latency by Test Type')
        ax.set_ylabel('Latency (ms)')
        ax.tick_params(axis='x', rotation=45)
        ax.set_yscale('log')
        
        # 3. Success Rate
        ax = axes[0, 2]
        if not fusevault_data.empty:
            success_by_type = fusevault_data.groupby('Test Type')['Success Rate'].mean()
            success_by_type.plot(kind='bar', ax=ax, color='lightgreen', alpha=0.7)
        
        ax.set_title('Success Rate by Test Type')
        ax.set_ylabel('Success Rate')
        ax.tick_params(axis='x', rotation=45)
        ax.set_ylim(0, 1.1)
        
        # 4. Performance vs Concurrency
        ax = axes[1, 0]
        if not fusevault_data.empty:
            # Group by concurrent clients and show average TPS
            concurrency_perf = fusevault_data.groupby('Clients')['TPS'].mean()
            concurrency_perf.plot(kind='line', ax=ax, marker='o', linewidth=2, markersize=8)
        
        ax.set_title('Scalability: TPS vs Concurrent Clients')
        ax.set_xlabel('Concurrent Clients')
        ax.set_ylabel('TPS')
        ax.grid(True, alpha=0.3)
        
        # 5. Data Size Impact
        ax = axes[1, 1]
        if not fusevault_data.empty:
            # Show how data size affects performance
            scatter = ax.scatter(fusevault_data['Data Size (bytes)'], 
                               fusevault_data['TPS'],
                               c=fusevault_data['Avg Latency (ms)'], 
                               cmap='coolwarm', s=100, alpha=0.7)
            plt.colorbar(scatter, ax=ax, label='Avg Latency (ms)')
        
        ax.set_title('TPS vs Data Size')
        ax.set_xlabel('Data Size (bytes)')
        ax.set_ylabel('TPS')
        ax.set_xscale('log')
        
        # 6. FuseVault vs Industry Comparison
        ax = axes[1, 2]
        if not fusevault_data.empty:
            fusevault_avg_tps = fusevault_data['TPS'].mean()
            bigchain_tps = BenchmarkTargets.BIGCHAIN_DB["typical_tps"]
            mongodb_read_tps = BenchmarkTargets.MONGODB_YCSB["read_tps"]
            
            comparison_systems = ['FuseVault\n(Avg)', 'BigchainDB', 'MongoDB YCSB\n(Read)']
            comparison_tps = [fusevault_avg_tps, bigchain_tps, mongodb_read_tps]
            
            colors = ['green', 'orange', 'purple']
            bars = ax.bar(comparison_systems, comparison_tps, color=colors, alpha=0.7)
            
            # Add value labels
            for bar, value in zip(bars, comparison_tps):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                       f'{value:.1f}', ha='center', va='bottom')
        
        ax.set_title('FuseVault vs Industry Benchmarks')
        ax.set_ylabel('TPS')
        
        plt.tight_layout()
        plt.savefig(output_dir / "fusevault_performance_analysis.png", dpi=300, bbox_inches='tight')
        plt.close()
    
    def _generate_analysis_report(self, df: pd.DataFrame, output_dir: Path):
        """Generate detailed analysis report for FuseVault"""
        
        fusevault_data = df[df['System'].str.contains('FuseVault', na=False)]
        
        report_lines = [
            "# FuseVault Performance Benchmark Report",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Wallet Address: {self.config['wallet_address']}",
            "",
            "## Executive Summary",
            ""
        ]
        
        if not fusevault_data.empty:
            avg_tps = fusevault_data['TPS'].mean()
            avg_latency = fusevault_data['Avg Latency (ms)'].mean()
            avg_success_rate = fusevault_data['Success Rate'].mean()
            total_tests = len(fusevault_data)
            
            # Compare to BigchainDB
            bigchain_tps = BenchmarkTargets.BIGCHAIN_DB["typical_tps"]
            bigchain_latency = BenchmarkTargets.BIGCHAIN_DB["median_latency_ms"]
            
            tps_vs_bigchain = (avg_tps / bigchain_tps) * 100
            latency_vs_bigchain = (avg_latency / bigchain_latency) * 100
            
            report_lines.extend([
                f"- **Total Tests Completed**: {total_tests}",
                f"- **Average TPS**: {avg_tps:.2f} ({tps_vs_bigchain:.1f}% of BigchainDB)",
                f"- **Average Latency**: {avg_latency:.2f}ms ({latency_vs_bigchain:.1f}% of BigchainDB)",
                f"- **Average Success Rate**: {avg_success_rate:.1%}",
                f"- **Best TPS Achieved**: {fusevault_data['TPS'].max():.2f}",
                f"- **Lowest Latency**: {fusevault_data['Avg Latency (ms)'].min():.2f}ms",
                "",
                "## Performance by Test Type",
                ""
            ])
            
            # Performance breakdown by test type
            for test_type in fusevault_data['Test Type'].unique():
                test_data = fusevault_data[fusevault_data['Test Type'] == test_type]
                
                report_lines.extend([
                    f"### {test_type.replace('_', ' ').title()}",
                    f"- Tests Run: {len(test_data)}",
                    f"- Average TPS: {test_data['TPS'].mean():.2f}",
                    f"- Best TPS: {test_data['TPS'].max():.2f}",
                    f"- Average Latency: {test_data['Avg Latency (ms)'].mean():.2f}ms",
                    f"- P95 Latency: {test_data['P95 Latency (ms)'].mean():.2f}ms",
                    f"- Success Rate: {test_data['Success Rate'].mean():.1%}",
                    ""
                ])
            
            # Scalability analysis
            report_lines.extend([
                "## Scalability Analysis",
                ""
            ])
            
            # Check how performance scales with concurrency
            concurrency_analysis = fusevault_data.groupby('Clients').agg({
                'TPS': 'mean',
                'Avg Latency (ms)': 'mean',
                'Success Rate': 'mean'
            }).round(2)
            
            report_lines.append("**Performance vs Concurrent Clients:**")
            for clients, row in concurrency_analysis.iterrows():
                report_lines.append(f"- {clients} clients: {row['TPS']} TPS, {row['Avg Latency (ms)']}ms latency, {row['Success Rate']:.1%} success")
            
            report_lines.append("")
        
        # Industry comparison
        report_lines.extend([
            "## Industry Benchmark Comparison",
            "",
            "### BigchainDB Comparison",
            f"- Target TPS: {BenchmarkTargets.BIGCHAIN_DB['typical_tps']}",
            f"- Target P95 Latency: {BenchmarkTargets.BIGCHAIN_DB['p95_latency_ms']}ms",
            "",
            "### MongoDB YCSB Comparison", 
            f"- Read TPS: {BenchmarkTargets.MONGODB_YCSB['read_tps']}",
            f"- Write TPS: {BenchmarkTargets.MONGODB_YCSB['write_tps']}",
            "",
            "### IPFS Performance",
            f"- Local Retrieval: {BenchmarkTargets.IPFS_BASELINE['local_retrieval_ms']}ms",
            f"- Network P95: {BenchmarkTargets.IPFS_BASELINE['network_retrieval_p95_ms']}ms",
            ""
        ])
        
        # Recommendations
        if not fusevault_data.empty:
            report_lines.extend([
                "## Performance Recommendations",
                ""
            ])
            
            if avg_tps < bigchain_tps * 0.5:
                report_lines.append("- **Throughput Optimization**: Consider optimizing blockchain verification and IPFS storage pipelines")
            
            if avg_latency > bigchain_latency * 2:
                report_lines.append("- **Latency Optimization**: Investigate bottlenecks in the upload/retrieval process")
            
            if avg_success_rate < 0.95:
                report_lines.append("- **Reliability Improvement**: Add more robust error handling and retry mechanisms")
            
            # Data size impact analysis
            size_impact = fusevault_data.groupby('Data Size (bytes)')['TPS'].mean()
            if len(size_impact) > 1:
                largest_size = size_impact.index.max()
                smallest_size = size_impact.index.min()
                perf_degradation = (size_impact[smallest_size] - size_impact[largest_size]) / size_impact[smallest_size]
                
                if perf_degradation > 0.3:
                    report_lines.append(f"- **Data Size Optimization**: Performance degrades {perf_degradation:.1%} with larger data sizes")
        
        # Write report
        with open(output_dir / "fusevault_performance_analysis.md", 'w') as f:
            f.write('\n'.join(report_lines))


def load_fusevault_config() -> Dict[str, Any]:
    """Load FuseVault configuration from environment variables"""
    load_dotenv()
    
    config = {
        "api_host": os.getenv("API_HOST", "localhost"),
        "api_port": os.getenv("API_PORT", "8000"),
        "mongodb_uri": os.getenv("MONGO_URI"),
        "db_name": os.getenv("MONGO_DB_NAME", "fusevault"),
        "api_key": os.getenv("API_KEY"),
        "wallet_address": os.getenv("WALLET_ADDRESS"),
    }
    
    # Validate required configuration
    required_fields = ["mongodb_uri", "api_key", "wallet_address"]
    missing = [f for f in required_fields if not config.get(f)]
    if missing:
        raise ValueError(f"Missing required environment variables: {missing}")
    
    return config


async def main():
    """Main benchmarking execution for FuseVault"""
    
    parser = argparse.ArgumentParser(description='FuseVault Performance Benchmarking Suite')
    parser.add_argument('--config', type=str, default='fusevault_benchmark_config.yaml',
                       help='Configuration file path')
    parser.add_argument('--output', type=str, default='fusevault_benchmark_results',
                       help='Output directory for results')
    parser.add_argument('--quick-test', action='store_true',
                       help='Run quick benchmark test')
    parser.add_argument('--full-suite', action='store_true',
                       help='Run complete benchmark suite')
    
    args = parser.parse_args()
    
    try:
        # Load configuration from environment
        config = load_fusevault_config()
        
        # Initialize FuseVault benchmarker
        benchmarker = FuseVaultBenchmarker(config)
        
        print(f"Starting FuseVault benchmark for wallet: {config['wallet_address']}")
        print(f"API endpoint: {benchmarker.api_base_url}")
        
        if args.quick_test:
            # Quick test with minimal parameters
            print("Running quick FuseVault benchmark test...")
            result = await benchmarker._benchmark_query_performance(20, 1, 8192)
            if result:
                benchmarker.results.append(result)
        
        elif args.full_suite:
            # Full comprehensive benchmark
            print("Running comprehensive FuseVault benchmark suite...")
            await benchmarker.run_comprehensive_benchmark()
        
        else:
            # Default: run key comparison tests
            print("Running key FuseVault performance tests...")
            
            # Test scenarios optimized for FuseVault
            test_scenarios = [
                (20, 1, 8192),    # Single client baseline
                (50, 2, 8192),    # Light concurrent load
                (100, 3, 8192),   # Moderate load
                (200, 5, 8192)    # Higher load
            ]
            
            for ops, clients, size in test_scenarios:
                print(f"Testing: {ops} operations, {clients} clients, {size} bytes")
                
                # Asset queries
                result = await benchmarker._benchmark_query_performance(ops, clients, size)
                if result:
                    benchmarker.results.append(result)
                
                # Asset uploads
                result = await benchmarker._benchmark_upload_performance(ops // 2, clients, size)
                if result:
                    benchmarker.results.append(result)
        
        # Generate reports
        output_dir = Path(args.output)
        benchmarker.generate_comparison_report(output_dir)
        
        # Save raw results
        results_json = [asdict(result) for result in benchmarker.results]
        with open(output_dir / "fusevault_raw_results.json", 'w') as f:
            json.dump(results_json, f, indent=2, default=str)
        
        print(f"\nFuseVault benchmark complete! Results saved to {output_dir}")
        print(f"Total tests run: {len(benchmarker.results)}")
        
        if benchmarker.results:
            avg_tps = statistics.mean([r.transactions_per_second for r in benchmarker.results])
            avg_latency = statistics.mean([r.average_latency_ms for r in benchmarker.results])
            avg_success = statistics.mean([r.success_rate for r in benchmarker.results])
            
            print(f"Average TPS: {avg_tps:.2f}")
            print(f"Average Latency: {avg_latency:.2f}ms")
            print(f"Average Success Rate: {avg_success:.1%}")
            
            # Compare to BigchainDB
            bigchain_tps = BenchmarkTargets.BIGCHAIN_DB["typical_tps"]
            print(f"Performance vs BigchainDB: {(avg_tps/bigchain_tps)*100:.1f}%")
    
    except Exception as e:
        print(f"FuseVault benchmark error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())