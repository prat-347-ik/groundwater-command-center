# --- Stage 1: Builder ---
FROM node:20-slim AS builder
WORKDIR /app

# 1. Copy ONLY package.json (Ignore local package-lock.json to avoid Windows/Linux conflicts)
COPY package.json ./

# 2. Install dependencies fresh. 
# We do NOT use 'npm ci' or copy the lockfile because it lacks Linux binaries.
RUN npm install

# 3. Copy the rest of the source code
COPY . .

# 4. Build the app
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# --- Stage 2: Runner ---
FROM node:20-slim AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Create a non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy necessary files from builder
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

# Switch to non-root user
USER nextjs

EXPOSE 3000
ENV PORT=3000

CMD ["node", "server.js"]