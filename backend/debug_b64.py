import base64

def _b64url_decode(s):
    """Base64 URL-safe decoding, adding padding if needed"""
    padding = 4 - (len(s) % 4)
    if padding != 4:
        s += '=' * padding
    return base64.urlsafe_b64decode(s)

s = 'c2lnZ'
print('Original string:', s)
print('Length:', len(s))
print('Length % 4:', len(s) % 4)
padding = 4 - (len(s) % 4)
print('Padding needed:', padding)
padded = s + '=' * padding
print('Padded string:', padded)
try:
    result = _b64url_decode(s)
    print('Decoded successfully:', result)
except Exception as e:
    print('Decode failed:', e)

# Test what "c2lnZ" should decode to
try:
    # Try without padding first
    result = base64.urlsafe_b64decode(s + '===')
    print('With 3 padding chars:', result)
except Exception as e:
    print('With 3 padding failed:', e)