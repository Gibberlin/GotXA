FROM node:18-alpine AS builder

WORKDIR /app

# Copy SCADA dashboard
COPY frontend/scada_dashboard ./

# Build
RUN npm install && npm run build

# Production image
FROM nginx:alpine

# Create frontend directory for React apps
RUN mkdir -p /app/frontend && chmod 755 /app/frontend

# Copy nginx config
COPY webservers/scada-frontend/nginx.conf /etc/nginx/nginx.conf

# Copy built app
COPY --from=builder /app/dist /usr/share/nginx/html

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:80/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
