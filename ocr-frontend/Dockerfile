# Stage 1: Build Angular application
FROM node:20-alpine AS build

WORKDIR /app

# Install npm dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy application source code and build production bundle
COPY . .
RUN npm run build

# Stage 2: Serve static bundle via Nginx
FROM nginx:alpine

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built web assets from build stage to Nginx web root
COPY --from=build /app/dist/ocr-frontend/browser /usr/share/nginx/html

# Expose web server port
EXPOSE 80

# Start Nginx in foreground
CMD ["nginx", "-g", "daemon off;"]
