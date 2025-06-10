import os
import hmac
import hashlib
import secrets
import base64
from typing import Tuple, Optional


def _b64url_encode(data: bytes) -> str:
    """Base64 URL-safe encoding without padding"""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _b64url_decode(s: str) -> bytes:
    """Base64 URL-safe decoding, adding padding if needed"""
    padding = 4 - (len(s) % 4)
    if padding != 4:
        s += '=' * padding
    return base64.urlsafe_b64decode(s)


def generate_api_key(wallet_address: str, secret_key: str) -> Tuple[str, str]:
    """
    Generate a new API key for a wallet address.
    
    Args:
        wallet_address: The Ethereum wallet address (with 0x prefix)
        secret_key: The server's secret key for signing
        
    Returns:
        Tuple of (api_key, key_hash) where:
        - api_key: The actual API key to give to the user
        - key_hash: The hash to store in the database
    """
    # Extract wallet tag (last 8 chars without 0x)
    wallet_tag = wallet_address.lower()[-8:]
    
    # Generate 128-bit nonce
    nonce = os.urandom(16)
    nonce_b64 = _b64url_encode(nonce)
    
    # Construct base string
    base = f"fv.v1.{wallet_tag}.{nonce_b64}"
    
    # Generate HMAC signature
    sig_full = hmac.new(
        secret_key.encode('utf-8'),
        base.encode('utf-8'),
        hashlib.sha256
    ).digest()
    
    # Take left-most 240 bits (30 bytes) and encode
    sig_truncated = sig_full[:30]
    sig_b64 = _b64url_encode(sig_truncated)
    
    # Construct final API key
    api_key = f"{base}.{sig_b64}"
    
    # Generate hash for storage
    key_hash = hashlib.sha256(api_key.encode('utf-8')).hexdigest()
    
    return api_key, key_hash


def validate_api_key_format(api_key: str) -> bool:
    """
    Validate the API key format without checking the signature.
    
    Args:
        api_key: The API key to validate
        
    Returns:
        True if the format is valid, False otherwise
    """
    try:
        parts = api_key.split('.')
        if len(parts) != 5:
            return False
            
        prefix, version, wallet_tag, nonce, sig = parts
        
        # Check prefix
        if prefix != 'fv':
            return False
            
        # Check version
        if version not in ['v1']:  # Can add v2, v3 in future
            return False
            
        # Check wallet tag format (8 hex chars)
        if len(wallet_tag) != 8 or not all(c in '0123456789abcdef' for c in wallet_tag):
            return False
            
        # Check nonce can be decoded and is not empty
        if not nonce:
            return False
        _b64url_decode(nonce)
        
        # Check signature can be decoded and is not empty
        if not sig:
            return False
        _b64url_decode(sig)
        
        return True
        
    except Exception:
        return False


def validate_api_key_signature(api_key: str, secret_key: str) -> bool:
    """
    Validate the API key signature using the secret key.
    
    Args:
        api_key: The API key to validate
        secret_key: The server's secret key for validation
        
    Returns:
        True if the signature is valid, False otherwise
    """
    try:
        parts = api_key.split('.')
        if len(parts) != 5:
            return False
            
        prefix, version, wallet_tag, nonce, provided_sig = parts
        
        # Reconstruct base string
        base = f"{prefix}.{version}.{wallet_tag}.{nonce}"
        
        # Compute expected signature
        expected_sig_full = hmac.new(
            secret_key.encode('utf-8'),
            base.encode('utf-8'),
            hashlib.sha256
        ).digest()
        
        # Take left-most 240 bits and encode
        expected_sig = _b64url_encode(expected_sig_full[:30])
        
        # Constant-time comparison
        return secrets.compare_digest(provided_sig, expected_sig)
        
    except Exception:
        return False


def get_api_key_hash(api_key: str) -> str:
    """
    Get the hash of an API key for database lookup.
    
    Args:
        api_key: The API key to hash
        
    Returns:
        The SHA256 hash of the API key
    """
    return hashlib.sha256(api_key.encode('utf-8')).hexdigest()


def extract_wallet_tag(api_key: str) -> Optional[str]:
    """
    Extract the wallet tag from an API key.
    
    Args:
        api_key: The API key
        
    Returns:
        The wallet tag if valid, None otherwise
    """
    try:
        # Handle non-string inputs gracefully
        if not isinstance(api_key, str):
            return None
            
        parts = api_key.split('.')
        if len(parts) == 5 and parts[0] == 'fv' and parts[1] in ['v1']:
            return parts[2]
        return None
    except Exception:
        return None