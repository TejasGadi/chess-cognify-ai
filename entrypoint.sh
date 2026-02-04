#!/bin/bash
set -e

# Function to wait for Postgres
function wait_for_postgres() {
    echo "Waiting for Postgres to be ready..."
    until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "${POSTGRES_DB:-chess_cognify}"; do
        echo "Postgres is unavailable - sleeping"
        sleep 2
    done
    echo "Postgres is up - executing command"
}

# Wait for DB
wait_for_postgres

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Start application
echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
