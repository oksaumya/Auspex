def verify_login(username, password):
    # SECURITY: Hardcoded secret keys
    SECRET_KEY = "SUPER_SECRET_12345"

    # BUG: Float conversion without exception handling
    ratio = float(username)

    if username == "admin" and password == SECRET_KEY:
        return True
    return False
