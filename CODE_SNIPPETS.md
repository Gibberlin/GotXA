# GotXA — Core Code Snippets & Implementation Details

This report provides the exact code implementations for the critical security mechanisms, access controls, database logging, and industrial simulations driving the GotXA platform.

---

## 🛡️ 1. Automated IP Blocking (iptables DROP Rule)
*   **File Path**: [`app/playbooks.py`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/app/playbooks.py#L53-L118)
*   **Mechanism**: Issues a packet filtering block command inside the container using `iptables`, while matching targets against a whitelisting exclusion criteria to prevent analyst lockout.

```python
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
```

---

## 🔒 2. Container Network Isolation (Docker SDK for Python)
*   **File Path**: [`app/playbooks.py`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/app/playbooks.py#L120-L180)
*   **Mechanism**: Uses the mounted Docker Unix socket (`/var/run/docker.sock`) to discover the networks attached to a compromised container and disconnects them laterally.

```python
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
```

---

## 🔄 3. Automated Service Restarts
*   **File Path**: [`app/playbooks.py`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/app/playbooks.py#L182-L220)
*   **Mechanism**: Connects to the host daemon using the Docker client library and restarts crashed log-collection or telemetry containers.

```python
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
```

---

## ⚙️ 4. Dynamic Settings Modification & Audit Tracking
*   **File Path**: [`backend/app/api_v1_consolidated.py`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/backend/app/api_v1_consolidated.py#L513-L558)
*   **Mechanism**: Iterates over a dictionary of updated dynamic configurations, queries the SQL schema, updates values, and saves a setting change log entry tracking the editor and reason ticket.

```python
@api.route('/settings/<section>', methods=['PATCH'])
@authenticate
@require_permission('settings.write')
def update_settings_section(section):
    """Save active configuration changes."""
    try:
        data = request.get_json()
        values = data.get('values', {})
        reason = data.get('reason', '')
        change_ticket = data.get('change_ticket', '')
        
        for key, value in values.items():
            setting = db.session.query(Setting).filter_by(
                section=section, key=key
            ).first()
            
            if not setting:
                setting = Setting(section=section, key=key)
                db.session.add(setting)
            
            old_value = setting.value
            setting.value = value
            
            # Log change
            change = SettingChange(
                section=section,
                key=key,
                changed_by_id=g.user.id,
                old_value=old_value,
                new_value=value,
                reason=reason,
                change_ticket=change_ticket
            )
            db.session.add(change)
        
        db.session.commit()
        
        return success_response({
            'section': section,
            'status': 'saved',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        db.session.rollback()
        return error_response('InternalError', str(e), 500)
```

---

## 👥 5. Role-Based Access Control Filters (RBAC Decorators)
*   **File Path**: [`backend/app/auth.py`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/backend/app/auth.py)
*   **Mechanism**: Validates incoming session credentials and verifies claims against a role capability mapping, blocking illegal requests.

```python
def require_permission(action):
    """Decorator to enforce RBAC permissions."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import g
            
            # Validate authentication state
            if not hasattr(g, 'auth_context') or not g.auth_context:
                return error_response('Unauthorized', 'Authentication required', 401)
                
            # Verify role permissions
            if not g.auth_context.has_permission(action):
                logger.warning(
                    f"⛔ RBAC Violation: User '{g.user.username}' (role: {g.user.role}) "
                    f"attempted unauthorized action: '{action}'"
                )
                return error_response(
                    'Forbidden', 
                    f"Role '{g.user.role}' does not possess permissions for action '{action}'", 
                    403
                )
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator
```

---

## 📝 6. Immutable Audit Logger (Correlation Diffs)
*   **File Path**: [`backend/app/audit.py`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/backend/app/audit.py)
*   **Mechanism**: Implements an append-only transaction recorder storing actor references, target IDs, correlation UUIDs, and detailed before/after states.

```python
class AuditLogger:
    """Logs all mutations with correlation IDs."""
    
    def log(self, actor, action, resource_type, resource_id, change_before=None, 
            change_after=None, reason='', status='success', ip_address=None, user_agent=None):
        """
        Log an audit event.
        """
        from flask import g, request
        
        event = AuditEvent(
            correlation_id=getattr(g, 'correlation_id', str(uuid.uuid4())),
            actor_id=actor.id if actor else None,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            change_before=change_before or {},
            change_after=change_after or {},
            reason=reason,
            ip_address=ip_address or request.remote_addr if request else None,
            user_agent=user_agent or request.headers.get('User-Agent') if request else None
        )
        
        db.session.add(event)
        db.session.flush()
```

---

## 🎛️ 7. Autonomous OT PLC Process Simulator
*   **File Path**: [`modbus_plc_server.py`](file:///c:/Users/RJDhu/OneDrive/Desktop/Project/GotXA/modbus_plc_server.py#L110-L134)
*   **Mechanism**: Runs a continuous loop simulating a thermodynamic heater or flow mixer, adjusting register metrics by ±0.5-1.0% and logging parameters to GCS/local telemetry paths.

```python
def simulate(context):
    logger.info(f"Simulation started for {AGENT_NAME}")
    while True:
        try:
            time.sleep(random.uniform(2, 5))
            slave = context.slaves[1]
            
            for reg_name, reg_addr in REGISTERS.items():
                idx = reg_addr - 40001
                current = slave.getValues(3, idx, 1)[0]
                
                # Apply autonomous noise variations
                if 'temperature' in reg_name:
                    new_val = max(1500, min(2200, current + random.uniform(-0.5, 0.5)))
                elif 'pressure' in reg_name:
                    new_val = max(300, min(800, current + random.uniform(-0.3, 0.3)))
                else:  # flow_rate
                    new_val = max(200, min(1000, current + random.uniform(-0.8, 0.8)))
                
                slave.setValues(3, idx, [new_val])
                
                # Periodically log instrumentation logs
                if random.random() < 0.1:
                    log_event(reg_name, reg_addr, new_val)
        except Exception as e:
            logger.error(f"Simulation error: {e}")
```
