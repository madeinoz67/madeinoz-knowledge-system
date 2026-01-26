/**
 * Container Runtime Abstraction Layer
 *
 * Provides a unified interface for Podman and Docker container operations.
 * Automatically detects available runtime and handles compatibility differences.
 *
 * SECURITY HARDENING:
 * - All container names validated against strict regex to prevent injection
 * - Command arguments properly escaped before execution
 * - Network names and volume names also validated
 */

import { join } from 'node:path';

// Using Bun.spawn and Bun.spawnSync for container operations

// Container runtime types
export type ContainerRuntime = 'podman' | 'docker' | 'none';

/**
 * Security: Strict pattern for container names, network names, volume names
 * Prevents command injection via malicious names
 *
 * Pattern explanation:
 * - ^[a-zA-Z0-9] - Start with alphanumeric
 * - [a-zA-Z0-9_-]{0,63} - Up to 64 chars total, allowing alphanumeric, underscore, hyphen
 * - $ - End of string (no trailing special chars)
 *
 * Examples of VALID names: "my-container", "Container123", "my_container"
 * Examples of INVALID names: "my container", "my;container", "my-container && malicious", "../../etc/passwd"
 */
const CONTAINER_NAME_PATTERN = /^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$/;

// Container status
export type ContainerStatus = 'running' | 'stopped' | 'not-found';

// Container info
export interface ContainerInfo {
  name: string;
  status: ContainerStatus;
  exists: boolean;
  ports: string | undefined;
  uptime: string | undefined;
}

// Network info
export interface NetworkInfo {
  name: string;
  exists: boolean;
  subnet: string | undefined;
}

// Execution options
export interface ExecOptions {
  silent?: boolean;
  timeout?: number;
}

// Command result
export interface CommandResult {
  success: boolean;
  stdout: string;
  stderr: string;
  exitCode: number;
}

/**
 * Database backend type
 */
export type DatabaseBackend = 'falkordb' | 'neo4j';

/**
 * Security error for invalid container names
 */
export class ContainerValidationError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ContainerValidationError';
  }
}

/**
 * Validate a container/network/volume name to prevent injection attacks
 *
 * @param name - The name to validate
 * @param context - Description of what is being validated (for error messages)
 * @throws ContainerValidationError if name contains invalid characters
 *
 * @example
 * validateName('my-container', 'container') // OK
 * validateName('my;container', 'container') // throws
 * validateName('../../etc/passwd', 'volume') // throws
 */
export function validateName(name: string, context = 'resource'): void {
  if (!name || typeof name !== 'string') {
    throw new ContainerValidationError(`Invalid ${context} name: must be a non-empty string`);
  }

  if (!CONTAINER_NAME_PATTERN.test(name)) {
    throw new ContainerValidationError(
      `Invalid ${context} name "${name}": must contain only alphanumeric characters, hyphens, and underscores, and must start with alphanumeric (max 64 characters)`
    );
  }
}

/**
 * Container Manager class
 */
export class ContainerManager {
  private runtime: ContainerRuntime;
  private runtimeCommand: string;

  // Default container names - FalkorDB backend
  static readonly FALKORDB_CONTAINER = 'madeinoz-knowledge-falkordb';
  static readonly MCP_CONTAINER = 'madeinoz-knowledge-graph-mcp';
  static readonly NETWORK_NAME = 'madeinoz-knowledge-net';
  static readonly VOLUME_NAME = 'madeinoz-knowledge-falkordb-data';

  // Neo4j backend container names
  static readonly NEO4J_CONTAINER = 'madeinoz-knowledge-neo4j';
  static readonly NEO4J_VOLUME_DATA = 'madeinoz-knowledge-neo4j-data';
  static readonly NEO4J_VOLUME_LOGS = 'madeinoz-knowledge-neo4j-logs';

  // Container images per backend
  static readonly IMAGES = {
    falkordb: {
      database: 'falkordb/falkordb:latest',
      mcp: 'madeinoz-knowledge-system:fixed', // Custom image with patches
    },
    neo4j: {
      database: 'neo4j:5.26.0',
      mcp: 'madeinoz-knowledge-system:fixed', // Custom image with patches
    },
  } as const;

