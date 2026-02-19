/**
 * y-websocket server with LevelDB persistence.
 * CRDT transport layer for Feature 016 note collaboration.
 *
 * Configuration via environment variables:
 *   PORT     - WebSocket server port (default: 1234)
 *   HOST     - Bind address (default: 0.0.0.0)
 *   YPERSISTENCE - LevelDB data directory (default: /data)
 */

const http = require('http');
const { WebSocketServer } = require('ws');
const { setupWSConnection } = require('y-websocket/bin/utils');
const LeveldbPersistence = require('y-leveldb').LeveldbPersistence;

const PORT = parseInt(process.env.PORT ?? '1234', 10);
const HOST = process.env.HOST ?? '0.0.0.0';
const PERSISTENCE_DIR = process.env.YPERSISTENCE ?? '/data';

// LevelDB persistence for CRDT documents
const persistence = new LeveldbPersistence(PERSISTENCE_DIR);

const server = http.createServer((req, res) => {
  if (req.method === 'GET' && req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ status: 'ok', timestamp: new Date().toISOString() }));
    return;
  }
  res.writeHead(404);
  res.end();
});

const wss = new WebSocketServer({ server });

wss.on('connection', (conn, req) => {
  setupWSConnection(conn, req, { persistence });
});

server.listen(PORT, HOST, () => {
  console.log(`y-websocket server running on ${HOST}:${PORT}`);
  console.log(`LevelDB persistence at ${PERSISTENCE_DIR}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, closing server...');
  wss.close(() => {
    server.close(() => {
      console.log('Server closed.');
      process.exit(0);
    });
  });
});

process.on('SIGINT', () => {
  process.emit('SIGTERM');
});
