"""
Security detection engine with regex-based rule definitions and alert logic.
"""

import re
import logging
from datetime import datetime, timedelta
from typing import List, Tuple

logger = logging.getLogger(__name__)

# ============================================================================
# RULE DEFINITIONS & REGEX PATTERNS
# ============================================================================

class SecurityRules:
    """Repository of security detection rules and patterns."""
    
    # Brute Force Attack Patterns
    BRUTE_FORCE_KEYWORDS = [
        'failed.*login',
        'authentication.*failed',
        'invalid.*password',
        'unauthorized.*access',
        'access.*denied',
        'permission.*denied',
        'auth.*failure',
        'invalid.*credentials'
    ]
    BRUTE_FORCE_PATTERN = re.compile('|'.join(BRUTE_FORCE_KEYWORDS), re.IGNORECASE)
    
    # Critical System Errors
    CRITICAL_ERROR_KEYWORDS = [
        'critical',
        'fatal',
        'emergency',
        'panic',
        'kernel.*panic',
        'segmentation.*fault',
        'out.*of.*memory'
    ]
    CRITICAL_ERROR_PATTERN = re.compile('|'.join(CRITICAL_ERROR_KEYWORDS), re.IGNORECASE)
    
    # API/Service Anomalies
    API_FAILURE_KEYWORDS = [
        'api.*fail',
        'service.*down',
        'service.*unavailable',
        'connection.*refused',
        'connection.*timeout',
        'unreachable'
    ]
    API_FAILURE_PATTERN = re.compile('|'.join(API_FAILURE_KEYWORDS), re.IGNORECASE)
    
    # Suspicious Network Activity
    NETWORK_ANOMALY_KEYWORDS = [
        'port.*scan',
        'syn.*flood',
        'ddos',
        'anomalous.*traffic',
        'suspicious.*ip',
        'blacklist.*match'
    ]
    NETWORK_ANOMALY_PATTERN = re.compile('|'.join(NETWORK_ANOMALY_KEYWORDS), re.IGNORECASE)
    
    # Privilege Escalation / Access Control
    PRIVILEGE_ESCALATION_KEYWORDS = [
        'sudo',
        'root.*access',
        'privilege.*escalation',
        'elevated.*privilege',
        'unauthorized.*elevation'
    ]
    PRIVILEGE_ESCALATION_PATTERN = re.compile('|'.join(PRIVILEGE_ESCALATION_KEYWORDS), re.IGNORECASE)
    
    # Infrastructure/OT Anomalies (Cross-Zone)
    INFRASTRUCTURE_ANOMALY_KEYWORDS = [
        'disk.*full',
        'memory.*critical',
        'cpu.*spike',
        'temperature.*high',
        'hardware.*fault',
        'equipment.*failure'
    ]
    INFRASTRUCTURE_ANOMALY_PATTERN = re.compile('|'.join(INFRASTRUCTURE_ANOMALY_KEYWORDS), re.IGNORECASE)
    
    # Generic Error Detection
    ERROR_KEYWORDS = ['error', 'fail', 'exception']
    ERROR_PATTERN = re.compile('|'.join(ERROR_KEYWORDS), re.IGNORECASE)
    
    # Warning Detection
    WARN_KEYWORDS = ['warn', 'warning']
    WARN_PATTERN = re.compile('|'.join(WARN_KEYWORDS), re.IGNORECASE)


class AlertEngine:
    """
    Core alert generation and validation engine.
    Applies security rules to ingested logs and generates alerts.
    """
    
    def __init__(self):
        self.rules = SecurityRules()
        self.recent_failures = {}  # Track failed login attempts for threshold
    
    def analyze_log(self, log_id: int, host: str, message: str, level: str) -> List[Tuple[str, str, str]]:
        """
        Analyze a log entry and return list of (severity, rule_name, rule_triggered).
        
        Args:
            log_id: Database log record ID
            host: Source hostname/IP
            message: Log message text
            level: Log level (ERROR, WARN, INFO, DEBUG)
        
        Returns:
            List of tuples: [(severity, rule_name, triggered_reason), ...]
        """
        alerts = []
        
        try:
            # Rule 1: Brute Force Detection
            if self.rules.BRUTE_FORCE_PATTERN.search(message):
                alerts.append(('HIGH', 'Brute Force Attempt', f'Pattern detected: {message[:80]}'))
                self._track_failure(host)
            
            # Rule 2: Critical System Errors
            if self.rules.CRITICAL_ERROR_PATTERN.search(message):
                alerts.append(('HIGH', 'Critical System Error', f'Critical error detected: {message[:80]}'))
            
            # Rule 3: API/Service Failures
            if self.rules.API_FAILURE_PATTERN.search(message):
                alerts.append(('MEDIUM', 'Service Availability Issue', f'Service failure: {message[:80]}'))
            
            # Rule 4: Network Anomalies
            if self.rules.NETWORK_ANOMALY_PATTERN.search(message):
                alerts.append(('HIGH', 'Network Anomaly Detected', f'Suspicious network activity: {message[:80]}'))
            
            # Rule 5: Privilege Escalation
            if self.rules.PRIVILEGE_ESCALATION_PATTERN.search(message):
                alerts.append(('HIGH', 'Privilege Escalation', f'Unauthorized elevation: {message[:80]}'))
            
            # Rule 6: Infrastructure/OT Anomalies
            if self.rules.INFRASTRUCTURE_ANOMALY_PATTERN.search(message):
                alerts.append(('MEDIUM', 'Infrastructure Anomaly', f'System resource issue: {message[:80]}'))
            
            # Rule 7: Threshold-based Brute Force (multiple failures from same host)
            failure_count = self._get_failure_count(host)
            if failure_count >= 5:
                alerts.append(('HIGH', 'Brute Force Threshold Exceeded', f'{host} has {failure_count} failures in last 10 min'))
            
            # Rule 8: Generic Error Escalation
            if level.upper() == 'ERROR' and not any(a[1] for a in alerts):
                if self.rules.ERROR_PATTERN.search(message):
                    alerts.append(('MEDIUM', 'Error Event', f'Log level ERROR: {message[:80]}'))
            
            # Rule 9: Warning Detection
            if level.upper() == 'WARN':
                alerts.append(('LOW', 'Warning Event', f'Log level WARN: {message[:80]}'))
        
        except Exception as e:
            logger.error(f"Error in analyze_log: {e}", exc_info=True)
        
        return alerts
    
    def _track_failure(self, host: str):
        """Track failure event for threshold detection."""
        if host not in self.recent_failures:
            self.recent_failures[host] = []
        self.recent_failures[host].append(datetime.utcnow())
        # Clean up old entries (> 10 minutes)
        cutoff = datetime.utcnow() - timedelta(minutes=10)
        self.recent_failures[host] = [ts for ts in self.recent_failures[host] if ts > cutoff]
    
    def _get_failure_count(self, host: str) -> int:
        """Get count of recent failures for a host."""
        return len(self.recent_failures.get(host, []))


# Singleton instance
alert_engine = AlertEngine()
