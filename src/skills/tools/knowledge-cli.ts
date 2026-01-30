#!/usr/bin/env bun
/**
 * Knowledge CLI for Madeinoz Knowledge System
 *
 * This script provides a simple command-line interface to the Graphiti MCP server.
 * It handles JSON-RPC communication and provides compact, token-efficient output.
 *
 * Usage:
 *   bun run src/skills/tools/knowledge-cli.ts add_episode "Episode title" "Episode body"
 *   bun run src/skills/tools/knowledge-cli.ts search_nodes "search query"
 *   bun run src/skills/tools/knowledge-cli.ts get_status
 *
 * Flags:
 *   --raw          Output raw JSON instead of compact format
 *   --metrics      Display token metrics after each operation
 *   --metrics-file Write metrics to JSONL file
 */

import { createMCPClient, type MCPClientConfigExtended, type MCPClient } from '../lib/mcp-client';
import { cli } from '../lib/cli';
import { formatOutput, type FormatOptions } from '../lib/output-formatter';
import {
  profileManager,
  loadProfileWithOverrides,
  getProfileName,
  type ConnectionState,
} from '../lib/connection-profile';

/**
 * Command definitions
 */
interface Command {
  name: string;
  description: string;
  handler: (
    args: string[]
  ) => Promise<{ success: boolean; data?: unknown; error?: string; query?: string }>;
}

/**
 * CLI flags parsed from arguments
 */
interface CLIFlags {
  raw: boolean;
  metrics: boolean;
  metricsFile?: string;
  help: boolean;
  since?: string;
  until?: string;
  profile?: string;
  host?: string;
  port?: string;
  protocol?: string;
  tlsNoVerify?: boolean;
}

/**
 * Parse CLI flags from arguments
 */
function parseFlags(args: string[]): { flags: CLIFlags; positionalArgs: string[] } {
  const flags: CLIFlags = {
    raw: false,
    metrics: false,
    metricsFile: undefined,
    help: false,
    since: undefined,
    until: undefined,
    profile: undefined,
    host: undefined,
    port: undefined,
    protocol: undefined,
    tlsNoVerify: undefined,
  };
  const positionalArgs: string[] = [];

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg === '--raw') {
      flags.raw = true;
    } else if (arg === '--metrics') {
      flags.metrics = true;
    } else if (arg === '--metrics-file') {
      flags.metricsFile = args[++i];
    } else if (arg === '-h' || arg === '--help') {
      flags.help = true;
    } else if (arg === '--since') {
      flags.since = args[++i];
    } else if (arg === '--until') {
      flags.until = args[++i];
    } else if (arg === '--profile') {
      flags.profile = args[++i];
    } else if (arg === '--host') {
      flags.host = args[++i];
    } else if (arg === '--port') {
      flags.port = args[++i];
    } else if (arg === '--protocol') {
      flags.protocol = args[++i];
    } else if (arg === '--tls-no-verify') {
      flags.tlsNoVerify = true;
    } else if (!arg.startsWith('--')) {
      positionalArgs.push(arg);
    }
  }

  return { flags, positionalArgs };
}

/**
 * MCP Wrapper class
 */
class MCPWrapper {
  private commands: Map<string, Command>;
  private flags: CLIFlags;

  constructor(flags: CLIFlags) {
    this.commands = new Map();
    this.flags = flags;
    this.registerCommands();
  }

  /**
   * Create MCP client with CLI flags applied
   *
   * T017 [US1]: Add --host, --port, --protocol CLI flags
   * T016 [US1]: Add environment variable parsing
   *
   * Priority order (highest to lowest):
   * 1. CLI flags (--host, --port, --protocol, --profile)
   * 2. Individual environment variables (MADEINOZ_KNOWLEDGE_HOST, etc.)
   * 3. Profile from MADEINOZ_KNOWLEDGE_PROFILE environment variable
   * 4. Default profile from YAML file
   * 5. Code defaults (localhost:8001, http)
   */
  private createClient(): MCPClient {
    // Build config from CLI flags
    const cliConfig: MCPClientConfigExtended = {};

    // Apply CLI flags if provided
    if (this.flags.host) {
      cliConfig.host = this.flags.host;
    }
    if (this.flags.port) {
      cliConfig.port = Number.parseInt(this.flags.port, 10);
    }
    if (this.flags.protocol) {
      cliConfig.protocol = this.flags.protocol as 'http' | 'https';
    }
    if (this.flags.profile) {
      cliConfig.profile = this.flags.profile;
    }
    if (this.flags.tlsNoVerify) {
      cliConfig.tls = { ...cliConfig.tls, verify: false };
    }

    // If any CLI flags provided, create client with that config
    if (Object.keys(cliConfig).length > 0) {
      return createMCPClient(cliConfig);
    }

    // Otherwise use default (environment variables, profiles, or code defaults)
    return createMCPClient();
  }

