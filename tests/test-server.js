/**
 * Test Server Manager
 * 
 * Manages starting and stopping the Hugo server for tests.
 * Auto-starts Hugo server if not already running (can be disabled).
 * 
 * Environment variables:
 * - TEST_URL: If set, skips server management and uses this URL
 * - NO_AUTO_SERVER: If set to 'true', skips auto-starting Hugo (default: false)
 * - START_SERVER: Legacy flag, if set to 'false', skips server startup
 * - SERVER_PORT: Port for local server (default: 1313)
 * - SERVER_HOST: Host for local server (default: 127.0.0.1)
 */

const { spawn } = require('child_process');
const { promisify } = require('util');
const http = require('http');
const https = require('https');
const { URL } = require('url');

const sleep = promisify(setTimeout);

class TestServer {
  constructor() {
    this.process = null;
    this.port = process.env.SERVER_PORT || 1313;
    this.host = process.env.SERVER_HOST || '127.0.0.1';
    this.shouldManageServer = !process.env.TEST_URL && process.env.START_SERVER !== 'false' && process.env.NO_AUTO_SERVER !== 'true';
    this.baseUrl = process.env.TEST_URL || `http://${this.host}:${this.port}`;
  }

  /**
   * Check if a port is available
   */
  async isPortAvailable(port) {
    const net = require('net');
    return new Promise((resolve) => {
      const server = net.createServer();
      server.once('error', () => resolve(false));
      server.once('listening', () => {
        server.close();
        resolve(true);
      });
      server.listen(port, this.host);
    });
  }

  /**
   * Check if server is responding
   */
  async isServerReady() {
    return new Promise((resolve) => {
      const url = new URL(this.baseUrl);
      const client = url.protocol === 'https:' ? https : http;
      
      const req = client.get(this.baseUrl, (res) => {
        resolve(res.statusCode === 200);
      });
      
      req.on('error', () => {
        resolve(false);
      });
      
      req.setTimeout(5000, () => {
        req.destroy();
        resolve(false);
      });
    });
  }

  /**
   * Wait for server to be ready
   */
  async waitForServer(maxAttempts = 30, delayMs = 1000) {
    console.log(`Waiting for server at ${this.baseUrl}...`);
    
    for (let i = 0; i < maxAttempts; i++) {
      if (await this.isServerReady()) {
        console.log(`✓ Server is ready at ${this.baseUrl}`);
        return true;
      }
      await sleep(delayMs);
    }
    
    return false;
  }

  /**
   * Check if Hugo is available
   */
  async isHugoAvailable() {
    const { spawn } = require('child_process');
    return new Promise((resolve) => {
      const process = spawn('which', ['hugo']);
      process.on('close', (code) => {
        resolve(code === 0);
      });
      process.on('error', () => {
        resolve(false);
      });
    });
  }

  /**
   * Find available port if default is taken
   */
  async findAvailablePort(startPort) {
    const net = require('net');
    
    for (let port = startPort; port < startPort + 100; port++) {
      const available = await new Promise((resolve) => {
        const server = net.createServer();
        server.once('error', () => resolve(false));
        server.once('listening', () => {
          server.close();
          resolve(true);
        });
        server.listen(port, this.host);
      });
      
      if (available) {
        return port;
      }
    }
    
    throw new Error('No available ports found');
  }

  /**
   * Start Hugo server
   */
  async start() {
    if (!this.shouldManageServer) {
      console.log(`Using external server at ${this.baseUrl}`);
      
      // Verify external server is accessible
      if (!(await this.waitForServer(5, 2000))) {
        throw new Error(`External server at ${this.baseUrl} is not accessible`);
      }
      
      return;
    }

    // Check if Hugo is available
    if (!(await this.isHugoAvailable())) {
      throw new Error('Hugo binary not found. Please install Hugo or set TEST_URL environment variable.');
    }

    console.log(`Starting Hugo server on ${this.host}:${this.port}...`);

    // Check if server is already running
    if (await this.isServerReady()) {
      console.log('Server is already running');
      return;
    }

    // Find available port if default is taken
    const originalPort = this.port;
    if (!(await this.isPortAvailable(this.port))) {
      console.log(`Port ${this.port} is in use, finding available port...`);
      this.port = await this.findAvailablePort(this.port + 1);
      this.baseUrl = `http://${this.host}:${this.port}`;
      console.log(`Using port ${this.port} instead of ${originalPort}`);
    }

    // Start Hugo server
    this.process = spawn('hugo', [
      'server',
      '--bind', this.host,
      '--port', this.port.toString(),
      '--disableLiveReload',
      '--noHTTPCache'
    ], {
      cwd: 'hugo/site',
      stdio: ['ignore', 'pipe', 'pipe']
    });

    // Log output for debugging
    this.process.stdout.on('data', (data) => {
      const output = data.toString();
      if (output.includes('Web Server is available at')) {
        console.log('Hugo server started');
      }
    });

    this.process.stderr.on('data', (data) => {
      console.error('Hugo server error:', data.toString());
    });

    this.process.on('error', (error) => {
      console.error('Failed to start Hugo server:', error);
      throw error;
    });

    this.process.on('exit', (code) => {
      if (code !== 0 && code !== null) {
        console.error(`Hugo server exited with code ${code}`);
      }
    });

    // Wait for server to be ready
    if (!(await this.waitForServer())) {
      await this.stop();
      throw new Error('Server failed to start within timeout period');
    }
  }

  /**
   * Stop Hugo server
   */
  async stop() {
    if (!this.shouldManageServer) {
      console.log('Not managing server, skipping stop');
      return;
    }

    if (!this.process) {
      return;
    }

    console.log('Stopping Hugo server...');
    
    return new Promise((resolve) => {
      this.process.on('exit', () => {
        this.process = null;
        console.log('✓ Server stopped');
        resolve();
      });

      // Try graceful shutdown first
      this.process.kill('SIGTERM');

      // Force kill after 5 seconds
      setTimeout(() => {
        if (this.process) {
          this.process.kill('SIGKILL');
          this.process = null;
          resolve();
        }
      }, 5000);
    });
  }

  /**
   * Get the base URL for tests
   */
  getBaseUrl() {
    return this.baseUrl;
  }
}

// Singleton instance
let serverInstance = null;

/**
 * Get or create server instance
 */
function getServer() {
  if (!serverInstance) {
    serverInstance = new TestServer();
  }
  return serverInstance;
}

/**
 * Jest setup/teardown helpers
 */
async function setupTestServer() {
  const server = getServer();
  await server.start();
  return server.getBaseUrl();
}

async function teardownTestServer() {
  const server = getServer();
  await server.stop();
  serverInstance = null;
}

module.exports = {
  TestServer,
  getServer,
  setupTestServer,
  teardownTestServer
};
