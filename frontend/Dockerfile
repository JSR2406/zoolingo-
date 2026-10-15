# syntax=docker/dockerfile:1
# ZooLingo frontend — production image
# Build: docker build -t zoolingo-frontend ./frontend

FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies (dev deps required for vite build)
COPY package.json package-lock.json* ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# Production serve stage
FROM nginx:alpine AS runtime

RUN apk add --no-cache curl

# Copy built static assets
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost/ || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
