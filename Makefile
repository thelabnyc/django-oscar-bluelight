# Minimal makefile for building static assets and selenium screen shots

DOCKERCOMPOSE = docker-compose

statics:
	@$(DOCKERCOMPOSE) run --rm -e NODE_ENV=production node webpack

screenshots:
	@$(DOCKERCOMPOSE) run --rm test python sandbox/manage.py test oscarbluelight