  /**
   * Register all available commands
   */
  private registerCommands(): void {
    this.addCommand({
      name: 'add_episode',
      description: 'Add knowledge to graph',
      handler: this.cmdAddEpisode.bind(this),
    });

    this.addCommand({
      name: 'search_nodes',
      description: 'Search entities',
      handler: this.cmdSearchNodes.bind(this),
    });

    this.addCommand({
      name: 'search_facts',
      description: 'Search relationships',
      handler: this.cmdSearchFacts.bind(this),
    });

    this.addCommand({
      name: 'get_episodes',
      description: 'Get recent episodes',
      handler: this.cmdGetEpisodes.bind(this),
    });

    this.addCommand({
      name: 'get_status',
      description: 'Get graph status',
      handler: this.cmdGetStatus.bind(this),
    });

    this.addCommand({
      name: 'clear_graph',
      description: 'Delete all knowledge',
      handler: this.cmdClearGraph.bind(this),
    });

    this.addCommand({
      name: 'health',
      description: 'Check server health',
      handler: this.cmdHealth.bind(this),
    });

    // Feature 009: Memory decay commands
    this.addCommand({
      name: 'health_metrics',
      description: 'Get memory lifecycle health metrics',
      handler: this.cmdHealthMetrics.bind(this),
    });

    this.addCommand({
      name: 'run_maintenance',
      description: 'Run decay maintenance cycle',
      handler: this.cmdRunMaintenance.bind(this),
    });

    this.addCommand({
      name: 'classify_memory',
      description: 'Classify memory importance and stability',
      handler: this.cmdClassifyMemory.bind(this),
    });

    this.addCommand({
      name: 'recover_memory',
      description: 'Recover a soft-deleted memory',
      handler: this.cmdRecoverMemory.bind(this),
    });

    // Feature 010: Connection profile commands
    this.addCommand({
      name: 'list_profiles',
      description: 'List available connection profiles',
      handler: this.cmdListProfiles.bind(this),
    });

    this.addCommand({
      name: 'status',
      description: 'Show connection status and current profile',
      handler: this.cmdStatus.bind(this),
    });
  }

  /**
   * Add a command
   */
  private addCommand(command: Command): void {
    this.commands.set(command.name, command);
  }

  /**
   * Get a command by name
   */
  private getCommand(name: string): Command | undefined {
    return this.commands.get(name);
  }

  /**
   * List all available commands
   */
  listCommands(): Command[] {
    return Array.from(this.commands.values());
  }

  /**
   * Command: add_episode
   */
  private async cmdAddEpisode(
    args: string[]
  ): Promise<{ success: boolean; data?: unknown; error?: string }> {
    if (args.length < 2) {
      return {
        success: false,
        error: 'Usage: add_episode <title> <body> [source_description]',
      };
    }

    const title = args[0];
    const body = args[1];
    const sourceDescription = args[2];

    const client = this.createClient();
    const result = await client.addEpisode({
      name: title,
      episode_body: body,
      source_description: sourceDescription,
    });

    return result;
  }

  /**
   * Command: search_nodes
   */
  private async cmdSearchNodes(
    args: string[]
  ): Promise<{ success: boolean; data?: unknown; error?: string; query?: string }> {
    if (args.length < 1) {
      return {
        success: false,
        error: 'Usage: search_nodes <query> [limit] [--since <date>] [--until <date>]',
      };
    }

    const query = args[0];
    const limit = args.length > 1 ? Number.parseInt(args[1], 10) : 5;

    const client = this.createClient();
    const result = await client.searchNodes({
      query,
      limit,
      since: this.flags.since,
      until: this.flags.until,
    });

    return { ...result, query };
  }

