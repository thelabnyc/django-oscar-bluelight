# =============================================================================
# NodeJS Static Assets
# =============================================================================
FROM node:22@sha256:74066d050011dd18c56390523cb255b38bce09b332221a4ec15ab0d8e1ac61fe as client

RUN mkdir -p /oscarbluelight/server /oscarbluelight/client
WORKDIR /oscarbluelight/client

RUN apt-get update && \
    apt-get install -y gettext && \
    rm -rf /var/lib/apt/lists/*

# Install node_modules
COPY client/package.json /oscarbluelight/client/package.json
COPY client/package-lock.json /oscarbluelight/client/package-lock.json
RUN npm ci
VOLUME /oscarbluelight/client/node_modules

# Include NPM's .bin directory in the sys path
ENV PATH /oscarbluelight/client/node_modules/.bin:$PATH

# Add source
COPY client/ /oscarbluelight/client/

# Compile static assets
ENV NODE_ENV production
RUN webpack

# Set entry point so that packages are always updated before compiling things
ENTRYPOINT ["/oscarbluelight/client/entrypoint.sh"]
CMD ["webpack", "--watch"]


# =============================================================================
# Python / Django Application Server
# =============================================================================
FROM registry.gitlab.com/thelabnyc/python:3.13.686@sha256:a63b93e18b1148955f237c55ec8aa45a9ab503ee3d3652900d9fdef57c64b67d as server

RUN mkdir -p /oscarbluelight/server /oscarbluelight/client
WORKDIR /oscarbluelight/server

RUN apt-get update && \
    apt-get install -y gettext && \
    rm -rf /var/lib/apt/lists/*

COPY server/ /oscarbluelight/server/
RUN poetry install

RUN mkdir /oscarbluelight/tox
ENV TOX_WORK_DIR='/oscarbluelight/tox'

# Set entry point so that packages are always updated before compiling things
ENTRYPOINT ["/oscarbluelight/server/entrypoint.sh"]
CMD ["python", "manage.py", "runserver"]
