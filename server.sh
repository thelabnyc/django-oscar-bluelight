#!/bin/sh

cd sandbox
exec python3 manage.py runserver 0.0.0.0:8000
