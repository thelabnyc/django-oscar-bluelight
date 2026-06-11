# =============================================================================
# NodeJS Static Assets
# =============================================================================
FROM node:24@sha256:9c1d881a5b3354362cd134d15b6eee789313833caa720c3cb6ea8862925d6eb8 AS client

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
ENV PATH=/oscarbluelight/client/node_modules/.bin:$PATH

# Add source
COPY client/ /oscarbluelight/client/

# Compile static assets
ENV NODE_ENV=production
RUN webpack

# Set entry point so that packages are always updated before compiling things
CMD ["webpack", "--watch"]


# =============================================================================
# Python / Django Application Server
# =============================================================================
FROM registry.gitlab.com/thelabnyc/python:3.14@sha256:423a0201e46bcdfa1cab79bb589e56c051c984508160b2ea78ea2de2e76eb4ae AS server

RUN mkdir -p /oscarbluelight/server /oscarbluelight/client
WORKDIR /oscarbluelight/server

RUN apt-get update && \
    apt-get install -y gettext && \
    rm -rf /var/lib/apt/lists/*

COPY server/ /oscarbluelight/server/
RUN uv sync --all-extras
ENV PATH="/oscarbluelight/server/.venv/bin:$PATH"

RUN mkdir /oscarbluelight/tox
ENV TOX_WORK_DIR='/oscarbluelight/tox'

# Set entry point so that packages are always updated before compiling things
CMD ["python", "manage.py", "runserver"]
