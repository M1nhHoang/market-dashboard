# ============================================
# Frontend Dockerfile - React + Vite (multi-stage)
# ============================================

# --- Stage 1: Build ---
FROM node:20-alpine AS build

WORKDIR /app

# Copy package files first for layer caching
COPY package.json ./
RUN npm install

# Copy source files
COPY index.html vite.config.js postcss.config.js tailwind.config.js ./
COPY src/ src/

# Build for production
# VITE_API_URL is baked at build time; 
# empty means relative paths (proxied by nginx)
ARG VITE_API_URL=""
ENV VITE_API_URL=${VITE_API_URL}

RUN npm run build

# --- Stage 2: Serve with Nginx ---
FROM nginx:1.27-alpine AS production

# Copy custom nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built assets from build stage
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