  // Port mappings per backend
  static readonly PORTS = {
    falkordb: {
      database: ['3000:3000'], // FalkorDB web UI
      mcp: ['8000:8000'], // MCP HTTP endpoint
    },
    neo4j: {
      database: ['7474:7474', '7687:7687'], // Neo4j Browser + Bolt
      mcp: ['8000:8000'], // MCP HTTP endpoint
    },
  } as const;

  constructor(runtime?: ContainerRuntime) {
    if (runtime) {
      this.runtime = runtime;
      this.runtimeCommand = runtime;
    } else {
      const detected = this.detectRuntime();
      this.runtime = detected;
      this.runtimeCommand = detected;
    }
  }

  /**
   * Detect available container runtime (synchronous)
   */
  detectRuntime(): ContainerRuntime {
    // Use Bun.spawnSync for synchronous detection
    try {
      const podmanCheck = Bun.spawnSync(['which', 'podman']);
      if (podmanCheck.exitCode === 0) {
        return 'podman';
      }
    } catch {
      // Podman not found, try Docker
    }

    try {
      const dockerCheck = Bun.spawnSync(['which', 'docker']);
      if (dockerCheck.exitCode === 0) {
        return 'docker';
      }
    } catch {
      // Docker not found
    }

    return 'none';
  }

  /**
   * Get the detected runtime
   */
  getRuntime(): ContainerRuntime {
    return this.runtime;
  }

  /**
   * Get the runtime command for display purposes
   */
  getRuntimeCommand(): string {
    return this.runtimeCommand;
  }

  /**
   * Check if runtime is available
   */
  isRuntimeAvailable(): boolean {
    return this.runtime !== 'none';
  }

  /**
   * Execute a container command
   */
  async exec(args: string[], _options: ExecOptions = {}): Promise<CommandResult> {
    if (!this.isRuntimeAvailable()) {
      return {
        success: false,
        stdout: '',
        stderr: 'No container runtime found',
        exitCode: 1,
      };
    }

    try {
      // Use Bun.spawn for proper async execution
      const proc = Bun.spawn([this.runtimeCommand, ...args], {
        stdout: 'pipe',
        stderr: 'pipe',
      });

      const stdout = await new Response(proc.stdout).text();
      const stderr = await new Response(proc.stderr).text();
      const exitCode = await proc.exited;

      return {
        success: exitCode === 0,
        stdout: stdout.trim(),
        stderr: stderr.trim(),
        exitCode,
      };
    } catch (error: any) {
      return {
        success: false,
        stdout: '',
        stderr: error?.message || 'Unknown error',
        exitCode: error?.exitCode || 1,
      };
    }
  }

  /**
   * Check if a network exists
   */
  async networkExists(networkName: string): Promise<boolean> {
    validateName(networkName, 'network');
    const result = await this.exec(['network', 'inspect', networkName], {
      silent: true,
    });
    return result.success;
  }

  /**
   * Create a network
   */
  async createNetwork(networkName: string, subnet?: string): Promise<CommandResult> {
    validateName(networkName, 'network');
    const args = ['network', 'create', '--driver', 'bridge'];

    if (subnet) {
      args.push('--subnet', subnet);
    }

    args.push(networkName);

    return await this.exec(args);
  }

  /**
   * Get network information
   */
  async getNetworkInfo(networkName: string): Promise<NetworkInfo> {
    validateName(networkName, 'network');
    const exists = await this.networkExists(networkName);

    if (!exists) {
      return { name: networkName, exists: false, subnet: undefined };
    }

    // Try to get subnet info
    const result = await this.exec(
      ['network', 'inspect', '--format', '{{range .IPAM.Config}}{{.Subnet}}{{end}}', networkName],
      { silent: true }
    );

    return {
      name: networkName,
      exists: true,
      subnet: result.success ? result.stdout : undefined,
    };
  }

  /**
   * Check if a container exists
   */
  async containerExists(containerName: string): Promise<boolean> {
    validateName(containerName, 'container');
    const result = await this.exec(['ps', '-a', '--format', '{{.Names}}'], {
      silent: true,
    });

    if (!result.success) {
      return false;
    }

    const containers = result.stdout.split('\n').filter((line) => line.trim());
    return containers.includes(containerName);
  }

