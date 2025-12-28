rm -f "$SQLITE_DB_PATH"
sqlite3 "$SQLITE_DB_PATH" < sql/schema.sql
