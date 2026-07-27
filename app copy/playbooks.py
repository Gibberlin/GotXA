"""
SOAR Playbook Executors — Hybrid Response Actions (Simulated & Real-world)

Each playbook function handles both simulated (default) and real-world execution modes
depending on the `SOAR_REAL_MODE` environment flag. Real mode connects to the Docker
host daemon (requires /var/run/docker.sock mount) and packet filtering interfaces
to execute actual network containment, service restarts, and IP blocks.
"""

import logging
import time
import re
import random
import os
import subprocess
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Environment flag to toggle between safe simulated mode and real action mode
REAL_MODE = os.getenv('SOAR_REAL_MODE', 'false').lower() == 'true'


@dataclass
class ActionResult:
    """Result of a playbook execution."""
    success: bool
    detail: str
    execution_time_ms: int


def _extract_ip_from_message(message: str) -> str:
    """Extract IP address from log message, or return a placeholder."""
    ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    match = re.search(ip_pattern, message)
    if match:
        return match.group(0)
    return 'unknown-source'


def _extract_host_from_message(message: str, alert_host: str) -> str:
    """Extract the target host/service from the alert context."""
    return alert_host or 'unknown-host'


class PlaybookExecutor:
    """
    Executes SOAR response actions (supports both simulated and real-world execution).
    """

    @staticmethod
    def execute_ip_block(target_ip: str, reason: str) -> ActionResult:
        """
        Block traffic from an IP address.
        Simulated: Logs the command.
        Real: Inserts an iptables DROP rule inside the SIEM container.
        """
        start = time.time()
        command = f"iptables -A INPUT -s {target_ip} -j DROP"

        # Safeguard: Never block loopback, docker gateway, or internal docker network IPs 
        # (prevents host lockout from container ports during testing)
        is_safe_ip = (
            target_ip == '127.0.0.1' or
            target_ip.startswith('172.24.0.') or
            target_ip.startswith('172.25.0.') or
            target_ip.startswith('172.17.0.') or
            target_ip.startswith('172.18.0.')
        )

        if not REAL_MODE or target_ip == 'unknown-source' or is_safe_ip:
            # Run simulation
            logger.info(f"🛡️ [SOAR SIMULATED] IP Block: {command} (Reason: {reason})")
            time.sleep(random.uniform(0.1, 0.3))
            elapsed_ms = int((time.time() - start) * 1000)
            detail = (
                f"[SIMULATED] IP Block Action Executed\n"
                f"  Command: {command}\n"
                f"  Target IP: {target_ip}\n"
                f"  Reason: {reason}\n"
                f"  Result: Traffic from {target_ip} would be dropped\n"
                f"  Execution time: {elapsed_ms}ms"
            )
            return ActionResult(success=True, detail=detail, execution_time_ms=elapsed_ms)

        # Run real world iptables block
        logger.info(f"🛡️ [SOAR REAL] Executing packet filter block: {command}")
        try:
            # Add rule to drop traffic
            result = subprocess.run(
                ["iptables", "-A", "INPUT", "-s", target_ip, "-j", "DROP"],
                capture_output=True,
                text=True,
                check=True
            )
            elapsed_ms = int((time.time() - start) * 1000)
            detail = (
                f"[REAL WORLD] IP Blocked Successfully\n"
                f"  Command: {command}\n"
                f"  Target IP: {target_ip}\n"
                f"  Reason: {reason}\n"
                f"  Result: Incoming traffic from {target_ip} is now blocked at the SIEM server\n"
                f"  Execution time: {elapsed_ms}ms"
            )
            logger.info(f"✅ [SOAR REAL] IP {target_ip} blocked ({elapsed_ms}ms)")
            return ActionResult(success=True, detail=detail, execution_time_ms=elapsed_ms)
        except Exception as e:
            elapsed_ms = int((time.time() - start) * 1000)
            detail = (
                f"[REAL WORLD - ERROR] Command failed: {command}\n"
                f"  Error: {str(e)}\n"
                f"  Fallback: Simulated IP Block recorded.\n"
                f"  Reason: {reason}"
            )
            logger.warning(f"❌ [SOAR REAL] Real IP block failed (missing NET_ADMIN cap?): {e}")
            return ActionResult(success=True, detail=detail, execution_time_ms=elapsed_ms)

    @staticmethod
    def execute_container_isolate(container_name: str) -> ActionResult:
        """
        Isolate a compromised container.
        Simulated: Logs the isolation command.
        Real: Disconnects the container from corporate-net network using Docker daemon.
        """
        start = time.time()
        command = f"docker network disconnect corporate-net {container_name}"

        if not REAL_MODE or container_name == 'unknown-host':
            # Run simulation
            logger.info(f"🔒 [SOAR SIMULATED] Container Isolate: {command}")
            time.sleep(random.uniform(0.2, 0.4))
            elapsed_ms = int((time.time() - start) * 1000)
            detail = (
                f"[SIMULATED] Container Isolation Executed\n"
                f"  Command: {command}\n"
                f"  Container: {container_name}\n"
                f"  Result: Container disconnected from corporate-net\n"
                f"  Execution time: {elapsed_ms}ms"
            )
            return ActionResult(success=True, detail=detail, execution_time_ms=elapsed_ms)

        # Run real world container isolation
        logger.info(f"🔒 [SOAR REAL] Isolating container: {container_name}")
        try:
            import docker
            client = docker.from_env()
            container = client.containers.get(container_name)

            # Discover network names attached to this container
            networks = container.attrs['NetworkSettings']['Networks']
            disconnected = []

            for net_name in list(networks.keys()):
                # Disconnect container from the networks (specifically the corporate network)
                if 'corp' in net_name or 'corporate' in net_name:
                    network = client.networks.get(net_name)
                    network.disconnect(container)
                    disconnected.append(net_name)

            elapsed_ms = int((time.time() - start) * 1000)
            detail = (
                f"[REAL WORLD] Container Isolated Successfully\n"
                f"  Container: {container_name}\n"
                f"  Disconnected from networks: {', '.join(disconnected)}\n"
                f"  Result: Container is now quarantined off corporate network\n"
                f"  Execution time: {elapsed_ms}ms"
            )
            logger.info(f"✅ [SOAR REAL] Container {container_name} isolated from networks: {disconnected}")
            return ActionResult(success=True, detail=detail, execution_time_ms=elapsed_ms)
        except Exception as e:
            elapsed_ms = int((time.time() - start) * 1000)
            detail = (
                f"[REAL WORLD - ERROR] Isolation failed for {container_name}\n"
                f"  Error: {str(e)}\n"
                f"  Fallback: Simulated isolation completed."
            )
            logger.error(f"❌ [SOAR REAL] Container isolation failed (Docker socket missing?): {e}")
            return ActionResult(success=False, detail=detail, execution_time_ms=elapsed_ms)

    @staticmethod
    def execute_service_restart(service_name: str) -> ActionResult:
        """
        Restart a failed container service.
        Simulated: Logs the restart command.
        Real: Commands local Docker daemon to restart the container.
        """
        start = time.time()
        command = f"docker restart {service_name}"

        if not REAL_MODE or service_name == 'unknown-host':
            # Run simulation
            logger.info(f"🔄 [SOAR SIMULATED] Service Restart: {command}")
            time.sleep(random.uniform(0.3, 0.6))
            elapsed_ms = int((time.time() - start) * 1000)
            detail = (
                f"[SIMULATED] Service Restart Executed\n"
                f"  Command: {command}\n"
                f"  Service: {service_name}\n"
                f"  Result: Container restarted successfully\n"
                f"  Execution time: {elapsed_ms}ms"
            )
            return ActionResult(success=True, detail=detail, execution_time_ms=elapsed_ms)

        # Run real world service restart
        logger.info(f"🔄 [SOAR REAL] Restarting service container: {service_name}")
        try:
            import docker
            client = docker.from_env()
            container = client.containers.get(service_name)
            container.restart()

            elapsed_ms = int((time.time() - start) * 1000)
            detail = (
                f"[REAL WORLD] Service Restarted Successfully\n"
                f"  Service: {service_name}\n"
                f"  Result: Docker container restarted and resumed telemetry\n"
                f"  Execution time: {elapsed_ms}ms"
            )
            logger.info(f"✅ [SOAR REAL] Container {service_name} restarted ({elapsed_ms}ms)")
            return ActionResult(success=True, detail=detail, execution_time_ms=elapsed_ms)
        except Exception as e:
            elapsed_ms = int((time.time() - start) * 1000)
            detail = (
                f"[REAL WORLD - ERROR] Restart failed for {service_name}\n"
                f"  Error: {str(e)}\n"
                f"  Fallback: Simulated restart completed."
            )
            logger.error(f"❌ [SOAR REAL] Service restart failed: {e}")
            return ActionResult(success=False, detail=detail, execution_time_ms=elapsed_ms)

    @staticmethod
    def execute_rate_limit(target_ip: str, max_requests: int = 10) -> ActionResult:
        """
        Simulate enabling rate limiting on suspicious traffic.
        """
        start = time.time()
        command = (
            f"iptables -A INPUT -s {target_ip} -p tcp --dport 80 "
            f"-m limit --limit {max_requests}/min -j ACCEPT"
        )
        logger.info(f"⏱️ [SOAR] EXECUTING RATE LIMIT (Simulated): {command}")
        time.sleep(random.uniform(0.1, 0.2))
        elapsed_ms = int((time.time() - start) * 1000)
        detail = (
            f"[SIMULATED] Rate Limit Enabled\n"
            f"  Command: {command}\n"
            f"  Target IP: {target_ip}\n"
            f"  Result: Traffic from {target_ip} restricted to {max_requests}/min\n"
            f"  Execution time: {elapsed_ms}ms"
        )
        return ActionResult(success=True, detail=detail, execution_time_ms=elapsed_ms)

    @staticmethod
    def execute_credential_lock(account_name: str) -> ActionResult:
        """
        Simulate locking a user credential.
        """
        start = time.time()
        command = f"passwd -l {account_name}"
        logger.info(f"🔐 [SOAR] EXECUTING CREDENTIAL LOCK (Simulated): {command}")
        time.sleep(random.uniform(0.1, 0.2))
        elapsed_ms = int((time.time() - start) * 1000)
        detail = (
            f"[SIMULATED] Credential Lock Executed\n"
            f"  Command: {command}\n"
            f"  Account: {account_name}\n"
            f"  Result: User account '{account_name}' locked in authentication database\n"
            f"  Execution time: {elapsed_ms}ms"
        )
        return ActionResult(success=True, detail=detail, execution_time_ms=elapsed_ms)

    @staticmethod
    def execute_log_escalation(alert_rule: str, description: str) -> ActionResult:
        """
        Simulate creating an incident response ticket.
        """
        start = time.time()
        ticket_id = f"INC-{random.randint(10000, 99999)}"
        logger.info(f"📋 [SOAR] CREATING INCIDENT TICKET (Simulated): {ticket_id}")
        time.sleep(random.uniform(0.1, 0.2))
        elapsed_ms = int((time.time() - start) * 1000)
        detail = (
            f"[SIMULATED] Incident Escalated\n"
            f"  Ticket: {ticket_id}\n"
            f"  Rule: {alert_rule}\n"
            f"  Assigned: SOC Team L2\n"
            f"  Execution time: {elapsed_ms}ms"
        )
        return ActionResult(success=True, detail=detail, execution_time_ms=elapsed_ms)

    @staticmethod
    def execute_monitor_escalation(host: str) -> ActionResult:
        """
        Simulate increasing telemetry collection resolution.
        """
        start = time.time()
        logger.info(f"📡 [SOAR] ESCALATING MONITORING RESOLUTION (Simulated) for {host}")
        time.sleep(random.uniform(0.1, 0.2))
        elapsed_ms = int((time.time() - start) * 1000)
        detail = (
            f"[SIMULATED] Monitoring escalated for {host}\n"
            f"  Polling interval decreased from 60s to 10s\n"
            f"  Execution time: {elapsed_ms}ms"
        )
        return ActionResult(success=True, detail=detail, execution_time_ms=elapsed_ms)


# Singleton instance
playbook_executor = PlaybookExecutor()
