from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
import asyncio
import time
import statistics
from datetime import datetime

from app.services.baseline_service import BaselineService
from app.services.asset_service import AssetService
from app.utilities.auth_middleware import get_current_user

router = APIRouter(prefix="/performance", tags=["Performance Testing"])

@router.post("/baseline/single")
async def test_baseline_single(
    asset_id: str,
    metadata: Dict[str, Any],
    current_user = Depends(get_current_user)
):
    """
    Test baseline IPFS + Ethereum performance for single asset.
    Uses exact same metadata payload as FuseVault.
    """
    baseline_service = BaselineService()
    result = await baseline_service.baseline_store_single(asset_id, metadata)
    return result

@router.post("/baseline/batch")
async def test_baseline_batch(
    assets: List[Dict[str, Any]],
    current_user = Depends(get_current_user)
):
    """
    Test baseline IPFS + Ethereum performance for batch assets.
    Format: [{"asset_id": "...", "metadata": {...}}, ...]
    """
    if len(assets) > 50:
        raise HTTPException(status_code=400, detail="Batch size cannot exceed 50")
    
    baseline_service = BaselineService()
    result = await baseline_service.baseline_store_batch(assets)
    return result

@router.post("/comparison/single")
async def compare_fusevault_vs_baseline(
    asset_id: str,
    wallet_address: str,
    critical_metadata: Dict[str, Any],
    non_critical_metadata: Dict[str, Any] = None,
    current_user = Depends(get_current_user)
):
    """
    Compare FuseVault vs Baseline performance for single asset using identical data.
    """
    # Prepare metadata in FuseVault format
    fusevault_metadata = {
        "critical_metadata": critical_metadata,
        "non_critical_metadata": non_critical_metadata or {}
    }
    
    # Prepare metadata in baseline format (IPFS-only portion)
    baseline_metadata = critical_metadata  # Baseline only stores critical metadata
    
    # Run both tests concurrently
    baseline_service = BaselineService()
    asset_service = AssetService()
    
    start_time = time.time()
    
    # Test baseline
    baseline_result = await baseline_service.baseline_store_single(
        f"{asset_id}_baseline", 
        baseline_metadata
    )
    
    # Test FuseVault (simplified - you'd need to adapt based on your auth setup)
    try:
        fusevault_result = await asset_service.create_asset(
            asset_id=f"{asset_id}_fusevault",
            wallet_address=wallet_address,
            critical_metadata=critical_metadata,
            non_critical_metadata=non_critical_metadata
        )
        fusevault_success = True
        fusevault_time = fusevault_result.get("total_time", 0)
    except Exception as e:
        fusevault_success = False
        fusevault_result = {"error": str(e)}
        fusevault_time = time.time() - start_time
    
    return {
        "comparison_timestamp": datetime.utcnow().isoformat(),
        "test_asset_id": asset_id,
        "metadata_size_bytes": len(str(critical_metadata).encode('utf-8')),
        "baseline": {
            "success": baseline_result.get("success", False),
            "performance": baseline_result.get("performance", {}),
            "gas_used": baseline_result.get("gas_used", 0),
            "result": baseline_result
        },
        "fusevault": {
            "success": fusevault_success,
            "total_time": fusevault_time,
            "result": fusevault_result
        },
        "comparison": {
            "baseline_faster": baseline_result.get("performance", {}).get("total_time", float('inf')) < fusevault_time,
            "time_difference": abs(baseline_result.get("performance", {}).get("total_time", 0) - fusevault_time),
            "baseline_gas": baseline_result.get("gas_used", 0),
            # FuseVault gas would need to be extracted from your service
        }
    }

@router.post("/stress-test/concurrent")
async def stress_test_concurrent(
    base_asset_id: str,
    metadata: Dict[str, Any],
    concurrent_requests: int = 5,
    current_user = Depends(get_current_user)
):
    """
    Stress test: Run multiple concurrent baseline requests.
    """
    if concurrent_requests > 10:
        raise HTTPException(status_code=400, detail="Max 10 concurrent requests")
    
    baseline_service = BaselineService()
    
    async def single_test(index: int):
        return await baseline_service.baseline_store_single(
            f"{base_asset_id}_{index}",
            metadata
        )
    
    start_time = time.time()
    
    # Run concurrent tests
    tasks = [single_test(i) for i in range(concurrent_requests)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    total_time = time.time() - start_time
    
    # Analyze results
    successful_results = [r for r in results if isinstance(r, dict) and r.get("success")]
    failed_results = [r for r in results if not (isinstance(r, dict) and r.get("success"))]
    
    if successful_results:
        times = [r["performance"]["total_time"] for r in successful_results]
        gas_usage = [r["gas_used"] for r in successful_results]
        
        performance_stats = {
            "success_rate": len(successful_results) / concurrent_requests,
            "avg_time": statistics.mean(times),
            "median_time": statistics.median(times),
            "min_time": min(times),
            "max_time": max(times),
            "std_dev": statistics.stdev(times) if len(times) > 1 else 0,
            "avg_gas": statistics.mean(gas_usage),
            "total_throughput": concurrent_requests / total_time
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
        "detailed_results": results[:5]  # First 5 for inspection
    }

@router.get("/baseline/retrieve/{asset_id}")
async def test_baseline_retrieval(
    asset_id: str,
    current_user = Depends(get_current_user)
):
    """
    Test baseline retrieval performance.
    """
    baseline_service = BaselineService()
    result = await baseline_service.baseline_retrieve(asset_id)
    return result