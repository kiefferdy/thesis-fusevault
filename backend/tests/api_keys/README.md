# API Keys Feature Test Suite

This directory contains comprehensive tests for the API Keys feature implementation in FuseVault.

## Test Files Overview

### Core Component Tests

1. **`test_api_key_utils.py`** - Utility Functions
   - Key generation and validation
   - Format checking and signature verification
   - Base64 URL encoding/decoding
   - Cryptographic security functions

2. **`test_api_key_repository.py`** - Database Layer
   - MongoDB operations for API keys
   - CRUD operations and indexing
   - Expiration and cleanup logic
   - Database error handling

3. **`test_api_key_service.py`** - Business Logic
   - API key lifecycle management
   - Permission validation
   - Limit enforcement
   - Metadata handling

4. **`test_api_key_auth_provider.py`** - Authentication Provider
   - Request authentication via API keys
   - Rate limiting functionality
   - Permission checking
   - Security validation

5. **`test_api_key_routes.py`** - HTTP Endpoints
   - FastAPI route handlers
   - Request/response validation
   - Error handling
   - Authentication middleware integration

6. **`test_api_key_integration.py`** - End-to-End Workflows
   - Complete API key lifecycle
   - Authentication flow integration
   - Concurrent operations
   - Error propagation

### Test Infrastructure

- **`run_api_key_tests.py`** - Dedicated test runner script for API key tests
- **`README.md`** - This documentation file
- **`../conftest.py`** - Shared fixtures and mocks (in parent tests directory)

## Running the Tests

### Prerequisites

```bash
# Ensure you're in the backend directory
cd backend

# Install test dependencies (if not already installed)
pip install -r requirements.txt
```

### Using the Dedicated Test Runner (Recommended)

```bash
# Run all API key tests (default)
python3 tests/api_keys/run_api_key_tests.py

# Run specific test categories
python3 tests/api_keys/run_api_key_tests.py --utils      # Utility tests only
python3 tests/api_keys/run_api_key_tests.py --repo       # Repository tests only  
python3 tests/api_keys/run_api_key_tests.py --service    # Service tests only
python3 tests/api_keys/run_api_key_tests.py --auth       # Auth provider tests only
python3 tests/api_keys/run_api_key_tests.py --routes     # Route tests only
python3 tests/api_keys/run_api_key_tests.py --integration # Integration tests only

# Output options
python3 tests/api_keys/run_api_key_tests.py --quick      # Minimal output
python3 tests/api_keys/run_api_key_tests.py --verbose    # Detailed output
python3 tests/api_keys/run_api_key_tests.py --coverage   # With coverage report
```

### Running Individual Test Files (Alternative)

```bash
# Test utility functions
python -m pytest tests/api_keys/test_api_key_utils.py -v

# Test repository layer
python -m pytest tests/api_keys/test_api_key_repository.py -v

# Test service layer
python -m pytest tests/api_keys/test_api_key_service.py -v

# Test authentication provider
python -m pytest tests/api_keys/test_api_key_auth_provider.py -v

# Test HTTP routes
python -m pytest tests/api_keys/test_api_key_routes.py -v

# Test integration scenarios
python -m pytest tests/api_keys/test_api_key_integration.py -v
```

### Running All API Key Tests (Alternative)

```bash
# Run all API key related tests
python -m pytest tests/api_keys/ -v

# Run with coverage report
python -m pytest tests/api_keys/ --cov=app.services.api_key_service --cov=app.repositories.api_key_repo --cov=app.utilities.api_key_utils --cov=app.services.api_key_auth_provider --cov=app.api.api_keys_routes --cov-report=html

# Run with detailed output
python -m pytest tests/api_keys/ -v -s
```

### Running Tests by Category

```bash
# Security and cryptography tests
python -m pytest tests/api_keys/test_api_key_utils.py::TestApiKeyUtilities::test_signature_constant_time_comparison -v
python -m pytest tests/api_keys/test_api_key_utils.py::TestApiKeyUtilities::test_hmac_signature_length -v

# Database operation tests
python -m pytest tests/api_keys/test_api_key_repository.py::TestAPIKeyRepository::test_validate_and_get_api_key_expired -v
python -m pytest tests/api_keys/test_api_key_repository.py::TestAPIKeyRepository::test_cleanup_expired_keys -v

# Business logic tests
python -m pytest tests/api_keys/test_api_key_service.py::TestAPIKeyService::test_create_api_key_max_limit_reached -v
python -m pytest tests/api_keys/test_api_key_service.py::TestAPIKeyService::test_update_permissions_invalid_permissions -v

# Authentication tests
python -m pytest tests/api_keys/test_api_key_auth_provider.py::TestAPIKeyAuthProvider::test_authenticate_rate_limited -v
python -m pytest tests/api_keys/test_api_key_auth_provider.py::TestAPIKeyAuthProvider::test_check_permission_specific -v

# HTTP endpoint tests
python -m pytest tests/api_keys/test_api_key_routes.py::TestAPIKeyRoutes::test_create_api_key_success -v
python -m pytest tests/api_keys/test_api_key_routes.py::TestAPIKeyRoutes::test_authentication_required -v

# Integration tests
python -m pytest tests/api_keys/test_api_key_integration.py::TestAPIKeyIntegration::test_complete_api_key_lifecycle -v
python -m pytest tests/api_keys/test_api_key_integration.py::TestAPIKeyIntegration::test_api_key_permission_enforcement -v
```

