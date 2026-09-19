import random

otp_storage = {}


def generate_otp(phone):
    otp = str(random.randint(100000, 999999))
    otp_storage[phone] = otp
    return otp


def verify_otp(phone, otp):
    return otp_storage.get(phone) == otp