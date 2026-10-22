#!/bin/bash
# Daily DB backup script — «Улица праздников».
# В cron, например: 0 3 * * * /opt/holidays/deploy/backup.sh
#
# Бэкап только через backup API sqlite3: cp при включённом WAL теряет
# данные из holiday.db-wal. После копии — проверка integrity_check.
set -euo pipefail

DB_FILE="/opt/holidays/api/holiday.db"
BACKUP_DIR="/opt/holidays/api/backups"
RETENTION_DAYS=7

PY_BIN="/opt/holidays/api/venv/bin/python"
[ -x "$PY_BIN" ] || PY_BIN="python3"

mkdir -p "$BACKUP_DIR"

if [ ! -f "$DB_FILE" ]; then
    echo "БД не найдена: $DB_FILE — бэкап не создан."
    exit 1
fi

BACKUP_PATH="$BACKUP_DIR/holiday.db.bak.$(date '+%Y%m%d_%H%M%S')"
"$PY_BIN" -c "import sqlite3,sys; s=sqlite3.connect(sys.argv[1]); d=sqlite3.connect(sys.argv[2]); s.backup(d); d.close(); s.close()" "$DB_FILE" "$BACKUP_PATH"
"$PY_BIN" -c "import sqlite3,sys; c=sqlite3.connect(sys.argv[1]); r=c.execute('PRAGMA integrity_check').fetchone()[0]; c.close(); sys.exit(0 if r=='ok' else 1)" "$BACKUP_PATH"
echo "Бэкап БД создан (WAL-safe, integrity ok): $BACKUP_PATH"

find "$BACKUP_DIR" -name "holiday.db.bak.*" -type f -mtime +$RETENTION_DAYS -delete
