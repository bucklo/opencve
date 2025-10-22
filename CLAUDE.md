# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OpenCVE is a Vulnerability Intelligence Platform built with Django (web application) and Apache Airflow (data processing scheduler). It aggregates CVE data from multiple sources (MITRE, NVD, RedHat, Vulnrichment) and provides tools for monitoring, filtering, and receiving alerts about vulnerabilities.

## Architecture

The project consists of two main components:

### 1. Web Application (`web/`)
- **Framework**: Django 5.2.1
- **Database**: PostgreSQL with Prometheus metrics
- **Key Apps**:
  - `cves`: Core CVE listing, filtering, and detail views
  - `organizations`: Multi-tenancy support with organizations and memberships
  - `projects`: Project-based CVE subscriptions (vendors/products)
  - `users`: Custom user model with tags for CVE classification
  - `views`: Saved search queries (public/private)
  - `dashboards`: Customizable widget-based dashboards
  - `changes`: CVE change history and daily reports
  - `onboarding`: User onboarding flow
- **API**: Django REST Framework with nested routers for hierarchical resources
- **Authentication**: Django Allauth with social account support
- **Settings**: `web/opencve/conf/base.py` (base settings) + `web/opencve/conf/settings.py` (local overrides) + `web/opencve/conf/.env` (environment variables with `OPENCVE_` prefix)

### 2. Scheduler (`scheduler/`)
- **Framework**: Apache Airflow 2.10.4 with Celery executor
- **Main DAG** (`scheduler/dags/opencve_dag.py`): Runs hourly to:
  1. Fetch updates from 5 Git repositories (KB, MITRE, NVD, RedHat, Vulnrichment)
  2. Process CVE data and compute statistics
  3. Generate daily reports by project
  4. Send notifications (email/webhook)
- **Other DAGs**:
  - `summarize_reports_dag.py`: Uses OpenAI to generate AI summaries of reports
  - `check_smtp_dag.py`: SMTP health checks
- **Task Organization**: Uses `includes/` directory for operators, tasks, and utilities
- **Data Flow**: Git repos → Process KB → Statistics → Reports → Notifications

## Common Development Commands

### Web Application

```bash
cd web

# Setup environment
cp opencve/conf/settings.py.example opencve/conf/settings.py
cp opencve/conf/.env.example opencve/conf/.env
pip install -r requirements.txt

# Database migrations
python manage.py migrate
python manage.py check

# Run development server
python manage.py runserver

# Create superuser
python manage.py createsuperuser

# Generate new secret key
python manage.py generate_secret_key

# Run tests
pip install -r tests/requirements.txt
pytest tests/ -v

# Run specific test file
pytest tests/cves/test_models.py -v

# Run specific test
pytest tests/cves/test_models.py::test_cve_creation -v

# Collect static files
python manage.py collectstatic
```

### Scheduler

```bash
cd scheduler

# Install dependencies
pip install -r requirements.txt
pip install pytest==8.3.2  # for testing

# Run tests
pytest tests/ -v

# Note: Airflow is typically run via Docker (see docker-compose.yaml)
```

### Docker Development

```bash
cd docker

# Start all services (web, scheduler, postgres, redis, nginx)
docker-compose up -d

# View logs
docker-compose logs -f webserver
docker-compose logs -f airflow-scheduler

# Access Airflow web UI
# http://localhost:8080 (default credentials: airflow/airflow)

# Access OpenCVE web UI
# http://localhost:80
```

### Code Quality

```bash
# Run pre-commit hooks manually
pre-commit run --all-files

# Install pre-commit hooks
pre-commit install
pre-commit install --hook-type commit-msg

# Format code (black is used for Python formatting)
black .
```

## Key Data Models

### CVE Storage
- CVEs are stored using a PostgreSQL stored procedure `cve_upsert()` that handles atomic updates
- Changes are tracked with JSON arrays containing commit hashes and event types
- Multiple data sources are merged with priority: Vulnrichment > RedHat > NVD > MITRE

### Organizations & Projects
- Multi-tenant architecture: Users belong to Organizations via Memberships (OWNER/MEMBER roles)
- Projects within Organizations subscribe to vendors/products for monitoring
- Subscriptions format: `{'vendors': [...], 'products': [...]}` where products use `vendor$PRODUCT$product` format

### Notifications
- Configured per-project with types: email, webhook (Slack/Teams coming soon)
- Daily reports are generated and queued for notification delivery
- Notifications are chunked and sent asynchronously via Airflow

### User Tags
- Users can tag CVEs (e.g., "unread", "critical", "assigned-to-dev")
- Tags are scoped to (user, organization, CVE)

## Testing Patterns

Tests use pytest with Django integration:
- **Fixtures** (in `web/tests/conftest.py`): `create_user`, `create_organization`, `create_project`, `create_cve`, etc.
- **Test Data**: JSON fixtures in `web/tests/data/kb/` mirror the KB repository structure
- **CVE Creation**: Uses the same `cve_upsert()` stored procedure as production
- **Auth**: `auth_client` fixture for authenticated test requests
- Default test password: "password"

## Repository Paths

The application requires local clones of several Git repositories (configured via environment variables):
- `OPENCVE_KB_REPO_PATH`: opencve-kb (internal knowledge base)
- `OPENCVE_MITRE_REPO_PATH`: cvelistV5 (official MITRE CVE list)
- `OPENCVE_NVD_REPO_PATH`: opencve-nvd (NVD data)
- `OPENCVE_REDHAT_REPO_PATH`: opencve-redhat (RedHat advisories)
- `OPENCVE_VULNRICHMENT_REPO_PATH`: vulnrichment (enriched CVE data)

These are mounted as Docker volumes in production and accessed by Airflow tasks.

## Important Conventions

- **Commit Messages**: Use Conventional Commits format (enforced by pre-commit hook)
- **Code Style**: Black formatter with default settings (enforced by pre-commit)
- **Python Version**: 3.10+ required
- **Environment Variables**: All custom variables use `OPENCVE_` prefix
- **Audit Logs**: Automatically tracked for Organizations, Projects, Dashboards, Users, etc. via django-auditlog
- **Metrics**: Prometheus metrics exposed at `/metrics` endpoint

## Webhook Notifications

Webhook notifications allow OpenCVE to send CVE alerts via HTTP POST to external endpoints.

### Quick Reference:
- **Location**: Projects → Notifications → Add Notification → Webhook
- **Configuration**: URL + optional headers (JSON) for authentication
- **Testing**: "Test Webhook" button sends sample payload
- **Scheduler**: `scheduler/dags/includes/notifiers.py` - `WebhookNotifier` class
- **Web Forms**: `web/projects/forms.py` - `WebhookForm` class
- **Documentation**: See `WEBHOOKS.md` for complete payload schema and examples

### Payload Structure:
```json
{
  "organization": "...",
  "project": "...",
  "notification": "...",
  "changes": [
    {
      "cve": {
        "cve_id": "CVE-2024-1234",
        "description": "...",
        "cvss31": 7.5
      },
      "events": [{"type": "metrics", "data": {...}}]
    }
  ]
}
```

## Troubleshooting

- If tests fail with database errors, ensure PostgreSQL is running and `OPENCVE_DATABASE_URL` is set correctly
- For Airflow issues, check that Redis and PostgreSQL services are healthy in docker-compose
- The web app requires KB repository path even for basic operations - use test data path from conftest.py for local dev
- Django Debug Toolbar is enabled for `INTERNAL_IPS` (default: 127.0.0.1)
- Webhook test failures: Ensure endpoint is accessible, returns HTTP 200, and accepts JSON POST requests