  /**
   * Command: search_facts
   */
  private async cmdSearchFacts(
    args: string[]
  ): Promise<{ success: boolean; data?: unknown; error?: string; query?: string }> {
    if (args.length < 1) {
      return {
        success: false,
        error: 'Usage: search_facts <query> [limit] [--since <date>] [--until <date>]',
      };
    }

    const query = args[0];
    const limit = args.length > 1 ? Number.parseInt(args[1], 10) : 5;

    const client = this.createClient();
    const result = await client.searchFacts({
      query,
      max_facts: limit,
      since: this.flags.since,
      until: this.flags.until,
    });

    return { ...result, query };
  }

  /**
   * Command: get_episodes
   */
  private async cmdGetEpisodes(
    args: string[]
  ): Promise<{ success: boolean; data?: unknown; error?: string }> {
    const limit = args.length > 0 ? Number.parseInt(args[0], 10) : 5;

    const client = this.createClient();
    const result = await client.getEpisodes({ limit });

    return result;
  }

  /**
   * Command: get_status
   */
  private async cmdGetStatus(): Promise<{ success: boolean; data?: unknown; error?: string }> {
    const client = this.createClient();
    const result = await client.getStatus();

    return result;
  }

  /**
   * Command: clear_graph
   */
  private async cmdClearGraph(
    args: string[]
  ): Promise<{ success: boolean; data?: unknown; error?: string }> {
    // Safety check
    if (!args.includes('--force')) {
      return {
        success: false,
        error: 'This will delete ALL knowledge. Use --force to confirm.',
      };
    }

    const client = this.createClient();
    const result = await client.clearGraph();

    return result;
  }

  /**
   * Command: health
   */
  private async cmdHealth(): Promise<{ success: boolean; data?: unknown; error?: string }> {
    const client = this.createClient();
    const result = await client.testConnection();

    return result;
  }

  /**
   * Feature 009: Command: health_metrics
   */
  private async cmdHealthMetrics(
    args: string[]
  ): Promise<{ success: boolean; data?: unknown; error?: string }> {
    // Parse optional --group-id flag
    const groupId = args.includes('--group-id')
      ? args[args.indexOf('--group-id') + 1]
      : undefined;

    const client = this.createClient();
    const result = await client.getKnowledgeHealth({ group_id: groupId });

    return result;
  }

  /**
   * Feature 009: Command: run_maintenance
   */
  private async cmdRunMaintenance(
    args: string[]
  ): Promise<{ success: boolean; data?: unknown; error?: string }> {
    const dryRun = args.includes('--dry-run');

    const client = this.createClient();
    const result = await client.runDecayMaintenance({ dry_run: dryRun });

    return result;
  }

  /**
   * Feature 009: Command: classify_memory
   */
  private async cmdClassifyMemory(
    args: string[]
  ): Promise<{ success: boolean; data?: unknown; error?: string }> {
    if (args.length < 1) {
      return {
        success: false,
        error: 'Usage: classify_memory <content> [--source <description>]',
      };
    }

    const content = args[0];
    const sourceIdx = args.indexOf('--source');
    const sourceDescription = sourceIdx >= 0 ? args[sourceIdx + 1] : undefined;

    const client = this.createClient();
    const result = await client.classifyMemory({
      content,
      source_description: sourceDescription,
    });

    return result;
  }

  /**
   * Feature 009: Command: recover_memory
   */
  private async cmdRecoverMemory(
    args: string[]
  ): Promise<{ success: boolean; data?: unknown; error?: string }> {
    if (args.length < 1) {
      return {
        success: false,
        error: 'Usage: recover_memory <uuid>',
      };
    }

    const uuid = args[0];

    const client = this.createClient();
    const result = await client.recoverSoftDeleted({ uuid });

    return result;
  }

  /**
   * Feature 010: Command: list_profiles
   */
  private async cmdListProfiles(): Promise<{ success: boolean; data?: unknown; error?: string }> {
    try {
      const profiles = profileManager.listProfiles();
      const defaultProfile = profileManager.getDefaultProfile();
      const currentProfile = this.flags.profile || getProfileName();
      const configPath = profileManager.getConfigPath();

      const data = {
        default: defaultProfile,
        current: currentProfile,
        profiles: profiles,
        config_path: configPath,
        count: profiles.length,
      };

      return { success: true, data };
    } catch (error) {
      if (error instanceof Error) {
        return { success: false, error: error.message };
      }
      return { success: false, error: 'Unknown error' };
    }
  }

