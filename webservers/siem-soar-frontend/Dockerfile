FROM node:18-alpine AS builder

WORKDIR /app

# Copy all three frontend apps
COPY frontend/siem_dashboard ./siem_dashboard
COPY frontend/corp_portal ./corp_portal
COPY frontend/scada_dashboard ./scada_dashboard

# Build SIEM dashboard
WORKDIR /app/siem_dashboard
RUN npm install && npm run build

# Build output
FROM nginx:alpine

# Create frontend directory for React apps
RUN mkdir -p /app/frontend && chmod 755 /app/frontend

# Copy nginx config
COPY webservers/siem-soar-frontend/nginx.conf /etc/nginx/nginx.conf

# Copy built SIEM app
COPY --from=builder /app/siem_dashboard/dist /usr/share/nginx/html

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:80/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
