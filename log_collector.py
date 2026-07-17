#!/usr/bin/env python3
"""
Log Collector with Real-Time Dashboard (FIXED)
Correct log delimiter: ] (not ]:]
"""

import os, sys, time, json, logging, requests, threading
from pathlib import Path
from collections import deque
from flask import Flask, jsonify, render_template_string
from werkzeug.serving import make_server

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

SIEM_INGRESS_URL = 'http://siem-soar-server:5000/logs/ingest'
LOG_DIRS = ['/logs/corp-portal', '/logs/corp-database', '/logs/corp-workstation', '/logs/ot-scada', '/logs/ot-plc-1', '/logs/ot-plc-2']

raw_log_buffer = deque(maxlen=500)
buffer_lock = threading.Lock()

app = Flask(__name__)

DASHBOARD_HTML = '''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>🔍 Raw Log Stream</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Courier New',monospace;background:#0a0e27;color:#00ff88;height:100vh;overflow:hidden}.container{display:flex;flex-direction:column;height:100vh}.header{background:#1a1f3a;border-bottom:2px solid #00ff88;padding:12px 16px;display:flex;justify-content:space-between;align-items:center}.header h1{font-size:1.3em;letter-spacing:2px;text-shadow:0 0 10px #00ff88}.controls{display:flex;gap:10px;align-items:center}button{background:#00ff88;color:#0a0e27;border:none;padding:8px 16px;border-radius:4px;font-weight:bold;cursor:pointer;font-size:0.9em}button:hover{background:#00dd77;box-shadow:0 0 10px #00ff88}.toggle-label{color:#00ff88;display:flex;align-items:center;gap:8px;font-size:0.9em}input[type="checkbox"]{accent-color:#00ff88}.status{color:#00ff88;font-size:0.85em;display:flex;align-items:center;gap:6px}.status-dot{width:10px;height:10px;background:#00ff88;border-radius:50%;animation:pulse 1.5s infinite}@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}.log-container{flex:1;overflow-y:auto;background:#0a0e27;padding:16px;line-height:1.5}.log-entry{background:rgba(0,255,136,0.05);border-left:3px solid #00ff88;padding:10px 12px;margin-bottom:8px;border-radius:2px;font-size:0.95em;white-space:pre-wrap;word-break:break-all}.log-entry:hover{background:rgba(0,255,136,0.1)}.log-entry.highlight{border-left-color:#ff4444;background:rgba(255,68,68,0.05)}.json-key{color:#00ff88;font-weight:bold}.json-string{color:#ffaa00}.json-number{color:#ff55ff}.json-boolean{color:#55aaff}.empty-state{display:flex;align-items:center;justify-content:center;height:100%;color:#004400;font-size:1.2em;text-align:center;flex-direction:column;gap:12px}.spinner{width:20px;height:20px;border:2px solid #00664400;border-top-color:#00ff88;border-radius:50%;animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}.stats{font-size:0.85em;color:#00aa66;margin-right:12px}.log-container::-webkit-scrollbar{width:8px}.log-container::-webkit-scrollbar-track{background:#0a0e27}.log-container::-webkit-scrollbar-thumb{background:#00ff88;border-radius:4px}</style></head><body><div class="container"><div class="header"><div><h1>🔍 RAW LOG STREAM</h1></div><div class="controls"><div class="stats">Logs: <span id="log-count">0</span></div><label class="toggle-label"><input type="checkbox" id="auto-scroll" checked>Auto-Scroll</label><button onclick="togglePause()">▶ Pause</button><button onclick="clearScreen()">Clear</button><div class="status"><div class="status-dot"></div><span>STREAMING</span></div></div></div><div class="log-container" id="log-container"><div class="empty-state"><div class="spinner"></div><div>[SYSTEM READY] Waiting for incoming telemetry...</div></div></div></div><script>let isPaused=false,autoScroll=true,lastLogCount=0,emptyStateShown=true;const container=document.getElementById('log-container'),countEl=document.getElementById('log-count'),emptyEl=container.querySelector('.empty-state');async function updateLogs(){if(isPaused)return;try{const r=await fetch('/api/raw-stream'),logs=await r.json();if(countEl.textContent=logs.length,logs.length===0){if(!emptyStateShown){container.innerHTML='';emptyEl.style.display='flex';container.appendChild(emptyEl);emptyStateShown=true}return}if(emptyStateShown&&(container.innerHTML='',emptyStateShown=false),logs.length>lastLogCount){logs.slice(lastLogCount).forEach(log=>{const e=document.createElement('div');e.className='log-entry',('ERROR'===log.level||'HIGH'===log.level)&&e.classList.add('highlight'),e.innerHTML=highlight(JSON.stringify(log,null,2)),container.appendChild(e)})}lastLogCount=logs.length,autoScroll&&(container.scrollTop=container.scrollHeight)}catch(e){console.error('Error:',e)}}function highlight(json){return(json=json.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')).replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,m=>{let c='json-number';return/^"/.test(m)&&(c=/:$/.test(m)?'json-key':'json-string'),/true|false/.test(m)&&(c='json-boolean'),/null/.test(m)&&(c='json-null'),'<span class="'+c+'">'+m+'</span>'})}function togglePause(){isPaused=!isPaused}function clearScreen(){container.innerHTML='',lastLogCount=0,countEl.textContent='0',emptyStateShown=true}document.getElementById('auto-scroll').addEventListener('change',e=>{autoScroll=e.target.checked}),setInterval(updateLogs,2000),updateLogs()</script></body></html>'''

