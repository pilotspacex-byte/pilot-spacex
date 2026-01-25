#!/usr/bin/env bash
# =============================================================================
# Pilot Space - Database Backup Script
# =============================================================================
# Automated backup for Pilot Space Supabase PostgreSQL database.
#
# Usage:
#   ./scripts/backup.sh                    # Backup to default location
#   ./scripts/backup.sh /path/to/backups   # Backup to custom location
#   ./scripts/backup.sh --s3               # Upload to S3 (requires AWS CLI)
#
# Cron example (daily at 2 AM):
#   0 2 * * * /path/to/infra/supabase/scripts/backup.sh >> /var/log/pilot-space-backup.log 2>&1
# =============================================================================

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${1:-${PROJECT_DIR}/backups}"
CONTAINER_NAME="pilot-space-db"
DB_USER="${POSTGRES_USER:-supabase_admin}"
DB_NAME="${POSTGRES_DB:-postgres}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"
S3_BUCKET="${BACKUP_S3_BUCKET:-}"

# Timestamp for backup file
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="pilot-space-backup_${TIMESTAMP}.sql.gz"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] ${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] ${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] ${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "[$(date +'%Y-%m-%d %H:%M:%S')] ${RED}[ERROR]${NC} $1"
}

# Check if container is running
check_container() {
    if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        log_error "Container ${CONTAINER_NAME} is not running"
        exit 1
    fi
}

# Create backup directory
create_backup_dir() {
    if [[ ! -d "$BACKUP_DIR" ]]; then
        mkdir -p "$BACKUP_DIR"
        log_info "Created backup directory: ${BACKUP_DIR}"
    fi
}

# Perform backup
perform_backup() {
    log_info "Starting backup of ${DB_NAME} database..."

    # Create backup with pg_dump
    docker exec "$CONTAINER_NAME" pg_dump \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --format=plain \
        --no-owner \
        --no-acl \
        --clean \
        --if-exists \
        | gzip > "${BACKUP_DIR}/${BACKUP_FILE}"

    if [[ $? -eq 0 ]]; then
        local size=$(du -h "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)
        log_success "Backup created: ${BACKUP_FILE} (${size})"
    else
        log_error "Backup failed"
        exit 1
    fi
}

# Upload to S3 (optional)
upload_to_s3() {
    if [[ -n "$S3_BUCKET" ]]; then
        log_info "Uploading backup to S3: s3://${S3_BUCKET}/"

        if command -v aws &> /dev/null; then
            aws s3 cp "${BACKUP_DIR}/${BACKUP_FILE}" "s3://${S3_BUCKET}/${BACKUP_FILE}"
            log_success "Backup uploaded to S3"
        else
            log_warn "AWS CLI not installed, skipping S3 upload"
        fi
    fi
}

# Clean up old backups
cleanup_old_backups() {
    log_info "Cleaning up backups older than ${RETENTION_DAYS} days..."

    local count=$(find "$BACKUP_DIR" -name "pilot-space-backup_*.sql.gz" -mtime +${RETENTION_DAYS} | wc -l)

    if [[ $count -gt 0 ]]; then
        find "$BACKUP_DIR" -name "pilot-space-backup_*.sql.gz" -mtime +${RETENTION_DAYS} -delete
        log_info "Deleted ${count} old backup(s)"
    else
        log_info "No old backups to delete"
    fi
}

# Verify backup integrity
verify_backup() {
    log_info "Verifying backup integrity..."

    if gzip -t "${BACKUP_DIR}/${BACKUP_FILE}" 2>/dev/null; then
        log_success "Backup integrity verified"
    else
        log_error "Backup file is corrupted!"
        exit 1
    fi
}

# Show backup stats
show_stats() {
    echo ""
    log_info "Backup Statistics:"
    echo "  Location: ${BACKUP_DIR}/${BACKUP_FILE}"
    echo "  Size: $(du -h "${BACKUP_DIR}/${BACKUP_FILE}" | cut -f1)"
    echo "  Total backups: $(ls -1 "${BACKUP_DIR}"/pilot-space-backup_*.sql.gz 2>/dev/null | wc -l)"
    echo "  Oldest: $(ls -1t "${BACKUP_DIR}"/pilot-space-backup_*.sql.gz 2>/dev/null | tail -1 | xargs basename 2>/dev/null || echo 'N/A')"
    echo "  Newest: $(ls -1t "${BACKUP_DIR}"/pilot-space-backup_*.sql.gz 2>/dev/null | head -1 | xargs basename 2>/dev/null || echo 'N/A')"
}

# Main
main() {
    log_info "=== Pilot Space Database Backup ==="

    # Handle S3 flag
    if [[ "${1:-}" == "--s3" ]]; then
        S3_BUCKET="${BACKUP_S3_BUCKET:-$2}"
        shift
    fi

    check_container
    create_backup_dir
    perform_backup
    verify_backup
    upload_to_s3
    cleanup_old_backups
    show_stats

    log_success "=== Backup Complete ==="
}

main "$@"
