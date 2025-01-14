#!/bin/sh
set -e

# Wipe database
python manage.py flush

# Create database
python manage.py migrate

# Make a user
python manage.py createsuperuser --username=root

# Import some fixtures
python manage.py loaddata _catalogue/child_products.json
python manage.py oscar_import_catalogue _catalogue/*.csv
python manage.py oscar_import_catalogue_images _catalogue/images.tar.gz
python manage.py oscar_populate_countries
python manage.py loaddata _fixtures/pages.json _fixtures/ranges.json _fixtures/offers.json
python manage.py loaddata _catalogue/orders.json
python manage.py clear_index --noinput
python manage.py update_index
