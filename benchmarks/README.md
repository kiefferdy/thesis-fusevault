# FuseVault Benchmark - How to Run

_Assumes FuseVault backend is already running on `localhost:8000`_

## Prerequisites

- Windows 10/11 with PowerShell
- Python 3.7+
- FuseVault backend running on `localhost:8000`

## Quick Setup

1. **Create virtual environment:**

   ```powershell
   python -m venv fusevault_benchmark_env
   fusevault_benchmark_env\Scripts\activate
   ```

2. **Install dependencies:**

   ```powershell
   pip install -r requirements.txt
   ```

3. **Enable PowerShell scripts:**

   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

4. **Configure environment:**

   ```powershell
   .\fusevault_benchmark.ps1 setup
   ```

5. **Edit `.env` file with your FuseVault credentials:**
   ```
   API_HOST=localhost
   API_PORT=8000
   MONGO_URI=your_mongodb_connection_string
   MONGO_DB_NAME=fusevault
   API_KEY=your_fusevault_api_key
   WALLET_ADDRESS=your_wallet_address
   ```

## Running Benchmarks

### Quick Test (2-3 minutes)

```powershell
.\fusevault_benchmark.ps1 quick
```

### Industry Comparison (10-15 minutes)

```powershell
.\fusevault_benchmark.ps1 compare
```

### Full Benchmark Suite (30-60 minutes)

```powershell
.\fusevault_benchmark.ps1 full
```

### Stress Test

```powershell
.\fusevault_benchmark.ps1 stress
```

## Alternative Methods

### If PowerShell Issues

```powershell
# Direct Python commands
python fusevault_benchmark_suite.py --quick-test --output "results"
python fusevault_results_analyzer.py results\
```

### YCSB Standard Tests

```powershell
python fusevault_ycsb_adapter.py
```

## Troubleshooting

### Validate Setup

```powershell
.\fusevault_benchmark.ps1 validate
```

### Clean and Retry

```powershell
.\fusevault_benchmark.ps1 clean
.\fusevault_benchmark.ps1 quick
```

### If Dependencies Fail

```powershell
# Use minimal version (no charts)
python fusevault_benchmark_minimal.py --quick-test
```

## Viewing Results

### Open Results Folder

```powershell
explorer fusevault_benchmark_results
```

### View Performance Report

```powershell
notepad fusevault_benchmark_results\quick\fusevault_performance_analysis.md
```

### Re-analyze Existing Results

```powershell
.\fusevault_benchmark.ps1 analyze
```

## What You Get

- **Performance Metrics**: TPS, latency, success rates
- **Industry Comparisons**: vs BigchainDB, MongoDB, IPFS
- **Visual Charts**: Performance graphs and analysis
- **Detailed Reports**: Executive summaries and recommendations

## Expected Performance Results

- **MongoDB Queries**: 50-200 TPS
- **Full Stack Operations**: 5-50 TPS
- **API Retrieval**: 20-100 TPS
- **vs BigchainDB**: 10-50% performance (normal for blockchain systems)