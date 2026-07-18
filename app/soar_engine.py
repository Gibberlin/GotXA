"""
SOAR Engine — System Orchestration and Automated Response

Background daemon thread that continuously monitors for unhandled alerts,
maps each alert to the appropriate response playbook, executes the action,
and records the result. This is the "brain" of the automated response system.
"""

import logging
import threading
import time
import re
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# How often the engine polls for new alerts (seconds)
POLL_INTERVAL = 5

# Map detection rule names to (action_type, playbook_name) pairs
RULE_PLAYBOOK_MAP = {
    'Brute Force Attempt': [
        ('ip_block', 'brute_force_ip_block')
    ],
    'Brute Force Threshold Exceeded': [
        ('ip_block', 'brute_force_ip_block'),
        ('credential_lock', 'brute_force_credential_lock')
    ],
    'Critical System Error': [
        ('service_restart', 'critical_error_restart')
    ],
    'Network Anomaly Detected': [
        ('ip_block', 'network_anomaly_block'),
        ('rate_limit', 'network_anomaly_rate_limit')
    ],
    'Privilege Escalation': [
        ('container_isolate', 'privilege_escalation_isolate')
    ],
    'Service Availability Issue': [
        ('service_restart', 'service_availability_restart')
    ],
    'Infrastructure Anomaly': [
        ('service_restart', 'infrastructure_restart')
    ],
    'Error Event': [
        ('log_escalation', 'error_event_escalation')
    ],
    'Warning Event': [
        ('monitor_escalation', 'warning_monitor_escalation')
    ],
}


def _extract_ip(message: str) -> str:
    """Extract an IP address from a log message."""
    ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    match = re.search(ip_pattern, message or '')
    return match.group(0) if match else 'unknown-source'


