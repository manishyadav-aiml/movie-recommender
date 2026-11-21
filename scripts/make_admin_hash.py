"""Create the ADMIN_PASSWORD_HASH value for .env.   Usage: python -m scripts.make_admin_hash"""
import getpass

from werkzeug.security import generate_password_hash

if __name__ == "__main__":
    pw = getpass.getpass("Choose an admin password (min 12 characters): ")
    if len(pw) < 12:
        raise SystemExit("Password too short.")
    if pw != getpass.getpass("Repeat password: "):
        raise SystemExit("Passwords do not match.")
    print("\nAdd this line to your .env file (keep the single quotes):\n")
    print(f"ADMIN_PASSWORD_HASH='{generate_password_hash(pw)}'")
