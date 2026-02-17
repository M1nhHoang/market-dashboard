#!/bin/bash
# ============================================
# Market Intelligence Dashboard - Server Setup Script
# ============================================
# Usage: 
#   chmod +x server-setup.sh
#   ./server-setup.sh
#
# Prerequisites:
#   - Ubuntu 20.04+ / Debian 11+
#   - Root access
#   - SSL cert files ready (see below)
# ============================================

set -e

# --- Configuration ---
DOMAIN="trade.minhhoang.info"
APP_DIR="/root/minhhoang/market-dashboard"
SSL_DIR="/etc/ssl/cloudflare"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# --- Check root ---
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root"
    exit 1
fi

# --- Step 1: Install Docker ---
install_docker() {
    log_info "Installing Docker..."
    
    if command -v docker &> /dev/null; then
        log_info "Docker already installed: $(docker --version)"
        return 0
    fi
    
    apt-get update
    apt-get install -y ca-certificates curl gnupg
    
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    systemctl enable docker
    systemctl start docker
    
    log_info "Docker installed successfully"
}

# --- Step 2: Install Nginx ---
install_nginx() {
    log_info "Installing Nginx..."
    
    if command -v nginx &> /dev/null; then
        log_info "Nginx already installed: $(nginx -v 2>&1)"
        return 0
    fi
    
    apt-get install -y nginx
    systemctl enable nginx
    systemctl start nginx
    
    log_info "Nginx installed successfully"
}

# --- Step 3: Setup SSL Certificates ---
setup_ssl() {
    log_info "Setting up SSL certificates..."
    
    mkdir -p "$SSL_DIR"
    
    if [ -f "$SSL_DIR/$DOMAIN.pem" ] && [ -f "$SSL_DIR/$DOMAIN.key" ]; then
        log_info "SSL certificates already exist"
        return 0
    fi
    
    log_warn "SSL certificates not found!"
    echo ""
    echo "Please create Cloudflare Origin Certificate:"
    echo "  1. Go to Cloudflare Dashboard → SSL/TLS → Origin Server"
    echo "  2. Create Certificate for: $DOMAIN"
    echo "  3. Save certificate as: $SSL_DIR/$DOMAIN.pem"
    echo "  4. Save private key as:  $SSL_DIR/$DOMAIN.key"
    echo ""
    echo "Then run this script again."
    echo ""
    
    read -p "Do you have the cert files ready? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter path to certificate (.pem): " CERT_PATH
        read -p "Enter path to private key (.key): " KEY_PATH
        
        cp "$CERT_PATH" "$SSL_DIR/$DOMAIN.pem"
        cp "$KEY_PATH" "$SSL_DIR/$DOMAIN.key"
        chmod 644 "$SSL_DIR/$DOMAIN.pem"
        chmod 600 "$SSL_DIR/$DOMAIN.key"
        
        log_info "SSL certificates copied"
    else
        log_error "Cannot proceed without SSL certificates"
        exit 1
    fi
}

# --- Step 4: Configure Nginx ---
configure_nginx() {
    log_info "Configuring Nginx..."
    
    cat > /etc/nginx/sites-available/$DOMAIN << EOF
server {
    listen 80;
    server_name $DOMAIN;
    
    # Redirect HTTP to HTTPS
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl;
    server_name $DOMAIN;

    # SSL Configuration (Cloudflare Origin Certificate)
    ssl_certificate $SSL_DIR/$DOMAIN.pem;
    ssl_certificate_key $SSL_DIR/$DOMAIN.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # API routes -> Backend (port 8000)
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_http_version 1.1;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # All other routes -> Frontend (port 3000)
    location / {
        proxy_pass http://localhost:3000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

    # Enable the site
    rm -f /etc/nginx/sites-enabled/default
    ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
    
    # Test and reload
    nginx -t
    systemctl reload nginx
    
    log_info "Nginx configured successfully"
}

# --- Step 5: Clone/Update App ---
setup_app() {
    log_info "Setting up application..."
    
    if [ ! -d "$APP_DIR" ]; then
        log_warn "App directory not found at $APP_DIR"
        echo "Please clone the repository first:"
        echo "  git clone <your-repo-url> $APP_DIR"
        exit 1
    fi
    
    cd "$APP_DIR"
    
    # Check for .env file
    if [ ! -f "backend/.env" ]; then
        log_warn "backend/.env not found!"
        echo "Please create backend/.env with required environment variables"
        
        if [ -f "backend/.env.example" ]; then
            echo "Copying from .env.example..."
            cp backend/.env.example backend/.env
            echo "Please edit backend/.env with your actual values"
        fi
    fi
    
    log_info "Application directory ready"
}

# --- Step 6: Start Docker Services ---
start_services() {
    log_info "Starting Docker services..."
    
    cd "$APP_DIR"
    
    docker compose down 2>/dev/null || true
    docker compose up -d --build
    
    log_info "Waiting for services to start..."
    sleep 10
    
    # Check health
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        log_info "Backend is healthy"
    else
        log_warn "Backend health check failed (may still be starting)"
    fi
    
    docker compose ps
    
    log_info "Services started"
}

# --- Main ---
main() {
    echo "============================================"
    echo "Market Intelligence Dashboard - Server Setup"
    echo "============================================"
    echo ""
    
    install_docker
    install_nginx
    setup_ssl
    configure_nginx
    setup_app
    start_services
    
    echo ""
    echo "============================================"
    log_info "Setup complete!"
    echo ""
    echo "Your app should now be accessible at:"
    echo "  https://$DOMAIN"
    echo ""
    echo "Useful commands:"
    echo "  docker compose logs -f          # View logs"
    echo "  docker compose restart          # Restart services"
    echo "  docker compose down && docker compose up -d  # Full restart"
    echo "============================================"
}

main "$@"
