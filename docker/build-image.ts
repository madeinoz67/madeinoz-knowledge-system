#!/usr/bin/env bun
/**
 * Build Custom Docker Image for Madeinoz Knowledge System
 *
 * This script builds a custom Docker image with:
 * - Ollama embedder support (factories.py patch)
 * - Search-all-groups feature (graphiti_mcp_server.py patch)
 * - Neo4j configuration (config-neo4j.yaml)
 * - MADEINOZ_KNOWLEDGE_* prefix mapping (entrypoint.sh)
 *
 * The custom image includes entrypoint.sh which maps prefixed environment
 * variables to unprefixed container variables for PAI pack isolation.
 *
 * Usage:
 *   bun run build-image.ts
 */

import { cli } from "../src/skills/lib/cli.js";

cli.blank();
cli.header("Building Custom Docker Image");
cli.blank();

cli.info("This will build a custom Docker image with patches baked in.");
cli.blank();
cli.info("Prerequisites:");
cli.info("  - Docker or Podman installed");
cli.info("  - Access to zepai/knowledge-graph-mcp:standalone");
cli.blank();

cli.dim("Building image...");
// Build from project root with Dockerfile in docker/
const projectRoot = new URL("..", import.meta.url).pathname;
const buildResult = Bun.spawn(["docker", "build", "-f", "docker/Dockerfile", "-t", "madeinoz-knowledge-system:latest", "."], {
  cwd: projectRoot,
  stdout: "inherit",
  stderr: "inherit",
});

const exitCode = await buildResult.exited;

if (exitCode === 0) {
  cli.blank();
  cli.success("✓ Docker image built successfully!");
  cli.blank();
  cli.info("Image name: madeinoz-knowledge-system:latest");
  cli.blank();
  cli.info("To run:");
  cli.dim("  docker compose -f docker-compose.custom.yml up -d");
  cli.blank();
  cli.info("Your .env file (in project root) should contain:");
  cli.blank();
  cli.dim("  # LLM Configuration (PACK-ISOLATED)");
  cli.dim("  MADEINOZ_KNOWLEDGE_OPENAI_API_KEY=sk-...");
  cli.dim("  MADEINOZ_KNOWLEDGE_MODEL_NAME=openai/gpt-4o-mini");
  cli.dim("  MADEINOZ_KNOWLEDGE_OPENAI_BASE_URL=https://openrouter.ai/api/v1");
  cli.blank();
  cli.dim("  # Embedder Configuration (PACK-ISOLATED)");
  cli.dim("  MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER=ollama");
  cli.dim("  MADEINOZ_KNOWLEDGE_EMBEDDER_MODEL=mxbai-embed-large");
  cli.dim("  MADEINOZ_KNOWLEDGE_EMBEDDER_DIMENSIONS=1024");
  cli.dim("  MADEINOZ_KNOWLEDGE_EMBEDDER_PROVIDER_URL=http://YOUR_IP:11434");
  cli.blank();
  cli.dim("  # Neo4j Configuration (UNPREFIXED, shared infrastructure)");
  cli.dim("  NEO4J_URI=bolt://neo4j:7687");
  cli.dim("  NEO4J_USER=neo4j");
  cli.dim("  NEO4J_PASSWORD=madeinozknowledge");
  cli.blank();
  cli.info("See .env.example for complete configuration reference.");
  cli.blank();
} else {
  cli.error("✗ Docker build failed");
  process.exit(1);
}
