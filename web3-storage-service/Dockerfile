# Use Node.js 22 Alpine image (latest LTS)
FROM node:22-alpine

# Install dnsutils for better DNS resolution
RUN apk add --no-cache bind-tools

# Set working directory
WORKDIR /app

# Copy package files first for better caching
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY . .

# Create upload_queue directory if it doesn't exist
RUN mkdir -p upload_queue

# Create non-root user
RUN addgroup -g 1001 -S nodejs && \
    adduser -S fusevault -u 1001 -G nodejs && \
    chown -R fusevault:nodejs /app
USER fusevault

# Expose port
EXPOSE 8080

# Health check with increased timeout
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:8080/health || exit 1

# Run the application
CMD ["npm", "start"]