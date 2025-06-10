import pytest
import hashlib
import hmac
import secrets
from unittest.mock import patch

from app.utilities.api_key_utils import (
    generate_api_key,
    validate_api_key_format,
    validate_api_key_signature,
    get_api_key_hash,
    extract_wallet_tag,
    _b64url_encode,
    _b64url_decode
)


class TestApiKeyUtilities:
    """Test suite for API key utility functions."""

    def test_b64url_encode_decode_roundtrip(self):
        """Test that base64 URL encoding and decoding works correctly."""
        test_data = b"Hello, World! This is a test string with special chars: @#$%^&*()"
        
        # Encode and decode
        encoded = _b64url_encode(test_data)
        decoded = _b64url_decode(encoded)
        
        assert decoded == test_data
        # Ensure no padding characters
        assert '=' not in encoded

    def test_b64url_encode_no_padding(self):
        """Test that base64 URL encoding removes padding."""
        # Test with data that would normally have padding
        test_data = b"test"  # This would have padding in normal base64
        encoded = _b64url_encode(test_data)
        
        assert '=' not in encoded
        assert '+' not in encoded
        assert '/' not in encoded

    def test_b64url_decode_adds_padding(self):
        """Test that base64 URL decoding correctly adds padding."""
        # Test various padding scenarios
        test_cases = [
            ("dGVzdA", b"test"),  # 2 chars of padding needed
            ("dGVzdGE", b"testa"),  # 1 char of padding needed
            ("dGVzdGVy", b"tester"),  # No padding needed
        ]
        
        for encoded, expected in test_cases:
            decoded = _b64url_decode(encoded)
            assert decoded == expected

    def test_generate_api_key_format(self, test_wallet_address, test_api_key_secret):
        """Test that generated API keys have the correct format."""
        api_key, key_hash = generate_api_key(test_wallet_address, test_api_key_secret)
        
        # Check overall format
        parts = api_key.split('.')
        assert len(parts) == 5
        assert parts[0] == 'fv'
        assert parts[1] == 'v1'
        
        # Check wallet tag (last 8 chars of wallet address without 0x)
        expected_wallet_tag = test_wallet_address.lower()[-8:]
        assert parts[2] == expected_wallet_tag
        
        # Check that nonce and signature are base64 encoded
        nonce = parts[3]
        signature = parts[4]
        
        # Should be able to decode without error
        _b64url_decode(nonce)
        _b64url_decode(signature)
        
        # Check hash format
        assert len(key_hash) == 64  # SHA256 hex string
        assert all(c in '0123456789abcdef' for c in key_hash)

    def test_generate_api_key_uniqueness(self, test_wallet_address, test_api_key_secret):
        """Test that generated API keys are unique."""
        keys = []
        hashes = []
        
        for _ in range(10):
            api_key, key_hash = generate_api_key(test_wallet_address, test_api_key_secret)
            keys.append(api_key)
            hashes.append(key_hash)
        
        # All keys should be unique
        assert len(set(keys)) == 10
        assert len(set(hashes)) == 10

    def test_generate_api_key_deterministic_parts(self, test_wallet_address, test_api_key_secret):
        """Test that parts of the API key are deterministic where they should be."""
        api_key1, _ = generate_api_key(test_wallet_address, test_api_key_secret)
        api_key2, _ = generate_api_key(test_wallet_address, test_api_key_secret)
        
        parts1 = api_key1.split('.')
        parts2 = api_key2.split('.')
        
        # Prefix and version should be the same
        assert parts1[0] == parts2[0] == 'fv'
        assert parts1[1] == parts2[1] == 'v1'
        
        # Wallet tag should be the same
        assert parts1[2] == parts2[2]
        
        # Nonce and signature should be different (random nonce)
        assert parts1[3] != parts2[3]
        assert parts1[4] != parts2[4]

    def test_validate_api_key_format_valid_keys(self, test_api_key):
        """Test validation of correctly formatted API keys."""
        assert validate_api_key_format(test_api_key) is True
        
        # Test with different wallet tags
        valid_keys = [
            "fv.v1.12345678.dGVzdGluZw.c2lnbmF0dXJl",
            "fv.v1.abcdef12.bm9uY2U.c2lnbmF0dXJl",
            "fv.v1.00000000.YWJjZGVmZ2g.ZGVmYWJjZGVmZw"
        ]
        
        for key in valid_keys:
            assert validate_api_key_format(key) is True

    def test_validate_api_key_format_invalid_keys(self):
        """Test validation of incorrectly formatted API keys."""
        invalid_keys = [
            # Wrong number of parts
            "fv.v1.12345678.nonce",
            "fv.v1.12345678.nonce.sig.extra",
            
            # Wrong prefix
            "fusevault.v1.12345678.nonce.sig",
            "fv2.v1.12345678.nonce.sig",
            
            # Wrong version
            "fv.v2.12345678.nonce.sig",
            "fv.v0.12345678.nonce.sig",
            
            # Invalid wallet tag (not 8 hex chars)
            "fv.v1.1234567.nonce.sig",  # Too short
            "fv.v1.123456789.nonce.sig",  # Too long
            "fv.v1.1234567g.nonce.sig",  # Invalid char
            
            # Invalid base64
            "fv.v1.12345678.invalid@base64.sig",
            "fv.v1.12345678.nonce.invalid@base64",
            
            # Empty parts
            "fv.v1..nonce.sig",
            "fv.v1.12345678..sig",
        ]
        
        for key in invalid_keys:
            assert validate_api_key_format(key) is False

    def test_validate_api_key_signature_valid(self, test_wallet_address, test_api_key_secret):
        """Test signature validation for valid API keys."""
        # Generate a real API key
        api_key, _ = generate_api_key(test_wallet_address, test_api_key_secret)
        
        # Should validate correctly
        assert validate_api_key_signature(api_key, test_api_key_secret) is True

    def test_validate_api_key_signature_invalid_secret(self, test_wallet_address, test_api_key_secret):
        """Test signature validation with wrong secret."""
        # Generate API key with one secret
        api_key, _ = generate_api_key(test_wallet_address, test_api_key_secret)
        
        # Try to validate with different secret
        wrong_secret = "different_secret_key_minimum_32_chars"
        assert validate_api_key_signature(api_key, wrong_secret) is False

    def test_validate_api_key_signature_tampered_key(self, test_wallet_address, test_api_key_secret):
        """Test signature validation for tampered API keys."""
        # Generate a real API key
        api_key, _ = generate_api_key(test_wallet_address, test_api_key_secret)
        parts = api_key.split('.')
        
        # Tamper with different parts
        tampered_keys = [
            # Change nonce
            f"{parts[0]}.{parts[1]}.{parts[2]}.changed_nonce.{parts[4]}",
            # Change wallet tag
            f"{parts[0]}.{parts[1]}.87654321.{parts[3]}.{parts[4]}",
            # Change signature
            f"{parts[0]}.{parts[1]}.{parts[2]}.{parts[3]}.wrong_sig",
        ]
        
        for tampered_key in tampered_keys:
            assert validate_api_key_signature(tampered_key, test_api_key_secret) is False

    def test_validate_api_key_signature_malformed(self, test_api_key_secret):
        """Test signature validation for malformed keys."""
        malformed_keys = [
            "not.enough.parts",
            "too.many.parts.here.now.extra",
            "",
            "fv.v1.12345678.nonce",
        ]
        
        for key in malformed_keys:
            assert validate_api_key_signature(key, test_api_key_secret) is False

    def test_get_api_key_hash(self, test_api_key):
        """Test API key hashing."""
        hash1 = get_api_key_hash(test_api_key)
        hash2 = get_api_key_hash(test_api_key)
        
        # Same key should produce same hash
        assert hash1 == hash2
        
        # Hash should be SHA256 hex string
        assert len(hash1) == 64
        assert all(c in '0123456789abcdef' for c in hash1)
        
        # Should match manual SHA256
        expected_hash = hashlib.sha256(test_api_key.encode('utf-8')).hexdigest()
        assert hash1 == expected_hash

    def test_get_api_key_hash_different_keys(self):
        """Test that different keys produce different hashes."""
        key1 = "fv.v1.12345678.nonce1.sig1"
        key2 = "fv.v1.12345678.nonce2.sig2"
        
        hash1 = get_api_key_hash(key1)
        hash2 = get_api_key_hash(key2)
        
        assert hash1 != hash2

    def test_extract_wallet_tag_valid(self):
        """Test wallet tag extraction from valid API keys."""
        test_cases = [
            ("fv.v1.12345678.nonce.sig", "12345678"),
            ("fv.v1.abcdef00.nonce.sig", "abcdef00"),
            ("fv.v1.00000000.nonce.sig", "00000000"),
        ]
        
        for api_key, expected_tag in test_cases:
            assert extract_wallet_tag(api_key) == expected_tag

    def test_extract_wallet_tag_invalid(self):
        """Test wallet tag extraction from invalid API keys."""
        invalid_keys = [
            "not.enough.parts",
            "wrong.prefix.12345678.nonce.sig",
            "fv.v2.12345678.nonce.sig",  # Wrong version
            "",
            "invalid_format",
        ]
        
        for key in invalid_keys:
            assert extract_wallet_tag(key) is None

    def test_extract_wallet_tag_exception_handling(self):
        """Test wallet tag extraction handles exceptions gracefully."""
        # These should not raise exceptions, just return None
        edge_cases = [
            None,  # This would cause AttributeError
            123,   # This would cause AttributeError
            [],    # This would cause AttributeError
        ]
        
        for case in edge_cases:
            # The function handles these cases gracefully by returning None
            # In real usage, this function should only receive strings
            result = extract_wallet_tag(case)
            assert result is None

    def test_signature_constant_time_comparison(self, test_wallet_address, test_api_key_secret):
        """Test that signature validation uses constant-time comparison."""
        # Generate a real API key
        api_key, _ = generate_api_key(test_wallet_address, test_api_key_secret)
        
        # Mock secrets.compare_digest to ensure it's being used
        with patch('app.utilities.api_key_utils.secrets.compare_digest') as mock_compare:
            mock_compare.return_value = True
            
            validate_api_key_signature(api_key, test_api_key_secret)
            
            # Verify that secrets.compare_digest was called
            assert mock_compare.called

    def test_api_key_generation_with_special_wallet_address(self, test_api_key_secret):
        """Test API key generation with various wallet address formats."""
        test_addresses = [
            "0xa87a09e1c8E5F2256CDCAF96B2c3Dbff231D7D7f",  # Mixed case
            "0xA87A09E1C8E5F2256CDCAF96B2C3DBFF231D7D7F",  # Upper case
            "0xa87a09e1c8e5f2256cdcaf96b2c3dbff231d7d7f",  # Lower case
        ]
        
        for address in test_addresses:
            api_key, key_hash = generate_api_key(address, test_api_key_secret)
            
            # All should produce valid format
            assert validate_api_key_format(api_key)
            assert validate_api_key_signature(api_key, test_api_key_secret)
            
            # Wallet tag should be lowercase last 8 chars
            parts = api_key.split('.')
            expected_tag = address.lower()[-8:]
            assert parts[2] == expected_tag

    def test_hmac_signature_length(self, test_wallet_address, test_api_key_secret):
        """Test that HMAC signature is truncated to 240 bits (30 bytes)."""
        api_key, _ = generate_api_key(test_wallet_address, test_api_key_secret)
        parts = api_key.split('.')
        signature_part = parts[4]
        
        # Decode the signature
        signature_bytes = _b64url_decode(signature_part)
        
        # Should be exactly 30 bytes (240 bits)
        assert len(signature_bytes) == 30

    def test_nonce_entropy(self, test_wallet_address, test_api_key_secret):
        """Test that nonces have sufficient entropy."""
        nonces = []
        
        for _ in range(100):
            api_key, _ = generate_api_key(test_wallet_address, test_api_key_secret)
            parts = api_key.split('.')
            nonce = parts[3]
            nonces.append(nonce)
        
        # All nonces should be unique
        assert len(set(nonces)) == 100
        
        # Each nonce should decode to 16 bytes (128 bits)
        for nonce in nonces[:5]:  # Test a few
            nonce_bytes = _b64url_decode(nonce)
            assert len(nonce_bytes) == 16

    def test_api_key_backwards_compatibility(self):
        """Test that the current implementation validates known good keys."""
        # This is the actual test key from the implementation
        known_good_key = "fv.v1.231d7d7f.t2FC1oOt1BQDBisHMjXAyw.k0xpsz3t1GLzyyJiVvj8sWF9t6unlrFG91JdHUQb"
        
        # Should pass format validation
        assert validate_api_key_format(known_good_key) is True
        
        # Extract wallet tag
        assert extract_wallet_tag(known_good_key) == "231d7d7f"
        
        # Get hash
        key_hash = get_api_key_hash(known_good_key)
        assert len(key_hash) == 64