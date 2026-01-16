/**
 * Test Server Manager
 * 
 * Manages starting and stopping the Hugo server for tests.
 * Can be disabled via TEST_URL environment variable for testing against remote servers.
 * 
 * Environment variables:
 * - TEST_URL: If set, skips server management and uses this URL
 * - START_SERVER: If set to 'false', skips server startup (default: true)
 * - SERVER_PORT: Port for local server (default: 8668)
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
    this.port = process.env.SERVER_PORT || 8668;
    this.host = process.env.SERVER_HOST || '127.0.0.1';
    this.shouldManageServer = !process.env.TEST_URL && process.env.START_SERVER !== 'false';
    this.baseUrl = process.env.TEST_URL || `http://${this.host}:${this.port}`;
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

    console.log(`Starting Hugo server on ${this.host}:${this.port}...`);

    // Check if server is already running
    if (await this.isServerReady()) {
      console.log('Server is already running');
      return;
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
