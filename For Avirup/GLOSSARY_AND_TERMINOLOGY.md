# GotXA — Glossary & Terminology

This document contains a layman-friendly glossary of terms, abbreviations, and acronyms used throughout the GotXA platform.

---

## 📚 Key Terms & Definitions

*   **API (Application Programming Interface)**: A set of defined rules that allows different software applications to communicate with each other. In GotXA, the frontend dashboards query the backend Flask API to load live statistics.
*   **Audit Trail**: A secure, chronological record of system changes. The audit log tracks who performed an action (e.g., changing a setting), when it was done, and what changed, making it easy to trace anomalies.
*   **Authentication (AuthN)**: The process of verifying a user's identity (e.g., checking usernames and passwords).
*   **Authorization (AuthZ)**: The process of verifying a user's permissions (e.g., determining what actions an authenticated user is allowed to perform based on their role).
*   **Brute Force Attack**: A hacking method where an attacker repeatedly attempts to guess a password or login key using automated software scripts.
*   **CORS (Cross-Origin Resource Sharing)**: A browser security mechanism that restricts web applications from making requests to a different domain or port than the one that served them.
*   **ESD (Emergency Shutdown)**: A safety control loop in industrial processes that automatically halts operations when registers exceed safety thresholds to prevent physical explosions or leaks.
*   **HMI (Human-Machine Interface)**: A dashboard with graphical displays that allows human operators to monitor and interact with industrial control machinery (like refinery heaters or chemical mixers).
*   **IOC (Indicator of Compromise)**: Forensic evidence on a network or computer that indicates a security breach, such as suspicious IP addresses, failed logins, or file system modifications.
*   **IP Address (Internet Protocol)**: A unique numerical label assigned to each device participating in a network, used for routing and blocking traffic.
*   **Modbus TCP**: A standard messaging protocol used in industrial manufacturing to transfer control data between computers (SCADA gateways) and physical devices (PLCs).
*   **ORM (Object-Relational Mapping)**: A programming technique that translates database tables into coding objects. GotXA uses SQLAlchemy ORM to manage PostgreSQL tables as Python objects.
*   **OT (Operational Technology)**: The hardware and software used to monitor and control physical equipment, valves, pumps, and factory processes.
*   **PLC (Programmable Logic Controller)**: A rugged industrial computer designed to monitor sensors (temperature, pressure) and execute physical outputs (opening valves, turning on heaters).
*   **RBAC (Role-Based Access Control)**: A security method that assigns access permissions to users based on their job role (e.g., Admins, Managers, Analysts) rather than individual identities.
*   **RCE (Remote Code Execution)**: A severe vulnerability that allows an attacker to execute arbitrary command-line instructions on a target host server.
*   **SCADA (Supervisory Control and Data Acquisition)**: A system architecture that gathers real-time process data from remote sensors and PLCs to monitor and control industrial operations.
*   **SIEM (Security Information and Event Management)**: A software solution that aggregates log telemetry from across an organization, detects patterns matching threat signatures, and alerts security analysts.
*   **SOAR (Security Orchestration, Automation, and Response)**: An engineering pipeline that automatically executes containment playbooks (like IP bans or host isolations) when a SIEM alert is triggered.
*   **SQL Injection (SQLi)**: An exploit technique where an attacker inserts malicious SQL database command strings into user input fields to bypass login forms or extract table data.