  /**
   * Feature 010: Command: status
   */
  private async cmdStatus(): Promise<{ success: boolean; data?: unknown; error?: string }> {
    try {
      // Get current profile
      const profileName = this.flags.profile || getProfileName();
      const profile = loadProfileWithOverrides(profileName);

      // Apply CLI flag overrides (highest priority)
      const effectiveHost = this.flags.host || profile.host;
      const effectivePort = this.flags.port ? Number.parseInt(this.flags.port, 10) : profile.port;
      const effectiveProtocol = (this.flags.protocol as 'http' | 'https' | undefined) || profile.protocol;

      // Test connection with overridden values
      const client = createMCPClient({
        protocol: effectiveProtocol,
        host: effectiveHost,
        port: effectivePort,
        basePath: profile.basePath,
        timeout: profile.timeout,
      });

      const healthResult = await client.testConnection();

      const connectionState: ConnectionState = {
        profile: profileName,
        host: effectiveHost,
        port: effectivePort,
        protocol: effectiveProtocol,
        status: healthResult.success ? 'connected' : 'error',
        lastError: healthResult.success ? undefined : healthResult.error,
      };

      if (healthResult.success && healthResult.data) {
        const healthData = healthResult.data as { status: string; version?: string };
        connectionState.serverVersion = healthData.version;
        connectionState.lastConnected = new Date();
      }

      return { success: true, data: connectionState };
    } catch (error) {
      if (error instanceof Error) {
        return { success: false, error: error.message };
      }
      return { success: false, error: 'Unknown error' };
    }
  }