@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_HTML)

@app.route('/api/raw-stream')
def get_raw_stream():
    try:
        with buffer_lock:
            return jsonify(list(raw_log_buffer))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ====== LOG COLLECTION ======

class LogCollector:
    def __init__(self):
        self.buffer = []
        self.lock = threading.Lock()
        self.offsets = {}
    
    def run(self):
        logger.info("💾 Collector polling started")
        while True:
            try:
                for log_dir in LOG_DIRS:
                    self.check_logs(log_dir)
            except Exception as e:
                logger.error(f"Collector error: {e}", exc_info=True)
            time.sleep(2)
    
    def check_logs(self, log_dir):
        log_file = Path(log_dir) / 'app.log'
        if not log_file.exists():
            return
        
        key = str(log_file)
        offset = self.offsets.get(key, 0)
        
        try:
            with open(log_file, 'r') as f:
                f.seek(offset)
                lines = f.readlines()
                new_offset = f.tell()
            
            for line in lines:
                line = line.strip()
                # FIXED: Delimiter is ] (space), not ]:
                if not line or '] ' not in line:
                    continue
                
                try:
                    # Split on ] (space): [timestamp] activity
                    parts = line.split('] ', 1)
                    if len(parts) != 2:
                        continue
                    ts, activity = parts[0].lstrip('['), parts[1]
                    if ': ' not in activity:
                        continue
                    
                    atype, details = activity.split(': ', 1)
                    severity = 'HIGH' if any(x in atype for x in ['ERROR', 'FAILURE', 'INJECTION', 'COMMAND']) else ('MEDIUM' if any(x in atype for x in ['AUTH', 'SQL']) else 'LOW')
                    
                    entry = {'timestamp': ts, 'level': severity, 'message': f'{atype}: {details}', 'host': self._source(log_dir), 'source_type': 'corporate' if 'corp' in log_dir else 'operational'}
                    
                    with self.lock:
                        self.buffer.append(entry)
                    with buffer_lock:
                        raw_log_buffer.append(entry)
                    
                    logger.info(f"✓ Buffered: {entry['message'][:60]}")
                    
                    if len(self.buffer) >= 10:
                        self.flush()
                except Exception as parse_err:
                    logger.debug(f"Parse error: {parse_err}")
            
            self.offsets[key] = new_offset
        except Exception as e:
            logger.error(f"Error processing {log_file}: {e}")
    
    def _source(self, path):
        if 'corp-portal' in path: return 'corp-portal-agent'
        if 'corp-database' in path: return 'corp-database-agent'
        if 'corp-workstation' in path: return 'corp-workstation-agent'
        if 'ot-scada' in path: return 'ot-scada-gateway'
        if 'ot-plc-1' in path: return 'ot-plc-refinery-1'
        if 'ot-plc-2' in path: return 'ot-plc-refinery-2'
        return 'unknown'
    
    def flush(self):
        with self.lock:
            if not self.buffer:
                return
            batch = self.buffer[:]
            self.buffer.clear()
        
        try:
            logger.info(f"📤 Sending {len(batch)} logs to SIEM...")
            headers = {"Content-Type": "application/json"}
            payload_str = json.dumps(batch)
            logger.info(f"[POST] Sending to {SIEM_INGRESS_URL}")
            logger.debug(f"[PAYLOAD] {payload_str[:300]}...")
            r = requests.post(SIEM_INGRESS_URL, json=batch, headers=headers, timeout=3)
            logger.info(f"[RESPONSE] Status: {r.status_code}, Body: {r.text}")
            if r.status_code == 200:
                try:
                    resp_json = r.json()
                    ingested = resp_json.get('logs_ingested', 0)
                    logger.info(f"✓ SIEM ingested {ingested}/{len(batch)} logs")
                    if ingested == 0:
                        logger.warning(f"⚠️ SIEM reported 0 logs ingested! Response: {resp_json}")
                except Exception as parse_err:
                    logger.error(f"Failed to parse SIEM response: {parse_err}")
            else:
                logger.error(f"✗ SIEM returned {r.status_code}: {r.text}")
        except Exception as e:
            logger.error(f"SIEM error: {e}")
            with self.lock:
                self.buffer.extend(batch)

if __name__ == '__main__':
    logger.info("=" * 70)
    logger.info("🔍 DEDICATED LOG COLLECTOR - WITH RAW STREAM DASHBOARD")
    logger.info("=" * 70)
    
    for d in LOG_DIRS:
        Path(d).mkdir(parents=True, exist_ok=True)
        logger.info(f"✓ Log directory: {d}")
    
    logger.info(f"Forwarding to: {SIEM_INGRESS_URL}")
    logger.info("Dashboard: http://0.0.0.0:5001/")
    logger.info("API: http://0.0.0.0:5001/api/raw-stream")
    
    # Collector daemon thread
    collector = LogCollector()
    t = threading.Thread(target=collector.run, daemon=True)
    t.start()
    
    # Main thread: Flask server
    logger.info("✓ Starting Flask server on port 5001")
    server = make_server('0.0.0.0', 5001, app, threaded=True)
    server.serve_forever()
