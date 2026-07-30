import time
import requests

# Brute Force / Failed Login Simulation Script
TARGET_URL = "http://localhost:5001/login"

def run_bruteforce_attack():
    print("[*] Launching Brute Force (Failed Login) simulation...")
    
    for i in range(1, 6):
        payload = {"username": "admin", "password": f"wrong_pass_{i}"}
        try:
            res = requests.post(TARGET_URL, data=payload, timeout=3)
            print(f"[+] Sent failed login attempt #{i} | Status: {res.status_code}")
        except Exception as e:
            print(f"[-] Brute Force attempt #{i}: Event generated ({e})")
        
        time.sleep(0.5)

if __name__ == "__main__":
    run_bruteforce_attack()