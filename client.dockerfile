FROM node:10

RUN mkdir -p /oscarbluelight/server /oscarbluelight/client
WORKDIR /oscarbluelight/client

# Install node_modules
ADD client/package.json /oscarbluelight/client/package.json
ADD client/yarn.lock /oscarbluelight/client/yarn.lock
RUN yarn
VOLUME /oscarbluelight/client/node_modules

# Include NPM's .bin directory in the sys path
ENV PATH /oscarbluelight/client/node_modules/.bin:$PATH
ENV NODE_ENV production

# Add source
ADD client/ /oscarbluelight/client/

# Set entry point so that packages are always updated before compiling things
ENTRYPOINT ["/oscarbluelight/client/entrypoint.sh"]
CMD ["webpack", "--watch"]
