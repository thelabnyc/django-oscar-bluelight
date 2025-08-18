# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Django Oscar Bluelight is a Django package that extends Django Oscar's offers and vouchers system with advanced promotional features. This is a dual-language project with Python (Django) backend and TypeScript/React frontend components.

## Project Structure

### Dual Architecture
- **Server** (`/server/`): Django Python application with the main package in `oscarbluelight/`
- **Client** (`/client/`): TypeScript/React frontend components for dashboard interfaces
- **Dockerized Development**: Uses Docker Compose for development environment

### Key Components

#### Backend (`server/oscarbluelight/`)
- **offer/**: Core promotional offers logic with compound conditions and benefits
- **voucher/**: Enhanced voucher system with parent/child voucher codes
- **dashboard/**: Admin interface extensions for offers, vouchers, and ranges
- **mixins.py**: `BluelightBasketLineMixin` for basket line integration
- **caching.py**: Offer caching mechanisms
- **basket_utils.py**: Basket-related utility functions

#### Frontend (`client/src/`)
- **offergroups.tsx**: React component for managing offer groups
- Uses Webpack for bundling and builds to `server/oscarbluelight/static/`

### Sandbox Application
The `server/sandbox/` directory contains a test Django project that demonstrates Bluelight integration patterns, particularly in `basket/` and `partner/` apps.

## Development Commands

### Backend Commands
```bash
# Run tests
docker compose run --rm test python manage.py test oscarbluelight

# Type checking
tox -e py313-types
# or directly: mypy oscarbluelight sandbox

# Run full test matrix
tox

# Create migrations
docker compose run --rm test python manage.py makemigrations

# Coverage report
coverage run {toxinidir}/manage.py test oscarbluelight -v 2 --buffer --noinput
coverage report
```

### Frontend Commands
```bash
# Install dependencies and build assets
cd client && npm install

# Lint frontend code
npm run lint

# Build production assets
docker compose run --rm -e NODE_ENV=production node webpack

# Build assets via Makefile
make statics
```

### Additional Make Targets
```bash
make screenshots     # Run tests with screenshots
make migrations     # Create Django migrations
make translations   # Update translation files (.po/.mo)
```

## Testing

### Test Structure
- Backend tests in `oscarbluelight/tests/`
  - `offer/`: Tests for offer conditions, benefits, and compound logic
  - `voucher/`: Tests for voucher rules and parent/child relationships
- Uses Django's test framework with XML reporting (junit/)
- Extensive benefit and condition test coverage

### Running Specific Tests
```bash
# Run specific test module
python manage.py test oscarbluelight.tests.offer.test_benefit_compound

# Run with coverage
coverage run manage.py test oscarbluelight.tests.offer
```

## Key Architecture Concepts

### Compound Conditions and Benefits
Bluelight extends Oscar's single-condition offers with compound logic:
- **CompoundCondition**: Allows AND/OR logic combining multiple conditions
- **CompoundBenefit**: Enables complex benefit combinations
- Located in `offer/conditions.py` and `offer/benefits.py`

### Offer Groups
- `offer/groups.py`: System for organizing offers into logical groups
- Database model `OfferGroup` with slug-based organization
- Affects offer precedence and application logic

### Parent/Child Vouchers
- `voucher/models.py`: Bulk voucher code generation system
- Parent vouchers can generate unlimited child codes
- Child codes inherit parent properties but have unique codes
- CSV/JSON export capabilities

### Basket Integration
Projects using Bluelight must fork their basket app and add `BluelightBasketLineMixin` to their Line model for proper discount application.

## Configuration Notes

### Django Settings Integration
```python
from oscar.defaults import *
from oscarbluelight.defaults import *  # Must import Bluelight defaults

INSTALLED_APPS = [
    'oscarbluelight',  # Must come before 'oscar'
    'oscarbluelight.offer',     # Replaces 'oscar.apps.offer'
    'oscarbluelight.voucher',   # Replaces 'oscar.apps.voucher'
    'oscarbluelight.dashboard.offers',    # Replaces 'oscar.apps.dashboard.offers'
    'oscarbluelight.dashboard.vouchers',  # Replaces 'oscar.apps.dashboard.vouchers'
]
```

### Database Dependencies
- Requires PostgreSQL features (uses `thelabdb.pgviews`)
- Heavy use of database views and triggers for performance
- Migration files handle complex schema changes

## Linting and Code Quality

### Python (Backend)
- Uses `ruff` for linting and formatting
- `mypy` for type checking with Django stubs
- Configuration in `pyproject.toml`

### TypeScript (Frontend)
- ESLint configuration in `eslint.config.mjs`
- Standards from `@thelabnyc/standards`

## Common Workflows

When adding new offer conditions:
1. Create condition class in `offer/conditions.py`
2. Add database migration for new model
3. Add admin interface in `offer/admin.py`
4. Create dashboard form in `dashboard/offers/forms.py`
5. Add tests in `tests/offer/`

When modifying voucher logic:
1. Update models in `voucher/models.py`
2. Modify rules in `voucher/rules.py`
3. Update dashboard views in `dashboard/vouchers/`
4. Test parent/child relationships thoroughly

## Performance Considerations

- Offer application is cached via `caching.py`
- Range products use materialized views for performance
- Compound conditions can be expensive - test performance with large datasets
- Background tasks available via Celery integration (`tasks.py` files)
