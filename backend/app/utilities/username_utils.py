import random
import string
import re
from typing import Optional, Tuple, List


def generate_username(base: str = "user") -> str:
    """
    Generate a unique username with a random suffix.
    
    Args:
        base: The base name for the username (default: "user")
        
    Returns:
        str: A generated username in the format "base_xxxxxx" where x is a random digit
    """
    # Generate 6 random digits
    random_suffix = ''.join(random.choices(string.digits, k=6))
    return f"{base}_{random_suffix}"


def generate_username_from_wallet(wallet_address: str) -> str:
    """
    Generate a username based on a wallet address.
    
    Args:
        wallet_address: The Ethereum wallet address
        
    Returns:
        str: A username in the format "user_last8chars" where last8chars are from the wallet
    """
    # Take the last 8 characters of the wallet address (excluding 0x)
    if wallet_address.startswith('0x'):
        suffix = wallet_address[-8:].lower()
    else:
        suffix = wallet_address[-8:].lower()
    
    return f"user_{suffix}"


def validate_username(username: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a username according to the defined rules.
    
    Args:
        username: The username to validate
        
    Returns:
        tuple: (is_valid, error_message) where is_valid is bool and error_message is str or None
    """
    if not username or len(username.strip()) == 0:
        return False, "Username cannot be empty"
    
    username = username.strip()
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"
    
    if len(username) > 30:
        return False, "Username must be 30 characters or less"
    
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return False, "Username can only contain letters, numbers, underscores, and hyphens"
    
    # Check for reserved usernames
    reserved_usernames = [
        'admin', 'administrator', 'root', 'system', 'api', 'www', 
        'mail', 'email', 'support', 'help', 'info', 'contact',
        'fusevault', 'fuse', 'vault', 'user', 'guest', 'anonymous'
    ]
    
    if username.lower() in reserved_usernames:
        return False, "This username is reserved and cannot be used"
    
    return True, None


def normalize_username(username: str) -> str:
    """
    Normalize a username by stripping whitespace and converting to lowercase.
    
    Args:
        username: The username to normalize
        
    Returns:
        str: The normalized username
    """
    return username.strip().lower()


def suggest_similar_usernames(username: str, count: int = 3) -> List[str]:
    """
    Generate similar username suggestions by adding random suffixes.
    
    Args:
        username: The base username
        count: Number of suggestions to generate
        
    Returns:
        list: List of suggested usernames
    """
    suggestions = []
    base = normalize_username(username)
    
    for _ in range(count):
        # Add random 2-3 digit number
        random_num = random.randint(10, 999)
        suggestions.append(f"{base}{random_num}")
    
    return suggestions