  /**
   * Check if a container is running
   */
  async isContainerRunning(containerName: string): Promise<boolean> {
    validateName(containerName, 'container');
    const result = await this.exec(['ps', '--format', '{{.Names}}'], {
      silent: true,
    });

    if (!result.success) {
      return false;
    }

    const runningContainers = result.stdout.split('\n').filter((line) => line.trim());
    return runningContainers.includes(containerName);
  }

  /**
   * Get container information
   */
  async getContainerInfo(containerName: string): Promise<ContainerInfo> {
    validateName(containerName, 'container');
    const exists = await this.containerExists(containerName);

    if (!exists) {
      return {
        name: containerName,
        status: 'not-found',
        exists: false,
        ports: undefined,
        uptime: undefined,
      };
    }

    const isRunning = await this.isContainerRunning(containerName);

    // Get detailed status
    const statusResult = await this.exec(
      ['ps', '-a', '--filter', `name=${containerName}`, '--format', '{{.Status}}'],
      { silent: true }
    );

    // Get port mappings
    const portsResult = await this.exec(
      ['ps', '--filter', `name=${containerName}`, '--format', '{{.Ports}}'],
      { silent: true }
    );

    return {
      name: containerName,
      status: isRunning ? 'running' : 'stopped',
      exists: true,
      ports: portsResult.success ? portsResult.stdout : undefined,
      uptime: statusResult.success ? statusResult.stdout : undefined,
    };
  }

  /**
   * Start a container
   */
  async startContainer(containerName: string): Promise<CommandResult> {
    validateName(containerName, 'container');
    return await this.exec(['start', containerName]);
  }

  /**
   * Stop a container
   */
  async stopContainer(containerName: string): Promise<CommandResult> {
    validateName(containerName, 'container');
    return await this.exec(['stop', containerName]);
  }

  /**
   * Restart a container
   */
  async restartContainer(containerName: string): Promise<CommandResult> {
    validateName(containerName, 'container');
    return await this.exec(['restart', containerName]);
  }

  /**
   * Remove a container
   */
  async removeContainer(containerName: string): Promise<CommandResult> {
    validateName(containerName, 'container');
    return await this.exec(['rm', containerName]);
  }

  /**
   * Stop and remove a container
   */
  async stopAndRemoveContainer(containerName: string): Promise<CommandResult> {
    validateName(containerName, 'container');
    await this.stopContainer(containerName);
    await new Promise((resolve) => setTimeout(resolve, 1000));
    return await this.removeContainer(containerName);
  }

  /**
   * Run a new container
   */
  async runContainer(args: string[]): Promise<CommandResult> {
    return await this.exec(['run', '-d', ...args]);
  }

  /**
   * Get container logs
   */
  async getLogs(containerName: string, follow = false): Promise<CommandResult> {
    validateName(containerName, 'container');
    const args = ['logs'];
    if (follow) {
      args.push('-f');
    }
    args.push(containerName);

    // Note: For follow=true, this will hang until interrupted
    // Caller should handle streaming appropriately
    return await this.exec(args);
  }

  /**
   * Get container stats (resource usage)
   */
  async getStats(containerName: string): Promise<CommandResult> {
    validateName(containerName, 'container');
    return await this.exec(
      [
        'stats',
        containerName,
        '--no-stream',
        '--format',
        'table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}',
      ],
      { silent: true }
    );
  }

  /**
   * Create a volume
   */
  async createVolume(volumeName: string): Promise<CommandResult> {
    validateName(volumeName, 'volume');
    return await this.exec(['volume', 'create', volumeName]);
  }

  /**
   * Check if a volume exists
   */
  async volumeExists(volumeName: string): Promise<boolean> {
    validateName(volumeName, 'volume');
    const result = await this.exec(['volume', 'inspect', volumeName], {
      silent: true,
    });
    return result.success;
  }

  /**
   * List all containers (including stopped)
   */
  async listContainers(all = true): Promise<CommandResult> {
    return await this.exec(['ps', all ? '-a' : '', '--format', '{{.Names}}'], {
      silent: true,
    });
  }

