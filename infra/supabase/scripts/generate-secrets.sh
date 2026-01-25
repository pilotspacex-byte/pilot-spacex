#!/usr/bin/env bash
# =============================================================================
# Pilot Space - Generate Secure Secrets for Self-Hosted Supabase
# =============================================================================
# This script generates all required secrets for a production deployment.
#
# Usage:
#   ./scripts/generate-secrets.sh              # Print secrets to stdout
#   ./scripts/generate-secrets.sh --update     # Update .env file
#   ./scripts/generate-secrets.sh --env-file   # Create new .env from template
#
# Requirements:
#   - openssl
#   - Node.js (optional, for JWT generation)
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check dependencies
check_dependencies() {
    if ! command -v openssl &> /dev/null; then
        log_error "openssl is required but not installed"
        exit 1
    fi
}

# Generate random hex string
generate_hex() {
    local length=${1:-32}
    openssl rand -hex "$length"
}

# Generate random base64 string
generate_base64() {
    local length=${1:-32}
    openssl rand -base64 "$length" | tr -d '\n'
}

# Generate JWT token (anon or service_role)
generate_jwt() {
    local role=$1
    local secret=$2

    # Calculate timestamps
    local iat=$(date +%s)
    local exp=$((iat + 315360000)) # 10 years

    # Create header and payload
    local header='{"alg":"HS256","typ":"JWT"}'
    local payload="{\"role\":\"${role}\",\"iss\":\"supabase\",\"iat\":${iat},\"exp\":${exp}}"

    # Base64 URL encode (without padding)
    local header_b64=$(echo -n "$header" | openssl base64 -A | tr '+/' '-_' | tr -d '=')
    local payload_b64=$(echo -n "$payload" | openssl base64 -A | tr '+/' '-_' | tr -d '=')

    # Create signature
    local signature=$(echo -n "${header_b64}.${payload_b64}" | openssl dgst -sha256 -hmac "$secret" -binary | openssl base64 -A | tr '+/' '-_' | tr -d '=')

    echo "${header_b64}.${payload_b64}.${signature}"
}

# Generate all secrets
generate_all_secrets() {
    log_info "Generating secure secrets for Pilot Space Supabase..."
    echo ""

    # JWT Secret (main secret for all JWT operations)
    JWT_SECRET=$(generate_hex 32)

    # Generate API keys
    ANON_KEY=$(generate_jwt "anon" "$JWT_SECRET")
    SERVICE_ROLE_KEY=$(generate_jwt "service_role" "$JWT_SECRET")

    # Database password
    POSTGRES_PASSWORD=$(generate_hex 24)

    # Realtime secret (Phoenix/Elixir)
    REALTIME_SECRET_KEY_BASE=$(generate_base64 48)

    # Supavisor secret
    SUPAVISOR_SECRET_KEY_BASE=$(generate_base64 48)

    # Vault encryption key
    VAULT_ENC_KEY=$(generate_hex 16)

    # Redis password
    REDIS_PASSWORD=$(generate_hex 16)

    # Meilisearch API key
    MEILISEARCH_API_KEY=$(generate_hex 32)

    # Logflare API key (optional)
    LOGFLARE_API_KEY=$(generate_hex 32)

    echo "# ==================================================================="
    echo "# Generated Secrets for Pilot Space Supabase"
    echo "# Generated at: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
    echo "# ==================================================================="
    echo ""
    echo "# JWT Configuration (CRITICAL - do not lose)"
    echo "JWT_SECRET=${JWT_SECRET}"
    echo ""
    echo "# API Keys"
    echo "ANON_KEY=${ANON_KEY}"
    echo "SERVICE_ROLE_KEY=${SERVICE_ROLE_KEY}"
    echo ""
    echo "# Database"
    echo "POSTGRES_PASSWORD=${POSTGRES_PASSWORD}"
    echo ""
    echo "# Realtime (Phoenix)"
    echo "REALTIME_SECRET_KEY_BASE=${REALTIME_SECRET_KEY_BASE}"
    echo ""
    echo "# Supavisor (Connection Pooler)"
    echo "SUPAVISOR_SECRET_KEY_BASE=${SUPAVISOR_SECRET_KEY_BASE}"
    echo ""
    echo "# Vault"
    echo "VAULT_ENC_KEY=${VAULT_ENC_KEY}"
    echo ""
    echo "# Redis"
    echo "REDIS_PASSWORD=${REDIS_PASSWORD}"
    echo ""
    echo "# Meilisearch"
    echo "MEILISEARCH_API_KEY=${MEILISEARCH_API_KEY}"
    echo ""
    echo "# Analytics (optional)"
    echo "LOGFLARE_API_KEY=${LOGFLARE_API_KEY}"
    echo ""

    log_success "Secrets generated successfully!"
    log_warn "IMPORTANT: Save these secrets securely. The JWT_SECRET is especially critical."
}