def _extract_account(message: str) -> str:
    """Extract a username/account from a log message."""
    # Try patterns like 'username=xxx', 'User xxx', or 'credentials for xxx'
    patterns = [
        r'username[=:](\S+)',
        r'[Uu]ser\s+(\S+)',
        r'account[=:](\S+)',
        r'credentials\s+for\s+(\S+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, message or '')
        if match:
            return match.group(1).strip("'\"")
    return 'unknown-account'


def _determine_target(action_type: str, alert_host: str, alert_message: str, alert=None) -> str:
    """Determine the target for a given action type based on alert context."""
    if action_type == 'ip_block':
        ip = _extract_ip(alert_message)
        # If threshold alert, find IP from the last log
        if ip == 'unknown-source' and alert and 'Threshold Exceeded' in alert.rule:
            try:
                from models import Log
                last_log = Log.query.filter(
                    Log.host == alert_host,
                    Log.message.ilike('%from%') | Log.message.ilike('%ip=%')
                ).order_by(Log.created_at.desc()).first()
                if last_log:
                    ip = _extract_ip(last_log.message)
            except Exception as ex:
                logger.error(f"Failed to lookup threshold IP: {ex}")
        return ip
    elif action_type == 'rate_limit':
        return _extract_ip(alert_message)
    elif action_type == 'credential_lock':
        # If threshold alert, the summary message doesn't contain the account name.
        # Find the last log from this host to extract the target account.
        if alert and 'Threshold Exceeded' in alert.rule:
            try:
                from models import Log
                last_auth_log = Log.query.filter(
                    Log.host == alert_host,
                    Log.message.ilike('%credentials%') | Log.message.ilike('%login%') | Log.message.ilike('%user%')
                ).order_by(Log.created_at.desc()).first()
                if last_auth_log:
                    return _extract_account(last_auth_log.message)
            except Exception as ex:
                logger.error(f"Failed to lookup threshold username: {ex}")
        return _extract_account(alert_message)
    elif action_type == 'container_isolate':
        return alert_host
    elif action_type == 'service_restart':
        return alert_host
    elif action_type == 'log_escalation':
        return 'SOC-L2-Team'
    elif action_type == 'monitor_escalation':
        return alert_host
    return alert_host


def _build_description(action_type: str, target: str, alert_rule: str, alert_host: str) -> str:
    """Build a human-readable description for the SOAR action."""
    descriptions = {
        'ip_block': f"Blocked malicious IP {target} — triggered by '{alert_rule}' on {alert_host}",
        'container_isolate': f"Isolated container {target} from network — triggered by '{alert_rule}'",
        'service_restart': f"Restarted service {target} — triggered by '{alert_rule}'",
        'rate_limit': f"Applied rate limiting to IP {target} — triggered by '{alert_rule}' on {alert_host}",
        'credential_lock': f"Locked account {target} — triggered by '{alert_rule}' on {alert_host}",
        'log_escalation': f"Escalated incident to {target} — triggered by '{alert_rule}' on {alert_host}",
        'monitor_escalation': f"Increased monitoring for {target} — triggered by '{alert_rule}'",
    }
    return descriptions.get(action_type, f"Executed {action_type} on {target}")


class SoarEngine:
    """
    Core SOAR engine that runs as a background daemon thread.
    Polls for unhandled alerts and executes automated response playbooks.
    """

    def __init__(self, app):
        """
        Initialize the SOAR engine with a Flask app context.
        
        Args:
            app: Flask application instance (needed for database access in threads)
        """
        self.app = app
        self._running = False
        self._thread = None
        logger.info("🤖 [SOAR ENGINE] Initialized")

    def start(self):
        """Start the SOAR engine background thread."""
        if self._running:
            logger.warning("[SOAR ENGINE] Already running")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name='soar-engine')
        self._thread.start()
        logger.info("🚀 [SOAR ENGINE] Background daemon started (polling every %ds)", POLL_INTERVAL)

    def stop(self):
        """Stop the SOAR engine."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("🛑 [SOAR ENGINE] Stopped")

    def _run_loop(self):
        """Main polling loop — runs inside the background thread."""
        # Give the app a moment to fully start up
        time.sleep(3)
        
        while self._running:
            try:
                self._process_pending_alerts()
            except Exception as e:
                logger.error(f"[SOAR ENGINE] Error in processing loop: {e}", exc_info=True)
            
            time.sleep(POLL_INTERVAL)

    def _process_pending_alerts(self):
        """
        Find all unhandled (Open) alerts and execute the appropriate response playbook.
        Runs inside Flask app context for database access.
        """
        with self.app.app_context():
            from models import db, Alert, SoarAction
            from playbooks import playbook_executor

            try:
                # Find Open alerts that haven't been handled by SOAR yet
                open_alerts = Alert.query.filter(
                    Alert.status == 'Open'
                ).order_by(Alert.created_at.asc()).limit(20).all()

                if not open_alerts:
                    return

                for alert in open_alerts:
                    # Check if this alert already has SOAR actions
                    existing_actions = SoarAction.query.filter_by(alert_id=alert.id).count()
                    if existing_actions > 0:
                        continue

                    # Look up playbook(s) for this alert's rule
                    playbook_entries = RULE_PLAYBOOK_MAP.get(alert.rule, None)
                    if not playbook_entries:
                        # No playbook for this rule — mark as Investigating
                        alert.status = 'Investigating'
                        alert.updated_at = datetime.utcnow()
                        db.session.commit()
                        logger.info(f"[SOAR ENGINE] No playbook for rule '{alert.rule}' — marked Investigating")
                        continue

                    logger.info(f"🎯 [SOAR ENGINE] Processing alert #{alert.id}: {alert.rule} on {alert.host}")

                    # Execute each action in the playbook
                    all_succeeded = True
                    for action_type, playbook_name in playbook_entries:
                        target = _determine_target(action_type, alert.host, alert.log_message, alert)
                        description = _build_description(action_type, target, alert.rule, alert.host)

                        # Create the action record
                        soar_action = SoarAction(
                            alert_id=alert.id,
                            action_type=action_type,
                            target=target,
                            status='executing',
                            description=description,
                            playbook=playbook_name,
                            executed_at=datetime.utcnow()
                        )
                        db.session.add(soar_action)
                        db.session.flush()

                        # Check for action rate-limiting (60s cooldown per target/action_type)
                        recent_limit = datetime.utcnow() - timedelta(seconds=60)
                        recent_duplicate = SoarAction.query.filter(
                            SoarAction.action_type == action_type,
                            SoarAction.target == target,
                            SoarAction.status == 'completed',
                            SoarAction.completed_at >= recent_limit
                        ).first()

                        if recent_duplicate:
                            soar_action.status = 'completed'
                            soar_action.completed_at = datetime.utcnow()
                            soar_action.result_detail = (
                                f"[RATE LIMITED] Action skipped because the same action was executed "
                                f"successfully on this target recently (Action ID: {recent_duplicate.id})."
                            )
                            logger.info(f"⏱️ [SOAR ENGINE] Rate limited duplicate action {action_type} on {target}")
                            continue

                        # Execute the playbook action
                        try:
                            result = self._execute_action(action_type, target, alert, playbook_executor)
                            
                            soar_action.status = 'completed' if result.success else 'failed'
                            soar_action.completed_at = datetime.utcnow()
                            soar_action.result_detail = result.detail

                            if not result.success:
                                all_succeeded = False

                            logger.info(
                                f"{'✅' if result.success else '❌'} [SOAR ENGINE] "
                                f"Action {action_type} on {target}: "
                                f"{'SUCCESS' if result.success else 'FAILED'} ({result.execution_time_ms}ms)"
                            )

                        except Exception as e:
                            soar_action.status = 'failed'
                            soar_action.completed_at = datetime.utcnow()
                            soar_action.result_detail = f"Execution error: {str(e)}"
                            all_succeeded = False
                            logger.error(f"❌ [SOAR ENGINE] Action {action_type} failed: {e}", exc_info=True)

                    # Update alert status based on results
                    alert.status = 'Resolved' if all_succeeded else 'Investigating'
                    alert.updated_at = datetime.utcnow()
                    db.session.commit()

                    logger.info(
                        f"📋 [SOAR ENGINE] Alert #{alert.id} → {alert.status} "
                        f"({len(playbook_entries)} actions executed)"
                    )

            except Exception as e:
                db.session.rollback()
                logger.error(f"[SOAR ENGINE] Database error: {e}", exc_info=True)

    def _execute_action(self, action_type, target, alert, executor):
        """
        Route to the appropriate playbook executor method.
        
        Args:
            action_type: Type of action to execute
            target: Target of the action (IP, container name, etc.)
            alert: The Alert object that triggered this
            executor: PlaybookExecutor instance
            
        Returns:
            ActionResult from the playbook executor
        """
        if action_type == 'ip_block':
            return executor.execute_ip_block(target, f"Alert #{alert.id}: {alert.rule}")

        elif action_type == 'container_isolate':
            return executor.execute_container_isolate(target)

        elif action_type == 'service_restart':
            return executor.execute_service_restart(target)

        elif action_type == 'rate_limit':
            return executor.execute_rate_limit(target)

        elif action_type == 'credential_lock':
            return executor.execute_credential_lock(target)

        elif action_type == 'log_escalation':
            return executor.execute_log_escalation(alert.rule, alert.log_message)

        elif action_type == 'monitor_escalation':
            return executor.execute_monitor_escalation(target)

        else:
            from playbooks import ActionResult
            return ActionResult(
                success=False,
                detail=f"Unknown action type: {action_type}",
                execution_time_ms=0
            )


# Module-level reference (initialized in wsgi.py)
soar_engine_instance: Optional[SoarEngine] = None
