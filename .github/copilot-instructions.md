# Copilot Instructions for SCART Quotation

## Project Overview
SCART Quotation is a Python-based application for managing quotations, products, customers, and user permissions. The codebase is organized into modular components for models, routes, services, and templates, supporting both business logic and web UI.

## Architecture & Key Components
- **app/**: Main application package.
  - **db/models/**: Database models (e.g., `customer.py`, `product.py`, `quotation.py`).
  - **routes/**: Flask route handlers for each domain (e.g., `product.py`, `quotation.py`).
  - **services/**: Business logic and integrations (e.g., `notifications.py`).
  - **static/** & **templates/**: Web assets and Jinja2 templates.
- **scripts/**: Utility scripts for admin, testing, and migration tasks.
- **tools/**: One-off migration and schema update scripts.
- **build/**: PyInstaller build outputs.

## Developer Workflows
- **Run the app**: Use `run.py` for local development.
- **Database migrations**: Use scripts in `scripts/` and `tools/` (e.g., `db_create.py`, `upgrade_add_product_cost.py`).
- **Testing**: Run tests via scripts like `scripts/run_tests.py` or specific test scripts (e.g., `test_permissions.py`).
- **CI/CD**: GitHub Actions workflows can be triggered with `gh workflow run SCART Tests --ref main --field name=permissions`.
- **Debugging**: Use `debug_db_schema.py` and `db_check.py` for schema and data inspection.

## Project-Specific Patterns
- **Database Access**: Models in `app/db/models/` use SQLite and custom logic; inspect model files for relationships and constraints.
- **Routes**: Each domain (product, quotation, customer) has a dedicated route file in `app/routes/`.
- **Templates**: Jinja2 templates are split between `app/templates/` and top-level `templates/` for legacy and new UI.
- **Admin/User Management**: Scripts like `check_admin_pw.py`, `reset_admin.py`, and `reset_test_users.py` are used for user state management.
- **Error Handling**: Custom error pages in `app/templates/` (e.g., `403.html`, `404.html`, `500.html`).

## Integration Points
- **External**: Uses `sqlite3` (see `import sqlite3.ini` for config), and may integrate with notification services via `app/services/notifications.py`.
- **Builds**: PyInstaller specs (`scart_quotation.spec`, `SCARTQuotation.spec`) define build targets.

## Conventions
- **Scripts**: Prefer running scripts from the `scripts/` directory for admin and test tasks.
- **Naming**: Models, routes, and templates follow domain-based naming (e.g., `customer_approval_log.py`, `quotation_list.html`).
- **Testing**: Test scripts are named `test_*.py` and reside in `scripts/`.

## Examples
- To add a new product field, update `app/db/models/product.py`, create a migration script in `tools/`, and update relevant templates in `app/templates/`.
- To run all tests: `python scripts/run_tests.py`
- To build: Use PyInstaller spec files in the root directory.

## Key Files & Directories
- `app/db/models/` — Data models
- `app/routes/` — API and web routes
- `scripts/` — Admin, migration, and test scripts
- `app/templates/` & `templates/` — UI templates
- `build/` — Build outputs

---
_If any section is unclear or missing, please provide feedback for further refinement._
