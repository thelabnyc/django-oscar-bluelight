# =============================================================================
# NodeJS Static Assets
# =============================================================================
FROM node:22@sha256:afff6d8c97964a438d2e6a9c96509367e45d8bf93f790ad561a1eaea926303d9 AS client

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
FROM registry.gitlab.com/thelabnyc/python:3.13.970@sha256:620114e732e448d14e809d37b28f77757ab22c2b2112aa2fb9cd8caf85dbc583 AS server

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
