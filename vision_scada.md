# SCADA Dashboard — Frontend Vision and API Handoff

## Product intent

The SCADA dashboard is a no-sign-in, operator-style visualisation for the
simulated refinery. It should feel like a holographic HMI: machines are visible
at a glance, live values are legible, and selecting a machine reveals its
controls and history. It must make the simulated nature of controls explicit
and must never claim a command was applied until the server confirms it.

## Main experience

1. The landing view shows a stylised refinery scene with clickable machine
   holograms and a persistent overall connection/status bar.
2. The dashboard polls live telemetry and updates values without moving the
   scene layout.
3. Selecting a machine opens a right-side detail panel with its readings,
   health, alarm state, and visible knobs/sliders.
4. An operator changes a proposed setpoint, reviews a confirmation dialog, and
   submits the command.
5. The panel shows `Pending`, `Applied`, or `Rejected`, then refreshes telemetry
   from the gateway. A clear control-audit entry remains visible.

## Suggested machine scene

| Machine | Live values | Interactions |
| --- | --- | --- |
| Refinery 1 heater | Temperature, pressure, connection status | Temperature setpoint knob; heater enable toggle; emergency stop (simulated) |
| Refinery 2 flow unit | Flow rate, connection status | Flow-rate setpoint knob; pump enable toggle; emergency stop (simulated) |
| Utility/status rail | Gateway health, last telemetry update, active alarms | Refresh, alarm acknowledgement when implemented |

Avoid precise 3D physics in the first version. A layered SVG or CSS/canvas scene
with glow, scan lines, gradients, and subtle animated particles will give the
hologram effect while remaining responsive and accessible.

## Recommended component map

| Area | Components |
| --- | --- |
| App shell | `ScadaLayout`, `ConnectionBanner`, `AlarmRail`, `LastUpdated` |
| Scene | `HologramScene`, `MachineNode`, `TelemetryLabel`, `FlowLine`, `AlarmBeacon` |
| Selection | `MachineDetailDrawer`, `MachineHealth`, `TrendChart`, `ControlAuditList` |
| Controls | `ControlKnob`, `SetpointInput`, `ToggleControl`, `EmergencyStop`, `CommandConfirmDialog` |
| Shared | `StatusBadge`, `LoadingState`, `OfflineState`, `ApiErrorState`, `ReducedMotionToggle` |

## Telemetry APIs available today

The standalone `scada_gateway.py` provides read-only telemetry on port `5002`.

| Method and endpoint | Use | Response fields |
| --- | --- | --- |
| `GET /api/modbus` | Load/poll all machinery | `refinery_1`, `refinery_2` |
| `GET /api/modbus/refinery-1` | Heater detail | `temperature`, `pressure`, `last_update`, `status` |
| `GET /api/modbus/refinery-2` | Flow-unit detail | `flow_rate`, `last_update`, `status` |
| `GET /health` | Gateway connectivity indicator | `status`, `service`, `plc_1`, `plc_2` |

Recommended polling: `/api/modbus` every 2 seconds while the page is visible;
pause when the document is hidden and resume immediately on focus. A status of
`offline` or `error` should freeze the last known value, show its age, and make
controls unavailable.

### Gateway routing requirement

The Docker Compose file does not currently start `scada_gateway.py`, and the
SCADA Nginx config sends `/api/*` to the main backend, not port `5002`.
Deployment must either expose the gateway directly (for example
`http://localhost:5002/api/modbus`) or proxy only `/api/modbus*` to a
`scada-gateway:5002` service. The frontend should use one configured API base
URL rather than hard-coding a host.

## SCADA control APIs now available

The gateway now provides the following simulated control APIs. Numeric commands
are range-validated and written to the simulated PLC; toggles, alarms, command
status, history, and audit entries are held in gateway memory and reset when
the gateway restarts.

| Method and endpoint | Purpose | Request / response |
| --- | --- | --- |
| `GET /api/scada/machines` | Machine metadata, allowable ranges, and control availability | machine `id`, `name`, `controls[]`, `limits`, `status` |
| `POST /api/scada/machines/{id}/commands` | Submit a simulated command | request: `command`, `value`, `reason`; response: `command_id`, `status: pending` |
| `GET /api/scada/commands/{command_id}` | Poll command result | `status`, `applied_at`, `rejection_reason?` |
| `GET /api/scada/machines/{id}/history?metric=&from=&to=` | Chartable telemetry history | `metric`, `samples: [{ timestamp, value }]` |
| `GET /api/scada/alarms` | Active and historical alarms | `id`, `machine_id`, `severity`, `message`, `raised_at`, `status` |
| `POST /api/scada/alarms/{id}/acknowledge` | Record an operator acknowledgement | request: `note`; response: updated alarm |
| `GET /api/scada/audit?machine_id=` | Show recent controls and outcomes | `command`, `actor`, `requested_at`, `status`, `value` |

Command handling must be server-side, range-validated, rate-limited, audited,
and simulated by default. The UI must disable out-of-range options and require a
confirmation step for toggles or emergency actions. Do not expose raw Modbus
write operations directly from the browser.

## Frontend delivery plan

1. Create the responsive hologram scene with fixture data and select-machine
   behaviour.
2. Connect to read-only `/api/modbus` telemetry and implement offline/stale
   states.
3. Add the detail drawer, visual alarms, and a small trend view.
4. Integrate command controls with the server-side validation and audit results
   returned by the control API.
5. Test polling cleanup, keyboard access to machines/controls, reduced-motion
   mode, and narrow screens before generating `frontend/scada_dashboard/dist/`.

## Definition of done

* Machines are identifiable without relying only on color or animation.
* Telemetry age and gateway health are always visible.
* A command has an explicit pending/success/failure outcome and audit record.
* No browser code can make a direct Modbus write.
* The final build output is self-contained in `frontend/scada_dashboard/dist/`.