## Test Coverage Areas

### ✅ Cryptographic Security
- API key generation with proper entropy
- HMAC-SHA256 signature validation
- Constant-time comparison for security
- Base64 URL encoding without padding

### ✅ Database Operations
- API key CRUD operations
- Index creation and management
- Expiration handling and cleanup
- Concurrent operation safety

### ✅ Business Logic
- API key lifecycle management
- Permission validation and enforcement
- Rate limiting and quotas
- Error handling and validation

### ✅ Authentication & Authorization
- Request authentication via API keys
- Permission-based access control
- Rate limiting implementation
- Integration with existing auth system

### ✅ HTTP API
- RESTful endpoint implementation
- Request/response validation
- Error handling and status codes
- Authentication middleware integration

### ✅ Integration Scenarios
- End-to-end workflow testing
- Concurrent operation handling
- Error propagation testing
- Performance and scalability

## Test Data and Fixtures

The test suite uses the following test data:

- **Test Wallet Address**: `0xa87a09e1c8E5F2256CDCAF96B2c3Dbff231D7D7f`
- **Test API Key**: `fv.v1.231d7d7f.t2FC1oOt1BQDBisHMjXAyw.k0xpsz3t1GLzyyJiVvj8sWF9t6unlrFG91JdHUQb`
- **Test Secret Key**: `test_secret_key_for_api_key_signing_minimum_32_characters`

### Fixtures Available

- `mock_api_key_repo` - Mocked repository with async methods
- `mock_api_key_service` - Mocked service layer
- `mock_api_key_auth_provider` - Mocked authentication provider
- `test_wallet_address` - Standard test wallet address
- `test_api_key` - Valid test API key
- `test_api_key_hash` - SHA256 hash of test API key
- `test_api_key_data` - Sample database record
- `test_api_key_secret` - Test signing secret

## Mock Strategy

The tests use comprehensive mocking to:

1. **Isolate Units**: Each test focuses on a specific component
2. **Control Dependencies**: Mock external services (database, Redis, etc.)
3. **Simulate Scenarios**: Test error conditions and edge cases
4. **Ensure Determinism**: Predictable test outcomes

## Performance Considerations

### Test Execution Time
- Individual test files: ~2-5 seconds each
- Full API key test suite: ~15-30 seconds
- Integration tests: ~5-10 seconds

### Resource Usage
- Tests use mocks to minimize actual resource consumption
- No real database or Redis connections required
- Memory usage is minimal due to isolated test design

## Debugging Failed Tests

### Common Issues

1. **Import Errors**
   ```bash
   # Check if all dependencies are installed
   pip install -r requirements.txt
   
   # Verify Python path includes the app module
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

2. **Mock Configuration Issues**
   ```bash
   # Run with verbose output to see mock call details
   python -m pytest tests/test_api_key_service.py -v -s
   ```

3. **Async Test Issues**
   ```bash
   # Check event loop configuration
   python -m pytest tests/test_api_key_repository.py::TestAPIKeyRepository::test_create_api_key_success -v -s
   ```

### Debug Commands

```bash
# Run a single test with maximum verbosity
python -m pytest tests/api_keys/test_api_key_utils.py::TestApiKeyUtilities::test_generate_api_key_format -v -s --tb=long

# Run tests with pdb debugger on failure
python -m pytest tests/api_keys/test_api_key_service.py --pdb

# Generate detailed test report
python -m pytest tests/api_keys/ --html=reports/api_key_tests.html --self-contained-html
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
- name: Run API Key Tests
  run: |
    cd backend
    python3 tests/api_keys/run_api_key_tests.py --coverage
    
- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./backend/coverage.xml
```

### Pre-commit Hook

```bash
#!/bin/sh
# Run API key tests before commit
cd backend && python3 tests/api_keys/run_api_key_tests.py --quick
```

## Contributing to Tests

When adding new API key functionality:

1. **Add Unit Tests**: Update the appropriate test file
2. **Update Fixtures**: Add new fixtures to `conftest.py` if needed
3. **Integration Tests**: Add end-to-end scenarios to integration tests
4. **Documentation**: Update this README with new test categories

### Test Naming Convention

- `test_<functionality>_<scenario>` (e.g., `test_create_api_key_success`)
- Use descriptive names that explain the test purpose
- Group related tests in the same test class

### Mock Naming Convention

- `mock_<component>` (e.g., `mock_api_key_repo`)
- `sample_<data_type>` for test data (e.g., `sample_api_key_create`)
- `test_<identifier>` for test constants (e.g., `test_wallet_address`)

## Security Testing Notes

The test suite includes specific security-focused tests:

- **Timing Attack Prevention**: Constant-time comparison testing
- **Cryptographic Validation**: HMAC signature verification
- **Input Validation**: Format checking and sanitization
- **Permission Enforcement**: Access control validation
- **Rate Limiting**: Protection against abuse

These tests ensure the API key implementation follows security best practices.