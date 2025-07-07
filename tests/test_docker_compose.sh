#!/bin/bash
set -e

# Build the image
docker compose build

# Start the service in the background
docker compose up -d

# Wait for the server to start
sleep 10

# Run a simple SPARQL query
curl -s -X POST \
  --data 'query=SELECT * WHERE { ?s ?p ?o } LIMIT 1' \
  -H "Content-Type: application/x-www-form-urlencoded" \
  http://localhost:3031/royals/sparql

# Stop the service
docker compose down