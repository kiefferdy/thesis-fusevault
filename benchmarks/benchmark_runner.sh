# FuseVault Benchmark Runner Script for Windows PowerShell
# This script provides easy ways to run different benchmark scenarios for FuseVault

param(
    [Parameter(Position=0)]
    [string]$Action = "help"
)

$ErrorActionPreference = "Stop"

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$BENCHMARK_SCRIPT = Join-Path $SCRIPT_DIR "fusevault_benchmark_suite.py"
$CONFIG_FILE = Join-Path $SCRIPT_DIR "fusevault_benchmark_config.yaml"
$ENV_FILE = Join-Path $SCRIPT_DIR ".env"
$RESULTS_DIR = Join-Path $SCRIPT_DIR "fusevault_benchmark_results"

function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    } else {
        $input | Write-Output
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

function Print-Usage {
    Write-Host "Usage: .\fusevault_benchmark.ps1 [OPTION]" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  setup      Initial setup and environment configuration"
    Write-Host "  validate   Validate FuseVault system setup and configuration"
    Write-Host "  quick      Run quick benchmark test (development)"
    Write-Host "  compare    Run comparison against industry benchmarks"
    Write-Host "  full       Run comprehensive benchmark suite"
    Write-Host "  stress     Run stress test with high concurrency"
    Write-Host "  analyze    Re-analyze existing results"
    Write-Host "  clean      Clean previous results"
    Write-Host "  help       Show this help message"
    Write-Host ""
}

function Setup-Environment {
    Write-ColorOutput Blue "Setting up FuseVault benchmark environment..."
    
    # Check if .env exists
    if (-not (Test-Path $ENV_FILE)) {
        Write-ColorOutput Yellow "Creating FuseVault .env file template"
        
        $envContent = @"
# FuseVault Benchmark Configuration
# Copy your actual FuseVault .env values here

# API Configuration
API_HOST=localhost
API_PORT=8000

# Database Configuration
MONGO_URI=mongodb+srv://admin:admin@fusevault.4viqu.mongodb.net/?retryWrites=true&w=majority&appName=Fusevault
MONGO_DB_NAME=fusevault

# Authentication (REQUIRED)
# Get your API key from FuseVault dashboard or create one via the API
API_KEY=fv.v1.your_api_key_here

# Wallet Configuration (REQUIRED)
# The wallet address that owns the test assets
WALLET_ADDRESS=0x1234567890123456789012345678901234567890

# Optional: Blockchain Configuration
CONTRACT_ADDRESS=0x847eaE769bF06F99c5D848390C727803f049F745
ALCHEMY_SEPOLIA_URL=https://eth-sepolia.g.alchemy.com/v2/your_alchemy_key

# Benchmark Limits
BENCHMARK_MAX_OPERATIONS=500
BENCHMARK_MAX_CLIENTS=10
BENCHMARK_QUICK_MODE=true

# Test Configuration
TEST_DATA_PREFIX=fusevault_benchmark_
TEST_CLEANUP_AFTER_RUN=false
"@
        
        Set-Content -Path $ENV_FILE -Value $envContent
        Write-ColorOutput Green ".env file created"
        Write-ColorOutput Yellow "IMPORTANT: Please edit .env with your actual FuseVault configuration before running benchmarks"
        Write-ColorOutput Yellow "You need to set API_KEY and WALLET_ADDRESS"
    } else {
        Write-ColorOutput Green ".env file already exists"
    }
    
    # Check Python dependencies
    Write-ColorOutput Blue "Checking Python dependencies..."
    
    try {
        python -c "import aiohttp, pandas, matplotlib, pymongo, yaml, dotenv, numpy, seaborn" 2>$null
        Write-ColorOutput Green "All dependencies are installed"
    } catch {
        Write-ColorOutput Yellow "Installing Python dependencies..."
        
        $requirementsPath = Join-Path $SCRIPT_DIR "fusevault_benchmark_requirements.txt"
        if (Test-Path $requirementsPath) {
            pip install -r $requirementsPath
        } else {
            pip install aiohttp pandas matplotlib pymongo pyyaml python-dotenv numpy seaborn
        }
    }
    
    # Create default config if it doesn't exist
    if (-not (Test-Path $CONFIG_FILE)) {
        Write-ColorOutput Yellow "Config file not found, will be created on first run"
    }
    
    Write-ColorOutput Green "Setup complete!"
    Write-ColorOutput Yellow "Next steps:"
    Write-Host "1. Edit .env file with your FuseVault configuration"
    Write-Host "2. Make sure your FuseVault backend is running"
    Write-Host "3. Run '.\fusevault_benchmark.ps1 validate' to test connectivity"
}

function Load-EnvVars {
    if (Test-Path $ENV_FILE) {
        # Load environment variables from .env file
        Get-Content $ENV_FILE | Where-Object { $_ -notmatch "^#" -and $_ -match "=" } | ForEach-Object {
            $key, $value = $_ -split "=", 2
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
        Write-ColorOutput Green "Loaded environment from .env"
    } else {
        Write-ColorOutput Red ".env file not found. Run '.\fusevault_benchmark.ps1 setup' first."
        exit 1
    }
}

function Validate-Setup {
    Write-ColorOutput Blue "Validating FuseVault setup..."
    
    # Load environment variables
    Load-EnvVars
    
    # Check required environment variables
    $apiKey = [Environment]::GetEnvironmentVariable("API_KEY", "Process")
    $walletAddress = [Environment]::GetEnvironmentVariable("WALLET_ADDRESS", "Process")
    
    if (-not $apiKey -or $apiKey -eq "fv.v1.your_api_key_here") {
        Write-ColorOutput Red "API_KEY not set or using default value in .env"
        Write-ColorOutput Yellow "Please set a valid FuseVault API key"
        exit 1
    }
    
    if (-not $walletAddress -or $walletAddress -eq "0x1234567890123456789012345678901234567890") {
        Write-ColorOutput Red "WALLET_ADDRESS not set or using default value in .env"
        Write-ColorOutput Yellow "Please set a valid wallet address"
        exit 1
    }
    
    # Check Python dependencies
    try {
        python -c "import aiohttp, pandas, matplotlib, pymongo, yaml, dotenv, numpy, seaborn" 2>$null
        Write-ColorOutput Green "All Python dependencies are installed"
    } catch {
        Write-ColorOutput Red "Missing Python dependencies. Install with:"
        Write-Host "pip install aiohttp pandas matplotlib pymongo pyyaml python-dotenv numpy seaborn"
        exit 1
    }
    
    # Test FuseVault API connectivity
    $apiHost = [Environment]::GetEnvironmentVariable("API_HOST", "Process")
    $apiPort = [Environment]::GetEnvironmentVariable("API_PORT", "Process")
    
    if ($apiHost -and $apiPort) {
        Write-ColorOutput Blue "Testing FuseVault API connectivity..."
        
        # Test basic connectivity
        try {
            $response = Invoke-WebRequest -Uri "http://$apiHost`:$apiPort/docs" -TimeoutSec 10 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                Write-ColorOutput Green "✓ FuseVault API is responding at http://$apiHost`:$apiPort"
            }
        } catch {
            Write-ColorOutput Yellow "⚠ FuseVault API not responding at http://$apiHost`:$apiPort"
            Write-Host "Make sure your FuseVault backend is running"
        }
        
        # Test API key authentication
        Write-ColorOutput Blue "Testing API key authentication..."
        try {
            $headers = @{"X-API-Key" = $apiKey}
            $response = Invoke-WebRequest -Uri "http://$apiHost`:$apiPort/api/assets/user/$walletAddress" -Headers $headers -TimeoutSec 10 -UseBasicParsing
            
            if ($response.StatusCode -eq 200) {
                Write-ColorOutput Green "✓ API key authentication successful"
            }
        } catch {
            $statusCode = $_.Exception.Response.StatusCode.value__
            Write-ColorOutput Yellow "⚠ API key authentication failed (HTTP $statusCode)"
            Write-Host "Please check your API key and wallet address"
        }
    } else {
        Write-ColorOutput Red "API_HOST or API_PORT not set in .env"
        exit 1
    }
    
    # Test MongoDB connectivity
    $mongoUri = [Environment]::GetEnvironmentVariable("MONGO_URI", "Process")
    if ($mongoUri) {
        Write-ColorOutput Blue "Testing MongoDB connectivity..."
        
        $testScript = @"
import os
from pymongo import MongoClient
try:
    client = MongoClient(os.getenv('MONGO_URI'))
    client.admin.command('ping')
    print('✓ MongoDB connectivity confirmed')
except Exception as e:
    print(f'⚠ MongoDB connection failed: {e}')
"@
        
        python -c $testScript
    } else {
        Write-ColorOutput Red "MONGO_URI not set in .env"
        exit 1
    }
    
    # Check if assets exist for testing
    Write-ColorOutput Blue "Checking for test assets..."
    
    $assetCheckScript = @"
import os
from pymongo import MongoClient
try:
    client = MongoClient(os.getenv('MONGO_URI'))
    db = client[os.getenv('MONGO_DB_NAME', 'fusevault')]
    count = db.assets.count_documents({
        'walletAddress': os.getenv('WALLET_ADDRESS'),
        'isCurrent': True,
        'isDeleted': False
    })
    print(count)
except:
    print(0)
"@
    
    $assetCount = python -c $assetCheckScript
    
    if ([int]$assetCount -gt 0) {
        Write-ColorOutput Green "✓ Found $assetCount assets for testing"
    } else {
        Write-ColorOutput Yellow "⚠ No assets found for wallet $walletAddress"
        Write-ColorOutput Yellow "You may want to create some test assets first"
    }
    
    Write-ColorOutput Green "Setup validation complete"
}

function Run-QuickTest {
    Write-ColorOutput Blue "Running quick FuseVault benchmark test..."
    Load-EnvVars
    
    python $BENCHMARK_SCRIPT --config $CONFIG_FILE --output "$RESULTS_DIR\quick" --quick-test
}

function Run-Comparison {
    Write-ColorOutput Blue "Running FuseVault vs industry benchmark comparison..."
    Load-EnvVars
    
    python $BENCHMARK_SCRIPT --config $CONFIG_FILE --output "$RESULTS_DIR\comparison"
}

function Run-FullSuite {
    Write-ColorOutput Blue "Running comprehensive FuseVault benchmark suite..."
    Write-ColorOutput Yellow "This may take 30-60 minutes depending on your system"
    Load-EnvVars
    
    python $BENCHMARK_SCRIPT --config $CONFIG_FILE --output "$RESULTS_DIR\full_suite" --full-suite
}

function Run-StressTest {
    Write-ColorOutput Blue "Running stress test with high concurrency..."
    Load-EnvVars
    
    # Set environment variables for stress testing
    [Environment]::SetEnvironmentVariable("BENCHMARK_MAX_OPERATIONS", "1000", "Process")
    [Environment]::SetEnvironmentVariable("BENCHMARK_MAX_CLIENTS", "20", "Process")
    
    Write-ColorOutput Yellow "Stress test configuration:"
    Write-Host "Max Operations: 1000"
    Write-Host "Max Clients: 20"
    
    python $BENCHMARK_SCRIPT --config $CONFIG_FILE --output "$RESULTS_DIR\stress_test"
}

function Analyze-Results {
    Write-ColorOutput Blue "Analyzing existing FuseVault benchmark results..."
    
    if (-not (Test-Path $RESULTS_DIR)) {
        Write-ColorOutput Red "No results directory found"
        exit 1
    }
    
    # Find most recent results
    $latestResults = Get-ChildItem -Path $RESULTS_DIR -Recurse -Name "fusevault_raw_results.json" | 
                    ForEach-Object { Join-Path $RESULTS_DIR $_ } |
                    Sort-Object { (Get-Item $_).LastWriteTime } -Descending |
                    Select-Object -First 1
    
    if (-not $latestResults) {
        Write-ColorOutput Red "No FuseVault results found to analyze"
        exit 1
    }
    
    $resultsPath = Split-Path -Parent $latestResults
    Write-ColorOutput Green "Analyzing results from: $resultsPath"
    
    # Show summary
    Write-ColorOutput Yellow "FuseVault Benchmark Summary:"
    
    $summaryScript = @"
import json, statistics
try:
    with open('$($latestResults.Replace('\', '/'))') as f:
        results = json.load(f)
    if results:
        tps_values = [r['transactions_per_second'] for r in results]
        latency_values = [r['average_latency_ms'] for r in results]
        print(f'Tests run: {len(results)}')
        print(f'Average TPS: {statistics.mean(tps_values):.2f}')
        print(f'Average Latency: {statistics.mean(latency_values):.2f}ms')
        print(f'Max TPS: {max(tps_values):.2f}')
        print(f'Min Latency: {min(latency_values):.2f}ms')
        
        # Show comparison to BigchainDB
        bigchain_tps = 298
        comparison = (statistics.mean(tps_values) / bigchain_tps) * 100
        print(f'Performance vs BigchainDB: {comparison:.1f}%')
    else:
        print('No results found in file')
except Exception as e:
    print(f'Error analyzing results: {e}')
"@
    
    python -c $summaryScript
    
    # Check for generated reports
    $analysisReport = Join-Path $resultsPath "fusevault_performance_analysis.md"
    $performanceChart = Join-Path $resultsPath "fusevault_performance_comparison.png"
    
    if (Test-Path $analysisReport) {
        Write-ColorOutput Green "✓ Performance analysis report available"
        Write-Host "View: $analysisReport"
    }
    
    if (Test-Path $performanceChart) {
        Write-ColorOutput Green "✓ Performance charts available"
        Write-Host "View: $performanceChart"
    }
}

function Clean-Results {
    Write-ColorOutput Yellow "Cleaning previous FuseVault benchmark results..."
    if (Test-Path $RESULTS_DIR) {
        Remove-Item -Path $RESULTS_DIR -Recurse -Force
        Write-ColorOutput Green "Results cleaned"
    } else {
        Write-ColorOutput Blue "No results to clean"
    }
}

# Main script logic
switch ($Action.ToLower()) {
    "setup" {
        Setup-Environment
    }
    "validate" {
        Validate-Setup
    }
    "quick" {
        Validate-Setup
        Run-QuickTest
    }
    "compare" {
        Validate-Setup
        Run-Comparison
    }
    "full" {
        Validate-Setup
        Run-FullSuite
    }
    "stress" {
        Validate-Setup
        Run-StressTest
    }
    "analyze" {
        Analyze-Results
    }
    "clean" {
        Clean-Results
    }
    default {
        Print-Usage
    }
}

Write-ColorOutput Green "FuseVault benchmark operation completed!"