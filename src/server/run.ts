#!/usr/bin/env bun
/**
 * Run Madeinoz Knowledge System with Podman/Docker
 *
 * Supports two database backends:
 *   - Neo4j (default): Native graph database with Cypher queries
 *   - FalkorDB: Redis-based graph database with RediSearch
 *
 * Uses a public bridge network with database and MCP server containers.
 * This is the main setup script that creates containers, networks, and volumes.
 *
 * Configuration is read from PAI .env (${PAI_DIR}/.env or ~/.claude/.env)
 */

import { createContainerManager, ContainerManager, type DatabaseBackend } from "./lib/container.js";
import { createConfigLoader, type KnowledgeConfig } from "./lib/config.js";
import { cli } from "./lib/cli.js";
import inquirer from "inquirer";
import { dirname, join } from "path";

/**
 * Get the database backend from config
 */
function getDatabaseBackend(config: KnowledgeConfig): DatabaseBackend {
  const dbType = config.DATABASE_TYPE?.toLowerCase() || "neo4j";
  if (dbType === "falkordb") {
    return "falkordb";
  }
  return "neo4j";
}

/**
 * Start FalkorDB backend
 */
async function startFalkorDB(
  containerManager: ContainerManager,
  config: KnowledgeConfig,
  networkName: string
): Promise<boolean> {
  const containerName = ContainerManager.FALKORDB_CONTAINER;
  const volumeName = ContainerManager.VOLUME_NAME;
  const image = ContainerManager.IMAGES.falkordb.database;

  cli.blank();
  cli.header("Starting FalkorDB container...");

  // Check if container exists
  const exists = await containerManager.containerExists(containerName);
  if (exists) {
    cli.warning(`FalkorDB container '${containerName}' already exists.`);

    const { recreate } = await inquirer.prompt([
      {
        type: "confirm",
        name: "recreate",
        message: "Do you want to remove and recreate it?",
        default: false,
      },
    ]);

    if (recreate) {
      cli.info("Stopping and removing existing FalkorDB container...");
      await containerManager.stopAndRemoveContainer(containerName);
    } else {
      return true; // Already exists, continue
    }
  }

  // Run FalkorDB container
  if (!await containerManager.containerExists(containerName)) {
    const args = [
      `--name=${containerName}`,
      "--restart=unless-stopped",
      `--network=${networkName}`,
      "--network-alias=falkordb",  // DNS alias for service discovery
      "-p=3000:3000",  // FalkorDB web UI
      `-v=${volumeName}:/data`,
      `-e=FALKORDB_PASSWORD=${config.FALKORDB_PASSWORD || ""}`,
      image,
    ];

    const result = await containerManager.runContainer(args);
    if (result.success) {
      cli.success("✓ FalkorDB container started");
      cli.dim(`  Container: ${containerName}`);
      cli.dim(`  Volume: ${volumeName}`);
      cli.dim(`  Network: ${networkName}`);
    } else {
      cli.error(`Failed to start FalkorDB: ${result.stderr}`);
      return false;
    }
  }

  // Wait for FalkorDB to be ready
  cli.info("Waiting for FalkorDB to be ready...");
  await new Promise((resolve) => setTimeout(resolve, 5000));

  return true;
}

/**
 * Start Neo4j backend
 */
