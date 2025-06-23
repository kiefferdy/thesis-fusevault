"""
FuseVault System Validator with Enhanced Debugging
Quick validation script to test FuseVault system health before running benchmarks

Usage:
    python fusevault_validator_debug.py
    python fusevault_validator_debug.py --debug
"""

import argparse
import asyncio
import json
import os
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

import aiohttp
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()


class FuseVaultValidatorDebug:
    """Enhanced validator with debugging capabilities"""
    
    def __init__(self, debug=False):
        self.debug = debug
        self.config = self._load_config()
        self.api_base_url = f"http://{self.config['api_host']}:{self.config['api_port']}"
        self.api_url = f"{self.api_base_url}/api"
        self.results = []
    
    def _load_config(self) -> Dict[str, str]:
        """Load configuration from environment variables"""
        
        config = {
            "api_host": os.getenv("API_HOST", "localhost"),
            "api_port": os.getenv("API_PORT", "8000"),
            "mongodb_uri": os.getenv("MONGO_URI"),
            "db_name": os.getenv("MONGO_DB_NAME", "fusevault"),
            "api_key": os.getenv("API_KEY"),
            "wallet_address": os.getenv("WALLET_ADDRESS"),
        }
        
        return config
    
    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers"""
        headers = {"Content-Type": "application/json"}
        
        if self.config.get("api_key"):
            headers["X-API-Key"] = self.config["api_key"]
        
        return headers
    
    def _log_result(self, test_name: str, success: bool, message: str, details: Optional[Dict] = None):
        """Log a validation result"""
        
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        
        self.results.append(result)
        
        status = "✅" if success else "❌"
        print(f"{status} {test_name}: {message}")
        
        if details and (not success or self.debug):
            for key, value in details.items():
                print(f"   {key}: {value}")
    
    def debug_api_endpoints(self) -> bool:
        """Debug API endpoints to find the correct paths"""
        
        print("\n🔍 Debugging API Endpoints...")
        
        # Test various common paths
        test_paths = [
            "/docs",
            "/api/docs", 
            "/assets/user/" + self.config["wallet_address"],
            "/api/assets/user/" + self.config["wallet_address"],
            "/v1/assets/user/" + self.config["wallet_address"],
            "/api/v1/assets/user/" + self.config["wallet_address"]
        ]
        
        working_paths = []
        
        for path in test_paths:
            url = f"{self.api_base_url}{path}"
            
            try:
                if path.endswith("/docs") or path.endswith("/api/docs"):
                    # Test docs without auth
                    response = requests.get(url, timeout=5)
                else:
                    # Test API endpoints with auth
                    response = requests.get(url, headers=self._get_auth_headers(), timeout=5)
                
                status_color = "🟢" if response.status_code < 400 else "🔴"
                print(f"   {status_color} {path} → HTTP {response.status_code}")
                
                if response.status_code < 400:
                    working_paths.append(path)
                    
                if self.debug and response.status_code >= 400:
                    print(f"      Response: {response.text[:200]}")
                    
            except Exception as e:
                print(f"   🔴 {path} → Error: {str(e)[:100]}")
        
        if working_paths:
            print(f"\n✅ Working paths found: {working_paths}")
            return True
        else:
            print(f"\n❌ No working API paths found")
            return False
    
    def test_api_structure(self) -> Dict[str, Any]:
        """Test API structure to understand the available endpoints"""
        
        print("\n🏗️ Testing API Structure...")
        
        structure_info = {
            "base_url": self.api_base_url,
            "docs_available": False,
            "openapi_spec": None,
            "working_endpoints": []
        }
        
        # Test docs endpoint
        try:
            response = requests.get(f"{self.api_base_url}/docs", timeout=5)
            if response.status_code == 200:
                structure_info["docs_available"] = True
                print("   ✅ API docs available at /docs")
        except:
            pass
        
        # Test OpenAPI spec
        try:
            response = requests.get(f"{self.api_base_url}/openapi.json", timeout=5)
            if response.status_code == 200:
                spec = response.json()
                structure_info["openapi_spec"] = spec
                
                # Extract available paths
                if "paths" in spec:
                    paths = list(spec["paths"].keys())
                    print(f"   📋 Available API paths:")
                    for path in sorted(paths)[:10]:  # Show first 10
                        print(f"      - {path}")
                    if len(paths) > 10:
                        print(f"      ... and {len(paths) - 10} more")
                        
        except Exception as e:
            print(f"   ⚠️ Could not get OpenAPI spec: {e}")
        
        return structure_info
    
    def validate_configuration(self) -> bool:
        """Validate basic configuration"""
        
        print("🔧 Validating Configuration...")
        
        # Check required environment variables
        required_vars = ["api_key", "wallet_address", "mongodb_uri"]
        missing_vars = []
        
        for var in required_vars:
            if not self.config.get(var):
                missing_vars.append(var.upper())
        
        if missing_vars:
            self._log_result(
                "Configuration Check",
                False,
                f"Missing required environment variables: {', '.join(missing_vars)}",
                {"missing_variables": missing_vars}
            )
            return False
        
        # Validate API key format
        api_key = self.config["api_key"]
        if not api_key.startswith("fv.v1."):
            self._log_result(
                "API Key Format",
                False,
                "API key should start with 'fv.v1.'",
                {"provided_key_prefix": api_key[:10] + "..."}
            )
            return False
        
        # Validate wallet address format
        wallet = self.config["wallet_address"]
        if not (wallet.startswith("0x") and len(wallet) == 42):
            self._log_result(
                "Wallet Address Format",
                False,
                "Wallet address should be 42 characters starting with '0x'",
                {"provided_format": f"{wallet[:10]}... (length: {len(wallet)})"}
            )
            return False
        
        self._log_result(
            "Configuration Check",
            True,
            "All required configuration present and valid"
        )
        
        return True
    
    def validate_api_connectivity(self) -> bool:
        """Test basic API connectivity with enhanced debugging"""
        
        print("\n🌐 Testing API Connectivity...")
        
        # Test basic connectivity
        try:
            response = requests.get(f"{self.api_base_url}/docs", timeout=10)
            if response.status_code == 200:
                self._log_result(
                    "API Server",
                    True,
                    f"FuseVault API server responding at {self.api_base_url}"
                )
            else:
                self._log_result(
                    "API Server",
                    False,
                    f"API server returned status {response.status_code}",
                    {"status_code": response.status_code, "url": self.api_base_url}
                )
                return False
        except requests.exceptions.RequestException as e:
            self._log_result(
                "API Server",
                False,
                "Could not connect to FuseVault API server",
                {"error": str(e), "url": self.api_base_url}
            )
            return False
        
        # Debug API structure if debug mode is on
        if self.debug:
            api_structure = self.test_api_structure()
            self.debug_api_endpoints()
        
        # Test API key authentication - try multiple possible paths
        auth_endpoints_to_try = [
            f"/api/assets/user/{self.config['wallet_address']}",
            f"/assets/user/{self.config['wallet_address']}",
            f"/api/v1/assets/user/{self.config['wallet_address']}"
        ]
        
        auth_success = False
        working_endpoint = None
        
        for endpoint in auth_endpoints_to_try:
            try:
                url = f"{self.api_base_url}{endpoint}"
                response = requests.get(
                    url,
                    headers=self._get_auth_headers(),
                    timeout=10
                )
                
                if self.debug:
                    print(f"   Testing {endpoint} → HTTP {response.status_code}")
                
                if response.status_code == 200:
                    auth_success = True
                    working_endpoint = endpoint
                    break
                elif response.status_code == 401:
                    # 401 means endpoint exists but auth failed
                    working_endpoint = endpoint
                    break
                    
            except requests.exceptions.RequestException as e:
                if self.debug:
                    print(f"   Testing {endpoint} → Error: {e}")
                continue
        
        if auth_success:
            self._log_result(
                "API Authentication",
                True,
                f"API key authentication successful on {working_endpoint}"
            )
            return True
        elif working_endpoint:
            self._log_result(
                "API Authentication",
                False,
                f"API endpoint found at {working_endpoint} but authentication failed",
                {"endpoint": working_endpoint, "suggestion": "Check API key validity"}
            )
            return False
        else:
            self._log_result(
                "API Authentication",
                False,
                "Could not find working assets endpoint",
                {"tested_endpoints": auth_endpoints_to_try}
            )
            return False
    
    def validate_database_connectivity(self) -> bool:
        """Test MongoDB connectivity"""
        
        print("\n💾 Testing Database Connectivity...")
        
        try:
            client = MongoClient(self.config["mongodb_uri"], serverSelectionTimeoutMS=10000)
            
            # Test connection
            client.admin.command('ping')
            
            self._log_result(
                "MongoDB Connection",
                True,
                "Successfully connected to MongoDB"
            )
            
            # Test database access
            db = client[self.config["db_name"]]
            
            # Count assets for the wallet
            asset_count = db.assets.count_documents({
                "walletAddress": self.config["wallet_address"],
                "isCurrent": True,
                "isDeleted": False
            })
            
            self._log_result(
                "Database Access",
                True,
                f"Found {asset_count} assets for wallet",
                {"asset_count": asset_count, "database": self.config["db_name"]}
            )
            
            return True
            
        except Exception as e:
            self._log_result(
                "MongoDB Connection",
                False,
                "Failed to connect to MongoDB",
                {"error": str(e), "uri": self.config["mongodb_uri"].split('@')[1] if '@' in self.config["mongodb_uri"] else "local"}
            )
            return False
    
    def print_summary(self):
        """Print validation summary"""
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["success"])
        failed_tests = total_tests - passed_tests
        
        success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
        
        print(f"\n{'='*60}")
        print("🎯 FUSEVAULT VALIDATION SUMMARY")
        print(f"{'='*60}")
        
        print(f"📊 Tests: {passed_tests}/{total_tests} passed ({success_rate:.1f}%)")
        
        if failed_tests == 0:
            print("🎯 Overall Status: PASS")
            print("\n🟢 FuseVault system is ready for benchmarking!")
        else:
            print("🎯 Overall Status: FAIL")
            print(f"\n🔴 FuseVault system has {failed_tests} validation failures")
            print("   Please fix the issues above before running benchmarks")
        
        print(f"\n📝 Configuration:")
        print(f"   API: {self.api_base_url}")
        print(f"   Database: {self.config['db_name']}")
        print(f"   Wallet: {self.config['wallet_address'][:10]}...")
        
        # Show failed tests
        failed_tests = [r for r in self.results if not r["success"]]
        if failed_tests:
            print(f"\n🔍 Failed Tests:")
            for test in failed_tests:
                print(f"   ❌ {test['test']}: {test['message']}")


def main():
    """Main validation execution"""
    
    parser = argparse.ArgumentParser(description='FuseVault System Validator with Debug')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug mode with detailed API testing')
    
    args = parser.parse_args()
    
    print("🚀 FuseVault System Validator (Debug Mode)" if args.debug else "🚀 FuseVault System Validator")
    print("=" * 40)
    
    validator = FuseVaultValidatorDebug(debug=args.debug)
    
    # Run validation
    config_ok = validator.validate_configuration()
    if not config_ok:
        validator.print_summary()
        return
    
    api_ok = validator.validate_api_connectivity()
    db_ok = validator.validate_database_connectivity()
    
    # Print summary
    validator.print_summary()


if __name__ == "__main__":
    main()