# Build context is the repository root (see docker-compose.yml) so the shared
# workspace packages (@rdc/domain, @rdc/client, @rdc/ui) are available.
FROM node:20-slim AS builder
WORKDIR /repo

# Workspace manifests first for dependency-install caching.
COPY package.json ./
COPY apps/web/package.json apps/web/package.json
COPY packages/domain/package.json packages/domain/package.json
COPY packages/client/package.json packages/client/package.json
COPY packages/ui/package.json packages/ui/package.json
COPY packages/config/package.json packages/config/package.json
RUN npm install

# Source.
COPY packages packages
COPY apps/web apps/web
RUN npm run build --workspace apps/web

FROM node:20-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /repo/apps/web/.next/standalone ./
COPY --from=builder /repo/apps/web/.next/static ./apps/web/.next/static
COPY --from=builder /repo/apps/web/public ./apps/web/public
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
