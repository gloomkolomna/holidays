#!/bin/bash
# Daily DB backup script — «Улица праздников».
# В cron, например: 0 3 * * * /opt/holidays/deploy/backup.sh
DB_FILE="/opt/holidays/api/holiday.db"
BACKUP_DIR="/opt/holidays/api/backups"
RETENTION_DAYS=7

mkdir -p "$BACKUP_DIR"
BACKUP_PATH="$BACKUP_DIR/holiday.db.bak.$(date '+%Y%m%d_%H%M%S')"
cp "$DB_FILE" "$BACKUP_PATH"

find "$BACKUP_DIR" -name "holiday.db.bak.*" -type f -mtime +$RETENTION_DAYS -delete