  /**
   * Print help message
   */
  printHelp(): void {
    cli.blank();
    cli.header('Madeinoz Knowledge System - Knowledge CLI', 60);
    cli.blank();
    cli.info('Token-efficient command-line interface to the Graphiti MCP server.');
    cli.info('Achieves 25-35% token savings through compact output formatting.');
    cli.blank();
    cli.info('Usage:');
    cli.dim('  bun run src/skills/tools/knowledge-cli.ts <command> [args...] [options]');
    cli.blank();
    cli.info('Commands:');
    cli.blank();

    const commands = this.listCommands();
    const maxLength = Math.max(...commands.map((c) => c.name.length));

    commands.forEach((cmd) => {
      const paddedName = cmd.name.padEnd(maxLength);
      cli.dim(`  ${paddedName}  ${cmd.description}`);
    });

    cli.blank();
    cli.info('Options:');
    cli.blank();
    cli.dim('  --raw              Output raw JSON instead of compact format');
    cli.dim('  --metrics          Display token metrics after each operation');
    cli.dim('  --metrics-file <p> Write metrics to JSONL file');
    cli.dim('  --since <date>     Filter results created after this date');
    cli.dim('  --until <date>     Filter results created before this date');
    cli.dim('  --profile <name>   Use specific connection profile');
    cli.dim('  --host <hostname>  Override profile host');
    cli.dim('  --port <port>      Override profile port');
    cli.dim('  --protocol <proto> Override profile protocol (http/https)');
    cli.dim('  --tls-no-verify    Disable TLS certificate verification');
    cli.dim('  -h, --help         Show this help message');
    cli.blank();
    cli.info('Date Formats (for --since/--until):');
    cli.blank();
    cli.dim('  ISO 8601:  2026-01-26, 2026-01-26T00:00:00Z');
    cli.dim('  Relative:  today, yesterday, now');
    cli.dim('  Duration:  7d, 7 days, 1w, 1 week, 1m, 1 month');
    cli.dim('             (all relative dates look backward from now)');
    cli.blank();
    cli.info('Environment Variables:');
    cli.blank();
    cli.dim("  MADEINOZ_WRAPPER_COMPACT       Set to 'false' to disable compact output");
    cli.dim("  MADEINOZ_WRAPPER_METRICS       Set to 'true' to enable metrics collection");
    cli.dim('  MADEINOZ_WRAPPER_METRICS_FILE  Path to write metrics JSONL file');
    cli.dim('  MADEINOZ_WRAPPER_LOG_FILE      Path to write transformation error logs');
    cli.dim('  MADEINOZ_WRAPPER_SLOW_THRESHOLD Slow processing threshold in ms (default: 50)');
    cli.dim('  MADEINOZ_WRAPPER_TIMEOUT       Processing timeout in ms (default: 100)');
    cli.blank();
    cli.info('TLS/SSL Environment Variables (Feature 010):');
    cli.blank();
    cli.dim('  MADEINOZ_KNOWLEDGE_PROTOCOL    http or https (default: http)');
    cli.dim('  MADEINOZ_KNOWLEDGE_HOST        Hostname or IP address (default: localhost)');
    cli.dim('  MADEINOZ_KNOWLEDGE_PORT         TCP port (default: 8001)');
    cli.dim('  MADEINOZ_KNOWLEDGE_TLS_VERIFY  Enable certificate verification (default: true)');
    cli.dim('  MADEINOZ_KNOWLEDGE_TLS_CA       Path to CA certificate file');
    cli.dim('  MADEINOZ_KNOWLEDGE_TLS_CERT     Path to client certificate file');
    cli.dim('  MADEINOZ_KNOWLEDGE_TLS_KEY      Path to client private key file');
    cli.blank();
    cli.info('Examples:');
    cli.blank();
    cli.dim('  # Add knowledge to graph');
    cli.dim(
      '  bun run src/skills/tools/knowledge-cli.ts add_episode "Test Episode" "This is a test episode"'
    );
    cli.blank();
    cli.dim('  # Search for entities (compact output, 30%+ token savings)');
    cli.dim('  bun run src/skills/tools/knowledge-cli.ts search_nodes "PAI" 10');
    cli.blank();
    cli.dim('  # Search with raw JSON output');
    cli.dim('  bun run src/skills/tools/knowledge-cli.ts search_nodes "PAI" --raw');
    cli.blank();
    cli.dim('  # Search with metrics display');
    cli.dim('  bun run src/skills/tools/knowledge-cli.ts search_nodes "PAI" --metrics');
    cli.blank();
    cli.dim('  # Save metrics to file for analysis');
    cli.dim(
      '  bun run src/skills/tools/knowledge-cli.ts search_nodes "PAI" --metrics-file ~/.madeinoz-knowledge/metrics.jsonl'
    );
    cli.blank();
    cli.dim('  # Get graph status');
    cli.dim('  bun run src/skills/tools/knowledge-cli.ts get_status');
    cli.blank();
    cli.dim('  # Check server health');
    cli.dim('  bun run src/skills/tools/knowledge-cli.ts health');
    cli.blank();
    cli.dim('  # Clear graph (destructive - requires --force)');
    cli.dim('  bun run src/skills/tools/knowledge-cli.ts clear_graph --force');
    cli.blank();
    cli.dim('  # Feature 009: Memory decay and lifecycle');
    cli.blank();
    cli.dim('  # Get memory lifecycle health metrics');
    cli.dim('  bun run src/skills/tools/knowledge-cli.ts health_metrics');
    cli.blank();
    cli.dim('  # Run decay maintenance cycle');
    cli.dim('  bun run src/skills/tools/knowledge-cli.ts run_maintenance');
    cli.dim('  bun run src/skills/tools/knowledge-cli.ts run_maintenance --dry-run');
    cli.blank();
    cli.dim('  # Classify memory importance and stability');
    cli.dim('  bun run src/skills/tools/knowledge-cli.ts classify_memory "I prefer dark mode"');
    cli.dim('  bun run src/skills/tools/knowledge-cli.ts classify_memory "Allergic to peanuts" --source "medical"');
    cli.blank();
    cli.dim('  # Recover a soft-deleted memory');
    cli.dim('  bun run src/skills/tools/knowledge-cli.ts recover_memory abc123-def456-...');
    cli.blank();
    cli.info('Temporal Search Examples:');
    cli.blank();
    cli.dim("  # Search nodes from today");
    cli.dim('  bun run src/skills/tools/knowledge-cli.ts search_nodes "PAI" --since today');
    cli.blank();
    cli.dim("  # Search facts from last 7 days");
    cli.dim('  bun run src/skills/tools/knowledge-cli.ts search_facts "decisions" --since 7d');
    cli.blank();
    cli.dim("  # Search within a date range");
    cli.dim('  bun run src/skills/tools/knowledge-cli.ts search_nodes "project" --since 2026-01-01 --until 2026-01-15');
    cli.blank();
    cli.dim("  # Yesterday's knowledge only");
    cli.dim('  bun run src/skills/tools/knowledge-cli.ts search_nodes "learning" --since yesterday --until today');
    cli.blank();
    cli.dim("  # Last month's architecture decisions");
    cli.dim('  bun run src/skills/tools/knowledge-cli.ts search_facts "architecture" --since 1m');
    cli.blank();
  }

