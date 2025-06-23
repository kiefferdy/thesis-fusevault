# 🚀 FuseVault Benchmark - Quick Start

## Prerequisites

- Windows 10/11
- Python 3.7+
- FuseVault backend running on `localhost:8000`

## 1. Setup (One-Time)

```powershell
# Create virtual environment
python -m venv fusevault_benchmark_env
fusevault_benchmark_env\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Allow PowerShell scripts
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 2. Configure

Create `.env` file:

```bash
API_HOST=localhost
API_PORT=8000
MONGO_URI=your_mongodb_connection_string
MONGO_DB_NAME=fusevault
API_KEY=your_fusevault_api_key
WALLET_ADDRESS=your_wallet_address
```

## 3. Run Benchmarks

### Quick Test (2-3 minutes)

```powershell
.\fusevault_benchmark.ps1 quick
```

### Industry Comparison (10-15 minutes)

```powershell
.\fusevault_benchmark.ps1 compare
```

### Full Suite (30-60 minutes)

```powershell
.\fusevault_benchmark.ps1 full
```

### YCSB Standard Tests

```powershell
python fusevault_ycsb_adapter.py
```

## 4. Check Results

```powershell
# Open results folder
explorer fusevault_benchmark_results

# View performance report
notepad fusevault_benchmark_results\quick\fusevault_performance_analysis.md
```

## Alternative (If PowerShell Issues)

```powershell
# Direct Python commands
python fusevault_benchmark_suite.py --quick-test --output "results"
python fusevault_results_analyzer.py results\
```

## Troubleshooting

### Validate Setup

```powershell
python fusevault_validator.py
```

### If Dependencies Fail

```powershell
# Use minimal version (no charts)
python fusevault_benchmark_minimal.py --quick-test
```

### Clean & Retry

```powershell
.\fusevault_benchmark.ps1 clean
.\fusevault_benchmark.ps1 quick
```

## What You Get

- **Performance metrics**: TPS, latency, success rates
- **Industry comparisons**: vs BigchainDB, MongoDB, IPFS
- **Visual charts**: Performance graphs and analysis
- **Detailed reports**: Executive summaries and recommendations

## Expected Results

- **MongoDB queries**: 50-200 TPS
- **Full stack operations**: 5-50 TPS
- **API retrieval**: 20-100 TPS
- **vs BigchainDB**: 10-50% performance (normal for blockchain systems)

---

**That's it! Start with `.\fusevault_benchmark.ps1 quick` and you'll have results in 2-3 minutes.** 🎯
