#!/usr/bin/env bun
/**
 * Unified server management tool for madeinoz-knowledge-system
 * Consolidates start, stop, restart, status, and logs commands
 * @module src/skills/tools/server.ts
 */
import { join } from 'node:path';
import { createComposeManager, type DatabaseBackend } from '../server/lib/container.js';
import { loadConfig } from '../server/lib/config.js';
import { cli } from '../server/lib/cli.js';

const serverDir = join(import.meta.dir, '../server');

// Parse command and flags
const args = process.argv.slice(2);
const command = args[0]?.toLowerCase() || 'help';

// Extract flags
const flags = {
  dev: args.includes('--dev') || args.includes('-d'),
  mcp: args.includes('--mcp'),
  db: args.includes('--db'),
  noFollow: args.includes('--no-follow'),
  tail: (() => {
    const tailIdx = args.indexOf('--tail');
    if (tailIdx !== -1 && args[tailIdx + 1]) {
      return parseInt(args[tailIdx + 1], 10);
    }
    return 100;
  })(),
};

/**
 * Start the server containers
 */
async function start(): Promise<void> {
  cli.header('Starting Knowledge System');

  const compose = createComposeManager(serverDir);

  // Check if runtime is available
  if (!compose.isRuntimeAvailable()) {
    cli.error('No container runtime found!');
    process.exit(1);
  }

  cli.success(`Using container runtime: ${compose.getRuntimeCommand()}`);
  cli.blank();

  if (flags.dev) {
    cli.info('*** DEVELOPMENT MODE ***');
    cli.blank();
  }

  // Load configuration to determine database type
  const config = await loadConfig();
  const databaseType = (config.DATABASE_TYPE || 'neo4j') as DatabaseBackend;

  cli.info(`Database backend: ${databaseType}`);
  cli.blank();

  // Get compose file path for display
  const composeFile = compose.getComposeFilePath(databaseType, flags.dev);
  cli.dim(`Compose file: ${composeFile}`);
  cli.blank();

  // Start containers
  cli.info('Starting containers...');
  const result = await compose.up(databaseType, flags.dev);

  if (result.success) {
    cli.success('Server started successfully');
    cli.blank();

    // Show access URLs
    cli.info('Access Points:');
    if (databaseType === 'neo4j') {
      const browserPort = flags.dev ? 7475 : 7474;
      cli.url('Neo4j Browser', `http://localhost:${browserPort}`);
      cli.url('Bolt', `bolt://localhost:${flags.dev ? 7688 : 7687}`);
    } else {
      cli.url('FalkorDB Browser', 'http://localhost:3000');
      cli.url('Redis', 'localhost:6379');
    }
    const mcpPort = flags.dev ? 8001 : 8000;
    cli.url('MCP Server', `http://localhost:${mcpPort}/mcp/`);
  } else {
    cli.error(`Failed to start: ${result.stderr || 'Unknown error'}`);
    process.exit(1);
  }
}

/**
 * Stop the server containers
 */
async function stop(): Promise<void> {
  cli.header('Stopping Knowledge System');

  const compose = createComposeManager(serverDir);

  // Check if runtime is available
  if (!compose.isRuntimeAvailable()) {
    cli.error('No container runtime found!');
    process.exit(1);
  }

  cli.success(`Using container runtime: ${compose.getRuntimeCommand()}`);
  cli.blank();

  if (flags.dev) {
    cli.info('*** DEVELOPMENT MODE ***');
    cli.blank();
  }

  // Load configuration to determine database type
  const config = await loadConfig();
  const databaseType = (config.DATABASE_TYPE || 'neo4j') as DatabaseBackend;

  cli.info(`Database backend: ${databaseType}`);
  cli.blank();

  // Stop containers
  cli.info('Stopping containers...');
  const result = await compose.down(databaseType, flags.dev);

  if (result.success) {
    cli.success('Server stopped successfully');
  } else {
    cli.error(`Failed to stop: ${result.stderr || 'Unknown error'}`);
    process.exit(1);
  }
}

/**
 * Restart the server containers
 */
async function restart(): Promise<void> {
  cli.header('Restarting Knowledge System');

  const compose = createComposeManager(serverDir);

  // Check if runtime is available
  if (!compose.isRuntimeAvailable()) {
    cli.error('No container runtime found!');
    process.exit(1);
  }

  cli.success(`Using container runtime: ${compose.getRuntimeCommand()}`);
  cli.blank();

  if (flags.dev) {
    cli.info('*** DEVELOPMENT MODE ***');
    cli.blank();
  }

  // Load configuration to determine database type
  const config = await loadConfig();
  const databaseType = (config.DATABASE_TYPE || 'neo4j') as DatabaseBackend;

  cli.info(`Database backend: ${databaseType}`);
  cli.blank();

  // Restart containers
  cli.info('Restarting containers...');
  const result = await compose.restart(databaseType, undefined, flags.dev);

  if (result.success) {
    cli.success('Server restarted successfully');
    cli.blank();

    // Show access URLs
    cli.info('Access Points:');
    if (databaseType === 'neo4j') {
      const browserPort = flags.dev ? 7475 : 7474;
      cli.url('Neo4j Browser', `http://localhost:${browserPort}`);
      cli.url('Bolt', `bolt://localhost:${flags.dev ? 7688 : 7687}`);
    } else {
      cli.url('FalkorDB Browser', 'http://localhost:3000');
      cli.url('Redis', 'localhost:6379');
    }
    const mcpPort = flags.dev ? 8001 : 8000;
    cli.url('MCP Server', `http://localhost:${mcpPort}/mcp/`);
  } else {
    cli.error(`Failed to restart: ${result.stderr || 'Unknown error'}`);
    process.exit(1);
  }
}

