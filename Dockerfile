# =============================================================================
# NodeJS Static Assets
# =============================================================================
FROM node:26@sha256:e18c3ccdf7d71619990b0e85639f506e2028a95410999cab24cc373cbd10e0ac AS client

RUN mkdir -p /oscarbluelight/server /oscarbluelight/client
WORKDIR /oscarbluelight/client

# So a swapped package needs a TLS break, not just an apt signature-check bug
RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources && \
    ! grep -rqsiE '^[^#]*http://' /etc/apt/sources.list /etc/apt/sources.list.d/

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
FROM registry.gitlab.com/thelabnyc/python:3.15@sha256:e8f93efa6a89cacc9dbe9cfff0cb0b7e0b596c5aeec9b23fedb5798b2e40a1fc AS server

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
