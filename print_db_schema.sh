#!/bin/bash

# Change these if needed
DB_NAME="aquastock"
DB_USER="username"      # Your PostgreSQL username
DB_HOST="localhost"
DB_PORT="5432"

echo "📦 Listing all tables in '$DB_NAME'..."
echo

# List all tables
PGPASSWORD="password" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\dt"

echo
echo "🔍 Printing columns for each table..."
echo

# Get list of user tables (public schema)
tables=$(PGPASSWORD="password" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -Atc \
  "SELECT tablename FROM pg_tables WHERE schemaname='public';")

# Loop through each table and describe it
for table in $tables; do
  echo "📄 Table: $table"
  PGPASSWORD="password" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "\d $table"
  echo "--------------------------------------------"
done
