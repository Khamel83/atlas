#!/bin/bash

# Atlas API Runner Script
# Handles directory change and environment loading

cd /home/ubuntu/dev/atlas

# Load environment variables if .env exists
if [ -f .env ]; then
    export $(cat .env | grep -v ^# | xargs)
fi

# Start the API
exec /usr/bin/python3 api.py