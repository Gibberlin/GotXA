# Corporate Portal — Frontend Vision and API Handoff

## Product intent

The Corporate Portal is an authenticated employee operations workspace, not a
second SIEM. It should give an employee or administrator a calm, useful view of
business-system health, their work, announcements, and account security. Keep
security-event investigation in the SIEM dashboard.

## User journey

1. A user signs in from a focused, branded login page.
2. On success, they land on a personal dashboard.
3. They can review their assigned work, announcements, system availability, and
   recent account activity.
4. An administrator also sees the organization-wide operations summary and a
   lightweight user-management entry point.

## Dashboard content

### All signed-in users

* **Welcome and account card** — name, role, department, last sign-in, and a
  link to profile/security settings.
* **My tasks** — assigned, due soon, overdue, and recently completed work.
* **Announcements** — top three active notices, each with severity and publish
  date.
* **System status** — compact status tiles for Email, VPN, ERP, File Storage,
  and HR; show `Operational`, `Degraded`, or `Outage`.
* **Recent activity** — sign-in, password/security events, assigned work, and
  relevant system notices.

### Administrator additions

* **Operations overview** — active systems, open service issues, employee task
  completion, and average response time.
* **Team workload** — work grouped by team/status, with a link to a full queue.
* **Access review prompt** — pending access reviews and stale accounts.

## Recommended component map

| Area | Components |
| --- | --- |
| App shell | `PortalLayout`, top bar, responsive side navigation, global error/toast area |
| Authentication | `LoginPage`, `LoginForm`, `PasswordField`, session-expiry redirect |
| Home | `WelcomeCard`, `SystemStatusGrid`, `MyTasksCard`, `AnnouncementsCard`, `ActivityTimeline` |
| Admin | `OperationsKpis`, `TeamWorkload`, `AccessReviewCard` |
| Shared | `StatusBadge`, `EmptyState`, `LoadingSkeleton`, `ApiErrorState`, `ConfirmDialog` |

## API contract

### Available today (legacy service)

These routes are implemented in `siem_server.py`. The existing Corporate
Portal already calls them.

| Method and endpoint | Use | Response shape |
| --- | --- | --- |
| `POST /api/login` | Demo sign-in; send `multipart/form-data` with `username`, `password` | `{ "user": { "id", "username", "role" } }` |
| `GET /api/dashboard-metrics` | Existing organization KPI cards | `{ "active_systems", "total_transactions", "open_issues", "security_score", "response_time", "data_volume" }` |
| `GET /api/recent-activity` | Existing activity feed | `{ "activities": [{ "timestamp", "description", "status" }] }` |

Important: the Docker Compose `backend` service does not currently implement
these three legacy routes. The frontend team should not assume they are exposed
by the main `/api` proxy unless the deployment specifically starts and routes to
`siem_server.py`.

### Corporate Portal APIs now available

The active backend now provides the dedicated Corporate Portal namespace and
its token-based demo session flow. The dashboard content is seeded demo data at
present; replace the in-memory fixtures with persisted Corporate models when
real employee, task, and announcement data is introduced.

| Method and endpoint | Purpose | Minimum response/request fields |
| --- | --- | --- |
| `POST /api/corporate/auth/login` | Sign in and create a session/token | request: `username`, `password`; response: `user`, `access_token`, `expires_at` |
| `POST /api/corporate/auth/logout` | End the session | `204 No Content` |
| `GET /api/corporate/me` | Current user and permissions | `id`, `name`, `email`, `role`, `department`, `last_login`, `permissions[]` |
| `GET /api/corporate/dashboard` | One request for initial dashboard load | `system_summary`, `my_tasks`, `announcements`, `activity`, `admin_summary?` |
| `GET /api/corporate/systems` | Detailed service-status list | `id`, `name`, `status`, `message`, `updated_at` |
| `GET /api/corporate/tasks?status=&limit=` | User task list | `items[]` with `id`, `title`, `status`, `due_at`, `priority` |
| `PATCH /api/corporate/tasks/{id}` | Update a task the user may edit | request: `status`; response: updated task |
| `GET /api/corporate/announcements` | Notices visible to the user | `items[]` with `id`, `title`, `body`, `severity`, `published_at` |
| `GET /api/corporate/activity?limit=` | Account/work activity timeline | `items[]` with `id`, `type`, `message`, `created_at` |
| `GET /api/corporate/admin/overview` | Administrator-only operational KPI data | `kpis`, `team_workload`, `access_review_count` |

All protected routes should use `Authorization: Bearer <token>` and return
`401` for an expired/missing session and `403` for a role restriction. Never
place passwords or access tokens in local storage; prefer secure HTTP-only
cookies if the deployment supports them.

## Frontend delivery plan

1. Build the shell and login flow using the current legacy endpoints or mocked
   fixtures.
2. Build the personal dashboard with loading, empty, error, and expired-session
   states.
3. Add admin-only sections behind a role/permission guard.
4. Replace fixture content with the dedicated Corporate API responses.
5. Test mobile, keyboard navigation, session expiry, and API failures before
   generating `frontend/corp_portal/dist/`.

## Definition of done

* No dashboard card invents a success state when its request has failed.
* Each card has loading, empty, and failure states.
* User navigation and API data are permission-aware.
* The build output is self-contained in `frontend/corp_portal/dist/`.
