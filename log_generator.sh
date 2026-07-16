#!/bin/bash
# Lightweight log generator for agent containers
# Sends logs to log-processor via TCP

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
    
    LOG="[$TIMESTAMP] $L - $MSG"
    
    # Send log to log-processor via TCP
    echo "$LOG" | nc -w 1 log-processor 5000 2>/dev/null || echo "$LOG" >&2
    
    sleep $((RANDOM % 5 + 1))
done
