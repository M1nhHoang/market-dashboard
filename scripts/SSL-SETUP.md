# SSL Certificate Setup Guide

## Cloudflare Origin Certificate (Recommended)

### Step 1: Create Origin Certificate

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Select your domain: `minhhoang.info`
3. Navigate to: **SSL/TLS** → **Origin Server**
4. Click **Create Certificate**
5. Settings:
   - Generate private key and CSR with Cloudflare: **Yes**
   - Hostnames: `trade.minhhoang.info`
   - Certificate Validity: **15 years** (default)
6. Click **Create**

### Step 2: Save Certificate Files

Copy the certificate content and save to these files on your server:

```bash
# Create directory
sudo mkdir -p /etc/ssl/cloudflare

# Save certificate (copy from Cloudflare "Origin Certificate")
sudo nano /etc/ssl/cloudflare/trade.minhhoang.info.pem

# Save private key (copy from Cloudflare "Private Key")
sudo nano /etc/ssl/cloudflare/trade.minhhoang.info.key

# Set permissions
sudo chmod 644 /etc/ssl/cloudflare/trade.minhhoang.info.pem
sudo chmod 600 /etc/ssl/cloudflare/trade.minhhoang.info.key
```

### Step 3: Configure Cloudflare SSL Mode

1. Go to **SSL/TLS** → **Overview**
2. Set SSL/TLS encryption mode to: **Full (strict)**

This ensures traffic between Cloudflare and your origin server is encrypted.

### Step 4: Add DNS Record

1. Go to **DNS** → **Records**
2. Add record:
   - Type: `A`
   - Name: `trade`
   - IPv4 address: `<your-server-ip>`
   - Proxy status: **Proxied** (orange cloud) - recommended for DDoS protection
   - TTL: Auto

---

## Alternative: Let's Encrypt (Free, Auto-renewing)

If you don't use Cloudflare proxy, you can use Let's Encrypt:

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d trade.minhhoang.info

# Auto-renewal is set up automatically
# Test with: sudo certbot renew --dry-run
```

---

## Verifying SSL Setup

```bash
# Check certificate dates
openssl x509 -in /etc/ssl/cloudflare/trade.minhhoang.info.pem -noout -dates

# Test HTTPS connection
curl -I https://trade.minhhoang.info

# Check nginx config
sudo nginx -t
```
