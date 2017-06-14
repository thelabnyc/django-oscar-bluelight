#!/usr/bin/env bash

echo "Updating packages with yarn..."
NODE_ENV="dev" yarn
npm rebuild node-sass --force
echo "Done!"

exec $@