async function startNeo4j(
  containerManager: ContainerManager,
  config: KnowledgeConfig,
  networkName: string
): Promise<boolean> {
  const containerName = ContainerManager.NEO4J_CONTAINER;
  const volumeData = ContainerManager.NEO4J_VOLUME_DATA;
  const volumeLogs = ContainerManager.NEO4J_VOLUME_LOGS;
  const image = ContainerManager.IMAGES.neo4j.database;

  cli.blank();
  cli.header("Starting Neo4j container...");

  // Check if container exists
  const exists = await containerManager.containerExists(containerName);
  if (exists) {
    cli.warning(`Neo4j container '${containerName}' already exists.`);

    const { recreate } = await inquirer.prompt([
      {
        type: "confirm",
        name: "recreate",
        message: "Do you want to remove and recreate it?",
        default: false,
      },
    ]);

    if (recreate) {
      cli.info("Stopping and removing existing Neo4j container...");
      await containerManager.stopAndRemoveContainer(containerName);
    } else {
      return true; // Already exists, continue
    }
  }

  // Run Neo4j container
  if (!await containerManager.containerExists(containerName)) {
    const neo4jUser = config.NEO4J_USER || "neo4j";
    const neo4jPassword = config.NEO4J_PASSWORD || "madeinozknowledge";

    const args = [
      `--name=${containerName}`,
      "--restart=unless-stopped",
      `--network=${networkName}`,
      "--network-alias=neo4j",  // DNS alias for service discovery
      "-p=7474:7474",  // Neo4j Browser HTTP
      "-p=7687:7687",  // Bolt protocol
      `-v=${volumeData}:/data`,
      `-v=${volumeLogs}:/logs`,
      `-e=NEO4J_AUTH=${neo4jUser}/${neo4jPassword}`,
      "-e=NEO4J_server_memory_heap_initial__size=512m",
      "-e=NEO4J_server_memory_heap_max__size=1G",
      "-e=NEO4J_server_memory_pagecache_size=512m",
      image,
    ];

    const result = await containerManager.runContainer(args);
    if (result.success) {
      cli.success("✓ Neo4j container started");
      cli.dim(`  Container: ${containerName}`);
      cli.dim(`  Volumes: ${volumeData}, ${volumeLogs}`);
      cli.dim(`  Network: ${networkName}`);
    } else {
      cli.error(`Failed to start Neo4j: ${result.stderr}`);
      return false;
    }
  }

  // Wait for Neo4j to be ready (takes longer than FalkorDB)
  cli.info("Waiting for Neo4j to be ready (this may take 30+ seconds)...");
  await new Promise((resolve) => setTimeout(resolve, 15000));

  // Health check
  cli.info("Checking Neo4j health...");
  for (let i = 0; i < 6; i++) {
    try {
      const response = await fetch("http://localhost:7474", {
        signal: AbortSignal.timeout(5000),
      });
      if (response.ok) {
        cli.success("✓ Neo4j is ready");
        break;
      }
    } catch {
      if (i < 5) {
        cli.dim(`  Waiting... (attempt ${i + 1}/6)`);
        await new Promise((resolve) => setTimeout(resolve, 5000));
      } else {
        cli.warning("Neo4j health check timed out - may still be starting");
      }
    }
  }

  return true;
}

/**
 * Start MCP server for the given backend
 */
