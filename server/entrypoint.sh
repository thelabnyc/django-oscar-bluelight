#!/usr/bin/env bash

echo "Updating packages with pip..."
pip install -e .[development]
echo "Done!"

exec $@
