#!/usr/bin/env bash

echo "Updating packages with yarn..."
NODE_ENV="dev" yarn
echo "Done!"

exec $@