  /**
   * Execute a command
   */
  async execute(commandName: string, args: string[]): Promise<number> {
    const command = this.getCommand(commandName);

    if (!command) {
      cli.error(`Unknown command: ${commandName}`);
      cli.blank();
      cli.info(`Available commands: ${Array.from(this.commands.keys()).join(', ')}`);
      return 1;
    }

    // Execute command
    const result = await command.handler(args);

    // Output result
    if (result.success) {
      if (result.data !== undefined) {
        // Use raw JSON output if --raw flag is set
        if (this.flags.raw) {
          console.log(JSON.stringify(result.data, null, 2));
        } else {
          // Use compact formatter
          const formatOptions: FormatOptions = {
            collectMetrics: this.flags.metrics,
            query: result.query,
          };

          const formatted = formatOutput(commandName, result.data, formatOptions);
          console.log(formatted.output);

          // Show metrics if requested
          if (this.flags.metrics && formatted.metrics) {
            console.log();
            console.log('--- Token Metrics ---');
            console.log(`Operation: ${commandName}`);
            console.log(
              `Raw size: ${formatted.metrics.rawBytes.toLocaleString()} bytes (${Math.ceil(formatted.metrics.rawBytes / 4)} est. tokens)`
            );
            console.log(
              `Compact size: ${formatted.metrics.compactBytes.toLocaleString()} bytes (${Math.ceil(formatted.metrics.compactBytes / 4)} est. tokens)`
            );
            const tokensSaved =
              Math.ceil(formatted.metrics.rawBytes / 4) -
              Math.ceil(formatted.metrics.compactBytes / 4);
            console.log(
              `Savings: ${formatted.metrics.savingsPercent.toFixed(1)}% (${tokensSaved} tokens saved)`
            );
            console.log(`Processing time: ${formatted.metrics.processingTimeMs.toFixed(0)}ms`);
          }

          // Write to metrics file if specified
          if (this.flags.metricsFile && formatted.metrics) {
            const { appendFile, mkdir } = await import('node:fs/promises');
            const { dirname } = await import('node:path');

            try {
              await mkdir(dirname(this.flags.metricsFile), { recursive: true });
              const metricsLine = `${JSON.stringify({
                operation: commandName,
                timestamp: new Date().toISOString(),
                rawBytes: formatted.metrics.rawBytes,
                compactBytes: formatted.metrics.compactBytes,
                savingsPercent: formatted.metrics.savingsPercent,
                estimatedTokensBefore: Math.ceil(formatted.metrics.rawBytes / 4),
                estimatedTokensAfter: Math.ceil(formatted.metrics.compactBytes / 4),
                processingTimeMs: formatted.metrics.processingTimeMs,
              })}\n`;
              await appendFile(this.flags.metricsFile, metricsLine, 'utf-8');
            } catch (error) {
              cli.warning(`Failed to write metrics: ${error}`);
            }
          }
        }
      }
      return 0;
    }
    cli.error(`Error: ${result.error}`);
    return 1;
  }
}

/**
 * Main function
 */
async function main() {
  const { flags, positionalArgs } = parseFlags(process.argv.slice(2));

  // Show help if no arguments or help flag
  if (positionalArgs.length === 0 || flags.help) {
    const wrapper = new MCPWrapper(flags);
    wrapper.printHelp();
    process.exit(0);
  }

  // Execute command
  const commandName = positionalArgs[0];
  const commandArgs = positionalArgs.slice(1);

  const wrapper = new MCPWrapper(flags);
  const exitCode = await wrapper.execute(commandName, commandArgs);
  process.exit(exitCode);
}

// Run main function
main().catch((error) => {
  cli.error('Unexpected error:');
  console.error(error);
  process.exit(1);
});
