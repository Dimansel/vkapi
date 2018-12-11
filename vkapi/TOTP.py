import hmac

def generateTOTP(key, time, digits):
    result = ''
    while len(time) < 16:
        time = "0" + time

    msg = bytearray.fromhex(time)
    k = bytearray.fromhex(key)
    _hash = hmac.new(k, msg, "sha1").hexdigest()
    _hash = bytearray.fromhex(_hash)
    offset = _hash[-1] & 15
    binary = ((_hash[offset] & 127) << 24) | ((_hash[offset+1] & 255) << 16) | ((_hash[offset+2] & 255) << 8) | (_hash[offset+3] & 255)
    otp = binary % 10**digits
    result = str(otp)

    while len(result) < digits:
        result = "0" + result
    
    return result