async function startMCPServer(
  containerManager: ContainerManager,
  config: KnowledgeConfig,
  configLoader: ReturnType<typeof createConfigLoader>,
  backend: DatabaseBackend,
  networkName: string
): Promise<boolean> {
  const containerName = ContainerManager.MCP_CONTAINER;
  const image = ContainerManager.IMAGES[backend].mcp;

  cli.blank();
  cli.header(`Starting Graphiti MCP Server (${backend} backend)...`);

  // Check if container exists
  const exists = await containerManager.containerExists(containerName);
  if (exists) {
    cli.warning(`MCP container '${containerName}' already exists.`);

    const { recreate } = await inquirer.prompt([
      {
        type: "confirm",
        name: "recreate",
        message: "Do you want to remove and recreate it?",
        default: false,
      },
    ]);

    if (recreate) {
      cli.info("Stopping and removing existing MCP container...");
      await containerManager.stopAndRemoveContainer(containerName);
    } else {
      cli.info("Using existing MCP container...");
      return true;
    }
  }

  // Build container environment variables
  const containerEnv = configLoader.getContainerEnv(config);

  // Build args based on backend
  const args: string[] = [
    `--name=${containerName}`,
    "--restart=unless-stopped",
    `--network=${networkName}`,
    "-p=8000:8000",  // MCP HTTP endpoint
    // LLM Configuration
    `-e=OPENAI_API_KEY=${containerEnv.OPENAI_API_KEY || ""}`,
    `-e=OPENAI_BASE_URL=${containerEnv.OPENAI_BASE_URL || ""}`,
    `-e=OLLAMA_BASE_URL=${containerEnv.OLLAMA_BASE_URL || ""}`,
    `-e=ANTHROPIC_API_KEY=${containerEnv.ANTHROPIC_API_KEY || ""}`,
    `-e=GOOGLE_API_KEY=${containerEnv.GOOGLE_API_KEY || ""}`,
    `-e=GROQ_API_KEY=${containerEnv.GROQ_API_KEY || ""}`,
    `-e=VOYAGE_API_KEY=${containerEnv.VOYAGE_API_KEY || ""}`,
    // Model Configuration
    `-e=MODEL_NAME=${containerEnv.MODEL_NAME}`,
    `-e=LLM_PROVIDER=${containerEnv.LLM_PROVIDER}`,
    `-e=EMBEDDER_PROVIDER=${containerEnv.EMBEDDER_PROVIDER}`,
    `-e=EMBEDDER_MODEL=${containerEnv.EMBEDDER_MODEL || ""}`,
    `-e=EMBEDDER_DIMENSIONS=${containerEnv.EMBEDDER_DIMENSIONS || ""}`,
    // App Configuration
    `-e=SEMAPHORE_LIMIT=${containerEnv.SEMAPHORE_LIMIT}`,
    `-e=GRAPHITI_TELEMETRY_ENABLED=${containerEnv.GRAPHITI_TELEMETRY_ENABLED}`,
    `-e=GROUP_ID=${containerEnv.GROUP_ID}`,
    `-e=GRAPHITI_GROUP_ID=${containerEnv.GROUP_ID}`,
  ];

  // Add backend-specific configuration
  if (backend === "falkordb") {
    args.push(
      `-e=DATABASE_TYPE=falkordb`,
      `-e=FALKORDB_HOST=${ContainerManager.FALKORDB_CONTAINER}`,
      `-e=FALKORDB_PORT=6379`,
      `-e=FALKORDB_PASSWORD=${containerEnv.FALKORDB_PASSWORD || ""}`,
    );
  } else {
    // Neo4j backend
    const neo4jUser = config.NEO4J_USER || "neo4j";
    const neo4jPassword = config.NEO4J_PASSWORD || "madeinozknowledge";

    args.push(
      `-e=DATABASE_TYPE=neo4j`,
      `-e=NEO4J_URI=bolt://${ContainerManager.NEO4J_CONTAINER}:7687`,
      `-e=NEO4J_USER=${neo4jUser}`,
      `-e=NEO4J_PASSWORD=${neo4jPassword}`,
      `-e=NEO4J_DATABASE=${config.NEO4J_DATABASE || "neo4j"}`,
    );

    // Note: Config files and patches are baked into the custom madeinoz-knowledge-system:fixed image
    // The entrypoint.sh selects the correct config based on DATABASE_TYPE environment variable
  }

  // Add the image
  args.push(image);

  // Run MCP server
  if (!await containerManager.containerExists(containerName)) {
    const result = await containerManager.runContainer(args);
    if (result.success) {
      cli.success("✓ MCP Server container started");
      cli.dim(`  Container: ${containerName}`);
      cli.dim(`  Image: ${image}`);
      cli.dim(`  Network: ${networkName}`);
    } else {
      cli.error(`Failed to start MCP server: ${result.stderr}`);
      return false;
    }
  }

  return true;
}

/**
 * Main run function
 */
