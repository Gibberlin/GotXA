#!/bin/bash
# Lightweight log generator for agent containers
# Sends logs to log-processor via TCP and writes to shared volume

HOSTNAME=$(hostname)
MESSAGES=(
    "Database connection timeout"
    "Request processed successfully"
    "Memory usage above threshold"
    "User login attempt"
    "API call failed"
    "Cache invalidated"
    "Disk space running low"
    "Service restarted"
    "Configuration loaded"
    "Task completed"
)

# Determine the log directory based on AGENT_NAME
if [ "$AGENT_NAME" = "ot-scada-gateway" ]; then
    LOG_DIR="/logs/ot-scada"
elif [ "$AGENT_NAME" = "ot-plc-refinery-1" ]; then
    LOG_DIR="/logs/ot-plc-1"
elif [ "$AGENT_NAME" = "ot-plc-refinery-2" ]; then
    LOG_DIR="/logs/ot-plc-2"
fi

if [ -n "$LOG_DIR" ]; then
    mkdir -p "$LOG_DIR"
fi

echo "[*] Agent $HOSTNAME starting log generation..." >&2

while true; do
    LEVEL=$((RANDOM % 4))
    case $LEVEL in
        0) L="ERROR" ;;
        1) L="WARN" ;;
        2) L="INFO" ;;
        *) L="DEBUG" ;;
    esac
    
    MSG_IDX=$((RANDOM % ${#MESSAGES[@]}))
    MSG=${MESSAGES[$MSG_IDX]}
    TIMESTAMP=$(date '+%Y-%m-%dT%H:%M:%S')
    
    # Use ': ' instead of ' - ' so the log collector can parse it correctly
    LOG="[$TIMESTAMP] $L: $MSG"
    
    # Write to local shared volume if directory is defined
    if [ -n "$LOG_DIR" ]; then
        echo "$LOG" >> "$LOG_DIR/app.log"
    fi
    
    # Also write to stderr (keeps docker logs working)
    echo "$LOG" >&2
    
    sleep $((RANDOM % 5 + 1))
done
