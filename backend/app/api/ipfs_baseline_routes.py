from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import asyncio
import time
import statistics
from datetime import datetime

from app.services.ipfs_service import IPFSService
from app.utilities.auth_middleware import get_current_user
from app.utilities.format import format_json, get_ipfs_metadata

router = APIRouter(prefix="/ipfs-baseline", tags=["IPFS Baseline Testing"])

@router.post("/store/single")
async def test_ipfs_baseline_single(
    asset_id: str,
    metadata: Dict[str, Any],
    current_user = Depends(get_current_user)
):
    """
    Test pure IPFS performance for single asset.
    Uses exact same metadata payload as FuseVault but only stores to IPFS.
    """
    ipfs_service = IPFSService()
    start_time = time.time()
    
    try:
        # Store in IPFS using same formatting as FuseVault
        cid = await ipfs_service.store_metadata(metadata)
        total_time = time.time() - start_time
        
        # Calculate metadata size
        formatted_metadata = format_json(get_ipfs_metadata(metadata))
        metadata_size = len(formatted_metadata.encode('utf-8'))
        
        return {
            "success": True,
            "asset_id": asset_id,
            "cid": cid,
            "metadata_size_bytes": metadata_size,
            "performance": {
                "total_time": total_time,
                "throughput_mb_per_sec": (metadata_size / 1024 / 1024) / total_time if total_time > 0 else 0
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "total_time": time.time() - start_time
        }

@router.post("/store/batch")
async def test_ipfs_baseline_batch(
    assets: List[Dict[str, Any]],
    current_user = Depends(get_current_user)
):
    """
    Test pure IPFS performance for batch assets.
    Format: [{"asset_id": "...", "metadata": {...}}, ...]
    """
    if len(assets) > 50:
        raise HTTPException(status_code=400, detail="Batch size cannot exceed 50")
    
    ipfs_service = IPFSService()
    start_time = time.time()
    batch_size = len(assets)
    
    try:
        results = []
        total_size = 0
        
        # Store each asset in IPFS
        for asset in assets:
            asset_id = asset["asset_id"]
            metadata = asset["metadata"]
            
            asset_start = time.time()
            cid = await ipfs_service.store_metadata(metadata)
            asset_time = time.time() - asset_start
            
            # Calculate size
            formatted_metadata = format_json(get_ipfs_metadata(metadata))
            metadata_size = len(formatted_metadata.encode('utf-8'))
            total_size += metadata_size
            
            results.append({
                "asset_id": asset_id,
                "cid": cid,
                "time": asset_time,
                "size_bytes": metadata_size
            })
        
        total_time = time.time() - start_time
        
        return {
            "success": True,
            "batch_size": batch_size,
            "results": results,
            "performance": {
                "total_time": total_time,
                "avg_time_per_asset": total_time / batch_size,
                "throughput_assets_per_sec": batch_size / total_time,
                "total_size_bytes": total_size,
                "avg_size_per_asset": total_size / batch_size,
                "throughput_mb_per_sec": (total_size / 1024 / 1024) / total_time if total_time > 0 else 0
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "total_time": time.time() - start_time,
            "batch_size": batch_size
        }

@router.post("/retrieve/{cid}")
async def test_ipfs_baseline_retrieve(
    cid: str,
    current_user = Depends(get_current_user)
):
    """
    Test pure IPFS retrieval performance.
    """
    ipfs_service = IPFSService()
    start_time = time.time()
    
    try:
        metadata = await ipfs_service.retrieve_metadata(cid)
        total_time = time.time() - start_time
        
        # Calculate retrieved data size
        metadata_size = len(str(metadata).encode('utf-8'))
        
        return {
            "success": True,
            "cid": cid,
            "metadata": metadata,
            "retrieved_size_bytes": metadata_size,
            "performance": {
                "retrieval_time": total_time,
                "throughput_mb_per_sec": (metadata_size / 1024 / 1024) / total_time if total_time > 0 else 0
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "total_time": time.time() - start_time
        }

@router.post("/stress-test/concurrent")
async def stress_test_ipfs_concurrent(
    base_asset_id: str,
    metadata: Dict[str, Any],
    concurrent_requests: int = 5,
    current_user = Depends(get_current_user)
):
    """
    Stress test: Run multiple concurrent IPFS-only requests.
    """
    if concurrent_requests > 20:
        raise HTTPException(status_code=400, detail="Max 20 concurrent requests")
    
    ipfs_service = IPFSService()
    
    async def single_test(index: int):
        try:
            start_time = time.time()
            cid = await ipfs_service.store_metadata(metadata)
            total_time = time.time() - start_time
            
            # Calculate size
            formatted_metadata = format_json(get_ipfs_metadata(metadata))
            metadata_size = len(formatted_metadata.encode('utf-8'))
            
            return {
                "success": True,
                "asset_id": f"{base_asset_id}_{index}",
                "cid": cid,
                "time": total_time,
                "size_bytes": metadata_size
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "time": time.time() - start_time
            }
    
    start_time = time.time()
    
    # Run concurrent tests
    tasks = [single_test(i) for i in range(concurrent_requests)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    total_time = time.time() - start_time
    
    # Analyze results
    successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
    failed_results = [r for r in results if not (isinstance(r, dict) and r.get("success"))]
    
    if successful_results:
        times = [r["time"] for r in successful_results]
        sizes = [r["size_bytes"] for r in successful_results]
        total_size = sum(sizes)
        
        performance_stats = {
            "success_rate": len(successful_results) / concurrent_requests,
            "avg_time": statistics.mean(times),
            "median_time": statistics.median(times),
            "min_time": min(times),
            "max_time": max(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
            "total_throughput_assets_per_sec": concurrent_requests / total_time,
            "total_throughput_mb_per_sec": (total_size / 1024 / 1024) / total_time if total_time > 0 else 0,
            "avg_size_bytes": statistics.mean(sizes)
        }
    else:
        performance_stats = {"success_rate": 0}
    
    return {
        "test_config": {
            "concurrent_requests": concurrent_requests,
            "total_test_time": total_time,
            "metadata_size_bytes": len(str(metadata).encode('utf-8'))
        },
        "results": {
            "successful": len(successful_results),
            "failed": len(failed_results),
            "success_rate_percent": (len(successful_results) / concurrent_requests) * 100
        },
        "performance": performance_stats,
        "detailed_results": results[:10]  # First 10 for inspection
    }