# Update existing .env file
update_env_file() {
    local env_file="${PROJECT_DIR}/.env"

    if [[ ! -f "$env_file" ]]; then
        log_error ".env file not found. Run './scripts/generate-secrets.sh --env-file' first."
        exit 1
    fi

    log_info "Updating secrets in ${env_file}..."

    # Generate secrets
    JWT_SECRET=$(generate_hex 32)
    ANON_KEY=$(generate_jwt "anon" "$JWT_SECRET")
    SERVICE_ROLE_KEY=$(generate_jwt "service_role" "$JWT_SECRET")
    POSTGRES_PASSWORD=$(generate_hex 24)
    REALTIME_SECRET_KEY_BASE=$(generate_base64 48)
    SUPAVISOR_SECRET_KEY_BASE=$(generate_base64 48)
    VAULT_ENC_KEY=$(generate_hex 16)
    REDIS_PASSWORD=$(generate_hex 16)
    MEILISEARCH_API_KEY=$(generate_hex 32)

    # Update values in .env (macOS compatible sed)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|^JWT_SECRET=.*|JWT_SECRET=${JWT_SECRET}|" "$env_file"
        sed -i '' "s|^ANON_KEY=.*|ANON_KEY=${ANON_KEY}|" "$env_file"
        sed -i '' "s|^SERVICE_ROLE_KEY=.*|SERVICE_ROLE_KEY=${SERVICE_ROLE_KEY}|" "$env_file"
        sed -i '' "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${POSTGRES_PASSWORD}|" "$env_file"
        sed -i '' "s|^REALTIME_SECRET_KEY_BASE=.*|REALTIME_SECRET_KEY_BASE=${REALTIME_SECRET_KEY_BASE}|" "$env_file"
        sed -i '' "s|^SUPAVISOR_SECRET_KEY_BASE=.*|SUPAVISOR_SECRET_KEY_BASE=${SUPAVISOR_SECRET_KEY_BASE}|" "$env_file"
        sed -i '' "s|^VAULT_ENC_KEY=.*|VAULT_ENC_KEY=${VAULT_ENC_KEY}|" "$env_file"
        sed -i '' "s|^REDIS_PASSWORD=.*|REDIS_PASSWORD=${REDIS_PASSWORD}|" "$env_file"
        sed -i '' "s|^MEILISEARCH_API_KEY=.*|MEILISEARCH_API_KEY=${MEILISEARCH_API_KEY}|" "$env_file"
    else
        sed -i "s|^JWT_SECRET=.*|JWT_SECRET=${JWT_SECRET}|" "$env_file"
        sed -i "s|^ANON_KEY=.*|ANON_KEY=${ANON_KEY}|" "$env_file"
        sed -i "s|^SERVICE_ROLE_KEY=.*|SERVICE_ROLE_KEY=${SERVICE_ROLE_KEY}|" "$env_file"
        sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${POSTGRES_PASSWORD}|" "$env_file"
        sed -i "s|^REALTIME_SECRET_KEY_BASE=.*|REALTIME_SECRET_KEY_BASE=${REALTIME_SECRET_KEY_BASE}|" "$env_file"
        sed -i "s|^SUPAVISOR_SECRET_KEY_BASE=.*|SUPAVISOR_SECRET_KEY_BASE=${SUPAVISOR_SECRET_KEY_BASE}|" "$env_file"
        sed -i "s|^VAULT_ENC_KEY=.*|VAULT_ENC_KEY=${VAULT_ENC_KEY}|" "$env_file"
        sed -i "s|^REDIS_PASSWORD=.*|REDIS_PASSWORD=${REDIS_PASSWORD}|" "$env_file"
        sed -i "s|^MEILISEARCH_API_KEY=.*|MEILISEARCH_API_KEY=${MEILISEARCH_API_KEY}|" "$env_file"
    fi

    log_success ".env file updated with new secrets"
    log_warn "Make sure to restart services: docker compose down && docker compose up -d"
}

# Create .env from template
create_env_file() {
    local template="${PROJECT_DIR}/.env.example"
    local env_file="${PROJECT_DIR}/.env"

    if [[ ! -f "$template" ]]; then
        log_error ".env.example not found"
        exit 1
    fi

    if [[ -f "$env_file" ]]; then
        log_warn ".env already exists. Backing up to .env.backup"
        cp "$env_file" "${env_file}.backup"
    fi

    log_info "Creating .env from template..."
    cp "$template" "$env_file"

    # Update with generated secrets
    update_env_file

    log_success ".env file created at ${env_file}"
}

# Main
main() {
    check_dependencies

    case "${1:-}" in
        --update)
            update_env_file
            ;;
        --env-file)
            create_env_file
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  (no args)     Print generated secrets to stdout"
            echo "  --update      Update existing .env file with new secrets"
            echo "  --env-file    Create new .env file from template"
            echo "  --help, -h    Show this help message"
            ;;
        *)
            generate_all_secrets
            ;;
    esac
}

main "$@"
