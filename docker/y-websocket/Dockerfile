FROM node:20-alpine

# Install native build tools required by LevelDB
RUN apk add --no-cache python3 make g++

WORKDIR /app

# Install y-websocket + y-leveldb
RUN npm install --omit=dev \
    y-websocket@1.5.4 \
    y-leveldb@0.1.2 \
    ws@8.16.0

COPY server.js ./

# Persistence volume mount point
VOLUME ["/data"]

EXPOSE 1234

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:${PORT:-1234}/health || exit 1

ENV NODE_ENV=production
ENV PORT=1234
ENV HOST=0.0.0.0
ENV YPERSISTENCE=/data

CMD ["node", "server.js"]
