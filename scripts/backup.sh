#!/usr/bin/env bash
# Daily backup. Schedule via cron:
#   0 2 * * *  /path/scripts/backup.sh
set -euo pipefail
PROJECT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${BACKUP_DIR:-$PROJECT/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
STAMP="$(date -u +%Y-%m-%d_%H%M%S)"
ARCHIVE="$DEST/event-traffic-$STAMP.tar.gz"
mkdir -p "$DEST"

tar -czf "$ARCHIVE" -C "$PROJECT" \
  data/processed data/rag models logs

echo "wrote $ARCHIVE ($(du -h "$ARCHIVE" | cut -f1))"

# Prune older
find "$DEST" -name "event-traffic-*.tar.gz" -type f -mtime "+$RETENTION_DAYS" -delete
