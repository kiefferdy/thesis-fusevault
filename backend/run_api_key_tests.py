#!/usr/bin/env python3
"""
API Key Tests Runner

This script provides an easy way to run all API key related tests
with various options and configurations.

Usage:
    python run_api_key_tests.py [options]

Options:
    --all           Run all API key tests
    --utils         Run utility function tests
    --repo          Run repository tests
    --service       Run service tests
    --auth          Run authentication provider tests
    --routes        Run HTTP routes tests
    --integration   Run integration tests
    --coverage      Run with coverage report
    --verbose       Run with verbose output
    --quick         Run with minimal output
    --help          Show this help message
"""

import sys
import subprocess
import argparse
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and return the result."""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}")
    print()
    
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(
        description="Run API key tests with various options",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    # Test selection options
    parser.add_argument('--all', action='store_true', help='Run all API key tests')
    parser.add_argument('--utils', action='store_true', help='Run utility function tests')
    parser.add_argument('--repo', action='store_true', help='Run repository tests')
    parser.add_argument('--service', action='store_true', help='Run service tests')
    parser.add_argument('--auth', action='store_true', help='Run authentication provider tests')
    parser.add_argument('--routes', action='store_true', help='Run HTTP routes tests')
    parser.add_argument('--integration', action='store_true', help='Run integration tests')
    
    # Output options
    parser.add_argument('--coverage', action='store_true', help='Run with coverage report')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--quick', '-q', action='store_true', help='Quick/quiet output')
    
    args = parser.parse_args()
    
    # Change to backend directory
    backend_dir = Path(__file__).parent
    if backend_dir.name != 'backend':
        print("❌ This script must be run from the backend directory")
        sys.exit(1)
    
    # Determine what tests to run
    test_files = []
    
    if args.all or not any([args.utils, args.repo, args.service, args.auth, args.routes, args.integration]):
        # Default to all tests if no specific tests selected
        test_files = [
            'tests/test_api_key_utils.py',
            'tests/test_api_key_repository.py', 
            'tests/test_api_key_service.py',
            'tests/test_api_key_auth_provider.py',
            'tests/test_api_key_routes.py',
            'tests/test_api_key_integration.py'
        ]
    else:
        if args.utils:
            test_files.append('tests/test_api_key_utils.py')
        if args.repo:
            test_files.append('tests/test_api_key_repository.py')
        if args.service:
            test_files.append('tests/test_api_key_service.py')
        if args.auth:
            test_files.append('tests/test_api_key_auth_provider.py')
        if args.routes:
            test_files.append('tests/test_api_key_routes.py')
        if args.integration:
            test_files.append('tests/test_api_key_integration.py')
    
    # Build pytest command
    cmd = ['python', '-m', 'pytest']
    
    # Add test files
    cmd.extend(test_files)
    
    # Add output options
    if args.verbose:
        cmd.append('-v')
    elif args.quick:
        cmd.append('-q')
    else:
        cmd.append('-v')  # Default to verbose
    
    # Add coverage options
    if args.coverage:
        coverage_modules = [
            '--cov=app.services.api_key_service',
            '--cov=app.repositories.api_key_repo',
            '--cov=app.utilities.api_key_utils',
            '--cov=app.services.api_key_auth_provider',
            '--cov=app.api.api_keys_routes',
            '--cov-report=html:htmlcov',
            '--cov-report=term-missing'
        ]
        cmd.extend(coverage_modules)
    
    # Print test plan
    print("🚀 API Key Test Runner")
    print("=" * 50)
    print(f"Running {len(test_files)} test file(s):")
    for test_file in test_files:
        print(f"  📝 {test_file}")
    print()
    
    if args.coverage:
        print("📊 Coverage reporting enabled")
        print("   HTML report will be generated in htmlcov/")
        print()
    
    # Run the tests
    success = run_command(cmd, "Running API Key Tests")
    
    # Print results
    print("\n" + "="*60)
    if success:
        print("✅ All tests passed!")
        if args.coverage:
            print("📊 Coverage report generated in htmlcov/index.html")
    else:
        print("❌ Some tests failed!")
        print("💡 Try running with --verbose for more details")
    print("="*60)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()