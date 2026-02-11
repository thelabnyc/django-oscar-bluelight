# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ Critical Requirement

**ALL backend Python commands (tests, mypy, tox, manage.py, etc.) MUST be run inside Docker containers via `docker compose run --rm test ...`**

This project requires PostgreSQL and Redis, which are only available inside the Docker environment. Never run Python commands directly on the host machine.

## Project Overview

Django Oscar Bluelight is a Django package that extends Django Oscar's offers and vouchers system with advanced promotional features. It's a dual-language project with Python (Django) backend and TypeScript/React frontend components, distributed as a pip-installable package.

## Project Structure

### Dual Architecture
- **Server** (`/server/`): Django Python application with the main package in `server/oscarbluelight/`
- **Client** (`/client/`): TypeScript/React frontend components for dashboard interfaces
- **Dockerized Development**: Uses Docker Compose with separate services for postgres, redis, node, and test

### Key Backend Components (`server/oscarbluelight/`)
- **offer/**: Core promotional offers logic
  - `conditions.py` / `benefits.py`: Compound conditions and benefits with AND/OR logic
  - `groups.py`: Offer group organization affecting precedence
  - `results.py`: Offer application result structures
  - `signals.py`: Django signals for offer lifecycle events
- **voucher/**: Enhanced voucher system with parent/child voucher codes
  - `models.py`: Parent voucher bulk generation system
  - `rules.py`: Voucher validation and application rules
- **dashboard/**: Admin interface extensions for offers, vouchers, and ranges
  - `offers/`, `vouchers/`, `ranges/`: Dashboard apps with forms, views, and API endpoints
  - Uses Django REST Framework for API serialization
- **caching.py**: Offer caching mechanisms
- **mixins.py**: `BluelightBasketLineMixin` for basket line integration (required in consumer projects)

### Frontend (`client/src/`)
- React components for dashboard UI, primarily `offergroups.tsx`
- Webpack bundles output to `server/oscarbluelight/static/`
- Uses TypeScript, Babel, and SCSS

### Sandbox Application
`server/sandbox/` contains a complete Django Oscar site demonstrating Bluelight integration patterns, particularly:
- `basket/`: Shows how to fork basket app and add `BluelightBasketLineMixin`
- `partner/`: Example partner app integration
- `settings.py`: Example settings configuration with correct app ordering

## Development Commands

**IMPORTANT**: All backend/Python commands MUST be run inside Docker containers via `docker compose`. This ensures PostgreSQL and Redis dependencies are available and the correct Python environment is used. Commands assume you're in the repository root.

### Backend Testing and Quality
```bash
# Run all tests
docker compose run --rm test python manage.py test oscarbluelight

# Run specific test module or class
docker compose run --rm test python manage.py test oscarbluelight.tests.offer.test_benefit_compound
docker compose run --rm test python manage.py test oscarbluelight.tests.voucher.test_vouchers.TestVoucher

# Run tests with coverage
docker compose run --rm test bash -c "coverage run manage.py test oscarbluelight -v 2 --buffer --noinput && coverage report"

# Type checking with mypy
docker compose run --rm test mypy oscarbluelight sandbox
# or via tox:
docker compose run --rm test bash -c "cd /oscarbluelight/server && tox -e py313-types"

# Run full tox test matrix (tests against Django 4.2/5.2, DRF 3.16, Oscar 4.0/4.1)
docker compose run --rm test bash -c "cd /oscarbluelight/server && tox"
```

### Frontend Development
```bash
# Install dependencies (from repository root)
cd client && npm install

# Lint TypeScript/React code
cd client && npm run lint

# Build production assets
docker compose run --rm -e NODE_ENV=production node webpack
# or: make statics

# Watch mode for development (rebuilds on file changes)
docker compose up node
```

### Database Migrations
```bash
# Create new migrations after model changes
docker compose run --rm test python manage.py makemigrations
# or: make migrations

# Apply migrations in sandbox
docker compose run --rm test python manage.py migrate
```

### Running the Sandbox Development Server
```bash
# Start sandbox site with dependencies
docker compose up test

# Access at http://localhost:8000
# Admin credentials are typically created via bootstrap.sh
```

### Translations
```bash
# Update translation files (.po) and compile (.mo)
make translations
# Processes both client TypeScript and server Python files for Spanish locale
```

## Testing

**IMPORTANT**: All tests MUST be run via Docker Compose to ensure PostgreSQL and Redis are available.

### Test Structure
- Tests located in `server/oscarbluelight/tests/`
  - `offer/`: Extensive tests for offer conditions, benefits, compound logic, groups, and API
  - `voucher/`: Tests for voucher rules and parent/child relationships
- Uses Django's test framework with unittest-xml-reporting for XML output (junit/)
- Tests run against PostgreSQL and Redis via Docker Compose
- Tox matrix tests against multiple Django/Oscar versions
- Run tests via: `docker compose run --rm test python manage.py test oscarbluelight`
- Run full tox suite via: `docker compose run --rm test bash -c "cd /oscarbluelight/server && tox"`

## Key Architecture Concepts

### Compound Conditions and Benefits
Bluelight extends Oscar's single-condition offers with compound logic:
- **CompoundCondition** (`offer/conditions.py`): Allows AND/OR logic combining multiple conditions
  - Can nest conditions to arbitrary depth
  - Supports both conjunctive (AND) and disjunctive (OR) logic
- **CompoundBenefit** (`offer/benefits.py`): Enables complex benefit combinations
  - Allows multiple benefits to be applied from a single offer
  - Benefits can be combined with different application strategies

### Offer Groups
- **OfferGroup** model (`offer/groups.py`): System for organizing offers into logical groups
  - Slug-based organization for easy identification
  - Controls offer precedence and application order
  - Offers can belong to multiple groups
  - Groups affect which offers are evaluated together

### Parent/Child Vouchers
- **Parent/Child System** (`voucher/models.py`): Bulk voucher code generation
  - Parent vouchers generate unlimited unique child codes
  - Child codes inherit all properties (benefits, conditions, dates) from parent
  - Automatic code generation ensures uniqueness
  - CSV/JSON export for distribution
  - Parent modifications cascade to all children
  - Parent vouchers cannot be applied directly (only children)

### Group-Restricted Vouchers
- Vouchers can be restricted to specific `django.contrib.auth.models.Group` memberships
- Useful for customer service reps or VIP customer codes
- Validation happens in `voucher/rules.py`

### Basket Integration Requirement
**CRITICAL**: Consumer projects must fork their basket app and add `BluelightBasketLineMixin` to their `Line` model:
```python
from oscar.apps.basket.abstract_models import AbstractLine
from oscarbluelight.mixins import BluelightBasketLineMixin

class Line(BluelightBasketLineMixin, AbstractLine):
    pass
```
This mixin is required for proper discount tracking and application. See `server/sandbox/basket/models.py` for reference implementation.

## Configuration Notes

### Django Settings Integration
Consumer projects must follow this setup pattern (see `server/sandbox/settings.py` for complete example):
```python
from oscar.defaults import *
from oscarbluelight.defaults import *  # Required for dashboard view registration

INSTALLED_APPS = [
    # Bluelight must come before 'oscar' for template inheritance
    'oscarbluelight',
    'thelabdb.pgviews',  # Required for PostgreSQL views

    'oscar',
    # ... other Oscar apps ...

    # Replace these Oscar apps with Bluelight versions:
    'oscarbluelight.offer',              # instead of 'oscar.apps.offer'
    'oscarbluelight.voucher',            # instead of 'oscar.apps.voucher'
    'oscarbluelight.dashboard.offers',   # instead of 'oscar.apps.dashboard.offers'
    'oscarbluelight.dashboard.vouchers', # instead of 'oscar.apps.dashboard.vouchers'
]
```

### Database Dependencies
- **PostgreSQL Required**: Uses `thelabdb.pgviews` for materialized views
- Range product sets (`RangeProductSet` model) use database views for performance
- Migrations include complex schema changes, triggers, and view definitions
- Development environment uses PostgreSQL via Docker Compose

## Code Quality Tools

**REMINDER**: All Python/backend quality tools must be run via `docker compose run --rm test ...`

### Python
- **ruff**: Linting and formatting (configuration in `server/pyproject.toml`)
  - Run via: `docker compose run --rm test ruff check oscarbluelight`
- **mypy**: Type checking with django-stubs and djangorestframework-stubs
  - Run via: `docker compose run --rm test mypy oscarbluelight sandbox`
  - Strict mode enabled with specific overrides for Oscar and migrations
  - Django settings module: `sandbox.settings`
- **coverage**: Test coverage tracking with branch coverage enabled
  - Run via: `docker compose run --rm test bash -c "coverage run manage.py test oscarbluelight && coverage report"`
- **tox**: Multi-environment testing (Django 4.2/5.2, Oscar 4.0/4.1)
  - Run via: `docker compose run --rm test bash -c "cd /oscarbluelight/server && tox"`

### TypeScript/Frontend
- **ESLint**: Linting with `@thelabnyc/standards` configuration
  - Configuration in `client/eslint.config.mjs`
  - Run via: `cd client && npm run lint`
- **TypeScript**: Strict type checking for React components
- **Prettier**: Code formatting (via @thelabnyc/standards)

## Common Workflows

### Adding New Offer Conditions
1. Create condition class in `server/oscarbluelight/offer/conditions.py`
2. Generate database migration: `docker compose run --rm test python manage.py makemigrations`
3. Add admin interface in `server/oscarbluelight/offer/admin.py`
4. Create dashboard form in `server/oscarbluelight/dashboard/offers/forms.py`
5. Add comprehensive tests in `server/oscarbluelight/tests/offer/`
6. Update type hints if using typed code

### Adding New Benefit Types
1. Create benefit class in `server/oscarbluelight/offer/benefits.py`
2. Follow similar migration and admin steps as conditions
3. Test application logic thoroughly with various basket configurations
4. Verify interaction with compound benefits

### Modifying Voucher Logic
1. Update models in `server/oscarbluelight/voucher/models.py`
2. Modify validation rules in `server/oscarbluelight/voucher/rules.py`
3. Update dashboard views/forms in `server/oscarbluelight/dashboard/vouchers/`
4. **Critical**: Test parent/child relationships thoroughly
5. Verify group restrictions and cascade behavior

### Frontend Dashboard Changes
1. Modify React components in `client/src/`
2. Run `cd client && npm run lint` to check for issues
3. Build assets: `docker compose run --rm -e NODE_ENV=production node webpack`
4. Test in sandbox dashboard at http://localhost:8000/dashboard/

## Performance Considerations

- **Offer Caching**: Offer application is cached via `caching.py` to avoid redundant calculations
- **Database Views**: Range products use PostgreSQL materialized views (`RangeProductSet`) for fast lookups
- **Compound Conditions**: Can be expensive with deep nesting - benchmark with realistic basket sizes
- **Background Tasks**: Uses django-tasks for async operations (required dependency)
- **Parent Voucher Updates**: Bulk child voucher updates can be slow - consider async tasks for large volumes

## Package Distribution

- Built with hatchling (PEP 517)
- Version: Managed in `server/pyproject.toml`
- Package name: `django-oscar-bluelight` (PyPI)
- Includes both Python package and bundled static assets
- Custom PyPI index for thelabnyc dependencies: `https://gitlab.com/api/v4/groups/269576/-/packages/pypi/simple`
