# =============================================================================
# NodeJS Static Assets
# =============================================================================
FROM node:22@sha256:71bcbb3b215b3fa84b5b167585675072f4c270855e37a599803f1a58141a0716 as client

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
FROM registry.gitlab.com/thelabnyc/python:3.13.766@sha256:281d5d17fa4c1b41c70ec718cb8991c32730d36ccbbb817601254e648c498b04 as server

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