async function main() {
  cli.header("Madeinoz Knowledge System - Setup & Run");
  cli.blank();
  cli.info("This script will set up and start the Madeinoz Knowledge System.");
  cli.blank();
  cli.info("Prerequisites:");
  cli.dim("  - Podman or Docker (container runtime)");
  cli.dim("  - OpenAI API key or compatible LLM provider");
  cli.blank();

  // Create config loader
  const configLoader = createConfigLoader();

  // Check if PAI .env file exists
  if (!configLoader.envExists()) {
    cli.error(`Error: PAI .env file not found!`);
    cli.blank();
    cli.warning("Expected location: " + configLoader.getEnvFile());
    cli.blank();
    cli.info("Run the installer to create the configuration:");
    cli.dim(`  bun run src/server/install.ts`);
    cli.blank();
    cli.info("Or manually create the .env file:");
    cli.dim(`  nano ${configLoader.getEnvFile()}`);
    process.exit(1);
  }

  // Load configuration
  cli.blank();
  cli.info("Loading configuration...");
  const config = await configLoader.load();

  // Determine database backend
  const backend = getDatabaseBackend(config);
  cli.success(`✓ Database backend: ${backend.toUpperCase()}`);

  // Check if MADEINOZ_KNOWLEDGE_OPENAI_API_KEY is set
  let openaiKey = config.OPENAI_API_KEY;
  if (!openaiKey && config.PAI_PREFIXES?.MADEINOZ_KNOWLEDGE_OPENAI_API_KEY) {
    openaiKey = config.PAI_PREFIXES.MADEINOZ_KNOWLEDGE_OPENAI_API_KEY;
    cli.success("✓ Using dedicated Madeinoz Knowledge System API key");
  } else if (!openaiKey) {
    cli.warning("Warning: MADEINOZ_KNOWLEDGE_OPENAI_API_KEY is not set in .env");
    cli.warning("The server may not work properly without an API key.");
  }

  // Create container manager
  const containerManager = createContainerManager();

  // Check if runtime is available
  if (!containerManager.isRuntimeAvailable()) {
    cli.error("Error: No container runtime found!");
    cli.blank();
    cli.info("Please install Podman or Docker:");
    cli.blank();
    cli.dim("  Podman: brew install podman (macOS)");
    cli.dim("  Docker: https://docs.docker.com/get-docker/");
    process.exit(1);
  }

  cli.success(`✓ Container runtime: ${containerManager.getRuntimeCommand()}`);
  cli.blank();

  // Network name (same for both backends)
  const NETWORK_NAME = ContainerManager.NETWORK_NAME;

  // Create network if it doesn't exist
  const networkExists = await containerManager.networkExists(NETWORK_NAME);
  if (!networkExists) {
    cli.info(`Creating public network: ${NETWORK_NAME}`);
    const result = await containerManager.createNetwork(NETWORK_NAME);
    if (result.success) {
      cli.success("✓ Network created");
    } else {
      cli.error(`Failed to create network: ${result.stderr}`);
      process.exit(1);
    }
  } else {
    cli.success(`✓ Network exists: ${NETWORK_NAME}`);
  }

  // Start database backend
  let dbStarted: boolean;
  if (backend === "neo4j") {
    dbStarted = await startNeo4j(containerManager, config, NETWORK_NAME);
  } else {
    dbStarted = await startFalkorDB(containerManager, config, NETWORK_NAME);
  }

  if (!dbStarted) {
    cli.error("Failed to start database container");
    process.exit(1);
  }

  // Start MCP server
  const mcpStarted = await startMCPServer(
    containerManager,
    config,
    configLoader,
    backend,
    NETWORK_NAME
  );

  if (!mcpStarted) {
    cli.error("Failed to start MCP server");
    process.exit(1);
  }

  // Print success message
  cli.blank();
  cli.success("═══════════════════════════════════════");
  cli.success("Madeinoz Knowledge System is running!");
  cli.success("═══════════════════════════════════════");
  cli.blank();

  // Network topology based on backend
  cli.info("Network Topology:");
  if (backend === "neo4j") {
    cli.dim(`  Neo4j:        ${ContainerManager.NEO4J_CONTAINER}`);
  } else {
    cli.dim(`  FalkorDB:     ${ContainerManager.FALKORDB_CONTAINER}`);
  }
  cli.dim(`  MCP Server:   ${ContainerManager.MCP_CONTAINER}`);
  cli.dim(`  Network:      ${NETWORK_NAME} (public bridge)`);
  cli.blank();

  // Access points based on backend
  cli.info("Access points:");
  cli.url("MCP Server", "http://localhost:8000/mcp/");
  cli.url("Health Check", "http://localhost:8000/health");
  if (backend === "neo4j") {
    cli.url("Neo4j Browser", "http://localhost:7474");
    cli.dim("  Bolt URI: bolt://localhost:7687");
  } else {
    cli.url("FalkorDB UI", "http://localhost:3000");
  }
  cli.blank();

  cli.info("Management commands:");
  cli.dim("  View logs:     bun run src/server/logs.ts");
  cli.dim("  Stop system:   bun run src/server/stop.ts");
  cli.dim("  Start system:  bun run src/server/start.ts");
  cli.dim("  Check status:  bun run src/server/status.ts");
  cli.blank();
}

// Run main function
main().catch((error) => {
  cli.error("Unexpected error:");
  console.error(error);
  process.exit(1);
});