/**
 * Show server status
 */
async function status(): Promise<void> {
  cli.header('Knowledge System Status');

  const compose = createComposeManager(serverDir);

  // Check if runtime is available
  if (!compose.isRuntimeAvailable()) {
    cli.error('No container runtime found!');
    process.exit(1);
  }

  cli.success(`Using container runtime: ${compose.getRuntimeCommand()}`);
  cli.blank();

  if (flags.dev) {
    cli.info('*** DEVELOPMENT MODE ***');
    cli.blank();
  }

  // Load configuration to determine database type
  const config = await loadConfig();
  const databaseType = (config.DATABASE_TYPE || 'neo4j') as DatabaseBackend;

  cli.info(`Database backend: ${databaseType}`);
  cli.blank();

  // Get compose file path for display
  const composeFile = compose.getComposeFilePath(databaseType, flags.dev);
  cli.dim(`Compose file: ${composeFile}`);
  cli.blank();

  // Get container status using docker-compose ps
  cli.info('Container Status:');
  cli.blank();

  const result = await compose.ps(databaseType, flags.dev);

  if (result.success && result.stdout) {
    console.log(result.stdout);
  } else if (result.stderr) {
    cli.warning('Could not get container status');
    cli.dim(result.stderr);
  }

  cli.blank();

  // Determine ports based on database type and mode
  const mcpPort = flags.dev ? 8001 : 8000;
  const dbPort = databaseType === 'neo4j' ? (flags.dev ? 7475 : 7474) : 3000;
  const dbName = databaseType === 'neo4j' ? 'Neo4j Browser' : 'FalkorDB UI';

  // Test health endpoint
  cli.info('Health Check:');
  cli.blank();

  try {
    const healthUrl = `http://localhost:${mcpPort}/health`;
    const response = await fetch(healthUrl, {
      signal: AbortSignal.timeout(5000),
    });

    if (response.ok) {
      const data = await response.json();
      if (data.status === 'healthy' || data.status === 'ok') {
        cli.success('  MCP Server: healthy');
      } else {
        cli.warning(`  MCP Server: ${data.status}`);
      }
    } else {
      cli.warning('  MCP Server: unhealthy (server may be starting up)');
    }
  } catch {
    cli.warning('  MCP Server: not responding (server may be starting up)');
  }

  cli.blank();
  cli.separator();
  cli.blank();

  // Display access URLs
  cli.info('Access Points:');
  cli.url(`  ${dbName}`, `http://localhost:${dbPort}`);
  cli.url('  MCP Server', `http://localhost:${mcpPort}/mcp/`);
  cli.url('  Health Check', `http://localhost:${mcpPort}/health`);
  cli.blank();

  // Check if services are running
  const isRunning = await compose.isRunning(databaseType, flags.dev);

  if (isRunning) {
    cli.success('System operational');
    process.exit(0);
  } else {
    cli.warning('System not fully running');
    cli.blank();
    cli.info('To start the system:');
    cli.dim('  bun run server start');
    process.exit(1);
  }
}

/**
 * Show container logs
 */
async function logs(): Promise<void> {
  const compose = createComposeManager(serverDir);

  // Check if runtime is available
  if (!compose.isRuntimeAvailable()) {
    cli.error('No container runtime found!');
    process.exit(1);
  }

  // Load configuration to determine database type
  const config = await loadConfig();
  const databaseType = (config.DATABASE_TYPE || 'neo4j') as DatabaseBackend;

  // Determine which service to show logs for
  let service: string | undefined;
  if (flags.mcp) {
    service = 'graphiti-mcp-server';
  } else if (flags.db) {
    service = databaseType === 'neo4j' ? 'neo4j' : 'falkordb';
  }

  const header = service ? `Logs: ${service}` : 'Logs: all services';
  cli.header(header);
  cli.info(`Backend: ${databaseType}`);
  cli.info(`Runtime: ${compose.getRuntimeCommand()}`);
  cli.separator();

  // Get logs (this will stream if follow is enabled)
  const result = await compose.logs(
    databaseType,
    service,
    !flags.noFollow, // follow
    flags.dev,
    flags.tail
  );

  if (!result.success) {
    cli.error(`Failed to get logs: ${result.stderr || 'Unknown error'}`);
    process.exit(1);
  }

  // Output logs
  if (result.stdout) {
    console.log(result.stdout);
  }
}

/**
 * Show help
 */
function showHelp(): void {
  console.log(`
Usage: bun run server.ts <command> [options]

Commands:
  start     Start the server containers
  stop      Stop the server containers
  restart   Restart the server containers
  status    Show server status and health
  logs      Show container logs

Options:
  --dev, -d     Use development configuration
  --mcp         (logs) Show only MCP server logs
  --db          (logs) Show only database logs
  --tail N      (logs) Number of lines to show (default: 100)
  --no-follow   (logs) Don't follow log output

Examples:
  bun run server.ts start
  bun run server.ts stop
  bun run server.ts restart
  bun run server.ts status
  bun run server.ts logs --mcp --tail 50
  bun run server.ts logs --db --no-follow
`);
}

// Main execution
async function main(): Promise<void> {
  try {
    switch (command) {
      case 'start':
        await start();
        break;
      case 'stop':
        await stop();
        break;
      case 'restart':
        await restart();
        break;
      case 'status':
        await status();
        break;
      case 'logs':
        await logs();
        break;
      case 'help':
      case '--help':
      case '-h':
        showHelp();
        break;
      default:
        cli.error(`Unknown command: ${command}`);
        showHelp();
        process.exit(1);
    }
  } catch (error) {
    cli.error(`Error: ${error instanceof Error ? error.message : String(error)}`);
    process.exit(1);
  }
}

main();
