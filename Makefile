.PHONY: statics screenshots translations install_precommit test_precommit fmt fmt_client fmt_server

DOCKERCOMPOSE = docker-compose

statics:
	@$(DOCKERCOMPOSE) run --rm -e NODE_ENV=production node webpack

screenshots:
	@$(DOCKERCOMPOSE) run --rm test python sandbox/manage.py test oscarbluelight

migrations:
	@$(DOCKERCOMPOSE) run --rm test python sandbox/manage.py makemigrations

# Create the .po and .mo files used for i18n
translations:
	cd client/src && \
	django-admin makemessages --locale=es --extension=ts,tsx --domain djangojs && \
	cd ../../server/src/oscarbluelight && \
	django-admin makemessages --locale=es && \
	django-admin compilemessages

install_precommit:
	pre-commit install

test_precommit: install_precommit
	pre-commit run --all-files

fmt_client:
	cd client && \
	yarn prettier --no-color --write .

fmt_server:
	black .

fmt: fmt_client fmt_server
