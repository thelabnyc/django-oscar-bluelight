.PHONY: statics screenshots translations

DOCKERCOMPOSE = docker compose

statics:
	@$(DOCKERCOMPOSE) run --rm -e NODE_ENV=production node webpack

screenshots:
	@$(DOCKERCOMPOSE) run --rm test python manage.py test oscarbluelight

migrations:
	@$(DOCKERCOMPOSE) run --rm test python manage.py makemigrations

# Create the .po and .mo files used for i18n
translations:
	cd client/src && \
	django-admin makemessages --locale=es --extension=ts,tsx --domain djangojs && \
	cd ../../server/oscarbluelight && \
	django-admin makemessages --locale=es && \
	django-admin compilemessages