  /**
   * Export a container to a tar file
   */
  async exportContainer(containerName: string, outputPath: string): Promise<CommandResult> {
    validateName(containerName, 'container');
    // outputPath is not a container name, but we should still validate it's safe
    // Only allow absolute paths or paths relative to current directory, no parent traversal
    if (outputPath.includes('..')) {
      throw new ContainerValidationError(
        `Invalid export path "${outputPath}": parent directory traversal not allowed`
      );
    }
    return await this.exec(['export', containerName, '-o', outputPath]);
  }

  /**
   * Parse container name from various formats
   * SECURITY: Also validates the normalized name
   */
  static normalizeContainerName(name: string): string {
    const normalized = name.replace(/^[\/*]/, '').replace(/\/$/, '');
    // Validate the normalized name before returning
    try {
      validateName(normalized, 'container');
      return normalized;
    } catch {
      throw new ContainerValidationError(
        `Invalid container name "${name}": after normalization, "${normalized}" is not a valid container name`
      );
    }
  }
}

/**
 * Create a container manager instance with auto-detected runtime
 */
export function createContainerManager(): ContainerManager {
  return new ContainerManager();
}

/**
 * Create a container manager instance with specific runtime
 */
export function createContainerManagerWithRuntime(runtime: ContainerRuntime): ContainerManager {
  if (runtime === 'none') {
    throw new Error("Cannot create container manager with runtime 'none'");
  }
  return new ContainerManager(runtime);
}

/**
 * Docker Compose Manager class
 *
 * Provides docker-compose orchestration for Madeinoz Knowledge System.
 * This is the preferred way to manage containers (vs raw docker commands).
 */
export class ComposeManager {
  private containerManager: ContainerManager;
  private serverDir: string;

  // Compose file paths relative to server directory
  static readonly COMPOSE_FILES = {
    neo4j: 'docker-compose-neo4j.yml',
    falkordb: 'docker-compose-falkordb.yml',
    neo4jDev: 'docker-compose-neo4j-dev.yml',
    falkordbDev: 'docker-compose-falkordb-dev.yml',
  } as const;

  // Generated env file paths
  static readonly ENV_FILES = {
    neo4j: '/tmp/madeinoz-knowledge-neo4j.env',
    mcp: '/tmp/madeinoz-knowledge-mcp.env',
    neo4jDev: '/tmp/madeinoz-knowledge-neo4j-dev.env',
    mcpDev: '/tmp/madeinoz-knowledge-mcp-dev.env',
  } as const;

  constructor(serverDir?: string) {
    this.containerManager = createContainerManager();
    // Default to src/server directory
    this.serverDir = serverDir || join(import.meta.dir, '..');
  }

  /**
   * Get the container runtime command
   */
  getRuntimeCommand(): string {
    return this.containerManager.getRuntimeCommand();
  }

  /**
   * Check if runtime is available
   */
  isRuntimeAvailable(): boolean {
    return this.containerManager.isRuntimeAvailable();
  }

  /**
   * Get the compose file path for a database type
   */
  getComposeFilePath(databaseType: DatabaseBackend, devMode = false): string {
    if (devMode) {
      const devKey = `${databaseType}Dev` as keyof typeof ComposeManager.COMPOSE_FILES;
      return join(this.serverDir, ComposeManager.COMPOSE_FILES[devKey]);
    }
    return join(this.serverDir, ComposeManager.COMPOSE_FILES[databaseType]);
  }

  /**
   * Get env file paths for a mode
   */
  getEnvFilePaths(devMode = false): { neo4j: string; mcp: string } {
    if (devMode) {
      return {
        neo4j: ComposeManager.ENV_FILES.neo4jDev,
        mcp: ComposeManager.ENV_FILES.mcpDev,
      };
    }
    return {
      neo4j: ComposeManager.ENV_FILES.neo4j,
      mcp: ComposeManager.ENV_FILES.mcp,
    };
  }

  /**
   * Execute a compose command
   */
  async execCompose(composeFile: string, args: string[], envFile?: string): Promise<CommandResult> {
    if (!this.containerManager.isRuntimeAvailable()) {
      return {
        success: false,
        stdout: '',
        stderr: 'No container runtime found',
        exitCode: 1,
      };
    }

    const runtime = this.containerManager.getRuntimeCommand();
    const cmdArgs = ['compose', '-f', composeFile];

    if (envFile) {
      cmdArgs.push('--env-file', envFile);
    }

    cmdArgs.push(...args);

    try {
      const proc = Bun.spawn([runtime, ...cmdArgs], {
        stdout: 'pipe',
        stderr: 'pipe',
        cwd: this.serverDir,
      });

      const stdout = await new Response(proc.stdout).text();
      const stderr = await new Response(proc.stderr).text();
      const exitCode = await proc.exited;

      return {
        success: exitCode === 0,
        stdout: stdout.trim(),
        stderr: stderr.trim(),
        exitCode,
      };
    } catch (error: any) {
      return {
        success: false,
        stdout: '',
        stderr: error?.message || 'Unknown error',
        exitCode: error?.exitCode || 1,
      };
    }
  }

  /**
   * Start containers using docker-compose up
   */
  async up(
    databaseType: DatabaseBackend,
    devMode = false,
    extraArgs: string[] = []
  ): Promise<CommandResult> {
    const composeFile = this.getComposeFilePath(databaseType, devMode);
    const envFiles = this.getEnvFilePaths(devMode);

    return await this.execCompose(composeFile, ['up', '-d', ...extraArgs], envFiles.neo4j);
  }

  /**
   * Stop containers using docker-compose down
   * NOTE: Never uses -v flag to preserve data volumes
   */
  async down(databaseType: DatabaseBackend, devMode = false): Promise<CommandResult> {
    const composeFile = this.getComposeFilePath(databaseType, devMode);
    const envFiles = this.getEnvFilePaths(devMode);

    // CRITICAL: Never use -v flag - this destroys data volumes!
    return await this.execCompose(composeFile, ['down'], envFiles.neo4j);
  }

  /**
   * Get container status using docker-compose ps
   */
  async ps(databaseType: DatabaseBackend, devMode = false): Promise<CommandResult> {
    const composeFile = this.getComposeFilePath(databaseType, devMode);
    const envFiles = this.getEnvFilePaths(devMode);

    // Don't use --format flag as it's not supported by all compose versions
    return await this.execCompose(composeFile, ['ps'], envFiles.neo4j);
  }

  /**
   * Get container logs using docker-compose logs
   */
  async logs(
    databaseType: DatabaseBackend,
    service?: string,
    follow = false,
    devMode = false,
    tail?: number
  ): Promise<CommandResult> {
    const composeFile = this.getComposeFilePath(databaseType, devMode);
    const envFiles = this.getEnvFilePaths(devMode);

    const args = ['logs'];
    if (follow) {
      args.push('-f');
    }
    if (tail) {
      args.push('--tail', tail.toString());
    }
    if (service) {
      args.push(service);
    }

    return await this.execCompose(composeFile, args, envFiles.neo4j);
  }

  /**
   * Restart containers using docker-compose restart
   */
  async restart(
    databaseType: DatabaseBackend,
    service?: string,
    devMode = false
  ): Promise<CommandResult> {
    const composeFile = this.getComposeFilePath(databaseType, devMode);
    const envFiles = this.getEnvFilePaths(devMode);

    const args = ['restart'];
    if (service) {
      args.push(service);
    }

    return await this.execCompose(composeFile, args, envFiles.neo4j);
  }

  /**
   * Check if compose services are running
   */
  async isRunning(databaseType: DatabaseBackend, devMode = false): Promise<boolean> {
    const result = await this.ps(databaseType, devMode);
    if (!result.success) {
      return false;
    }
    // Check if any services are running (not just headers)
    const lines = result.stdout.split('\n').filter((line) => line.trim());
    // More than just the header line means services exist
    return lines.length > 1 && result.stdout.includes('running');
  }
}

/**
 * Create a compose manager instance
 */
export function createComposeManager(serverDir?: string): ComposeManager {
  return new ComposeManager(serverDir);
}
