#!/bin/bash
# Atlas Backup Restore Script
# Created: 2025-09-15T16:47:43.153932

BACKUP_DIR="backup_baseline_20250915_164736"
ARCHIVE_FILE="atlas_baseline_backup_20250915_164743.tar.gz"

echo "🔄 Restoring Atlas from backup: $BACKUP_DIR"
echo "⚠️  This will overwrite current system files!"
read -p "Continue? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Extract backup
    tar -xzf $ARCHIVE_FILE

    # Restore database
    if [ -f "$BACKUP_DIR/data/atlas.db" ]; then
        cp "$BACKUP_DIR/data/atlas.db" data/atlas.db
        echo "✅ Database restored"
    fi

    # Restore configs
    if [ -d "$BACKUP_DIR/config" ]; then
        cp -r "$BACKUP_DIR/config/"* . 2>/dev/null || true
        echo "✅ Configs restored"
    fi

    # Restore scripts
    if [ -d "$BACKUP_DIR/scripts" ]; then
        cp -r "$BACKUP_DIR/scripts/"* . 2>/dev/null || true
        echo "✅ Scripts restored"
    fi

    echo "✅ Restore complete!"
    echo "📊 System restored to backup timestamp: 2025-09-15T16:47:43.153956"
else
    echo "❌ Restore cancelled"
fi
