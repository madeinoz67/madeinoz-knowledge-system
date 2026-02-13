#!/usr/bin/env bun
/**
 * RAGFlow CLI Wrapper for LKAP (Feature 022 - T050)
 * Local Knowledge Augmentation Platform
 *
 * Command-line interface for RAGFlow vector database operations:
 * - Search documents with semantic queries
 * - Retrieve specific chunks by ID
 * - List ingested documents
 * - Check system health
 *
 * Usage:
 *   bun run rag-cli.ts search "GPIO configuration"
 *   bun run rag-cli.ts get-chunk <chunk-id>
 *   bun run rag-cli.ts list
 *   bun run rag-cli.ts health
 */

import { search, getChunk, listDocuments } from "./ragflow.js";
import type { SearchFilters } from "./types.js";

// ANSI color codes for terminal output
const colors = {
  reset: "\x1b[0m",
  bright: "\x1b[1m",
  dim: "\x1b[2m",
  green: "\x1b[32m",
  blue: "\x1b[34m",
  yellow: "\x1b[33m",
  red: "\x1b[31m",
  cyan: "\x1b[36m",
};

function colorize(text: string, color: keyof typeof colors): string {
  return `${colors[color]}${text}${colors.reset}`;
}

/**
 * Print formatted search results
 */
function printSearchResults(results: Array<{
  chunk_id: string;
  text: string;
  source_document: string;
  page_section: string;
  confidence: number;
  metadata: any;
}>): void {
  if (results.length === 0) {
    console.log(colorize("No results found.", "yellow"));
    return;
  }

  console.log(colorize(`\nFound ${results.length} result(s):\n`, "bright"));

  results.forEach((result, index) => {
    const confidenceColor = result.confidence >= 0.85 ? "green" :
                           result.confidence >= 0.70 ? "yellow" : "red";

    console.log(colorize(`[${index + 1}] ${result.source_document}`, "cyan"));
    console.log(`  ${colorize("Confidence:", "dim")} ${colorize(result.confidence.toFixed(3), confidenceColor)}`);
    console.log(`  ${colorize("Section:", "dim")} ${result.page_section || "N/A"}`);
    console.log(`  ${colorize("Chunk ID:", "dim")} ${result.chunk_id}`);
    console.log(`  ${colorize("Text:", "dim")} ${result.text.substring(0, 200)}${result.text.length > 200 ? "..." : ""}`);

    if (result.metadata && Object.keys(result.metadata).length > 0) {
      console.log(`  ${colorize("Metadata:", "dim")} ${JSON.stringify(result.metadata, null, 2).split("\n").join("\n    ")}`);
    }
    console.log("");
  });
}

/**
 * Print formatted chunk details
 */
function printChunk(chunk: {
  chunk_id: string;
  text: string;
  document: any;
  position: number;
  token_count: number;
  page_section?: string;
  metadata: any;
}): void {
  console.log(colorize("\n=== Chunk Details ===\n", "bright"));
  console.log(`${colorize("Chunk ID:", "dim")} ${chunk.chunk_id}`);
  console.log(`${colorize("Document:", "dim")} ${chunk.document.filename}`);
  console.log(`${colorize("Position:", "dim")} ${chunk.position}`);
  console.log(`${colorize("Tokens:", "dim")} ${chunk.token_count}`);
  console.log(`${colorize("Section:", "dim")} ${chunk.page_section || "N/A"}`);
  console.log(`\n${colorize("Text:", "cyan")}`);
  console.log(chunk.text);

  if (chunk.metadata && Object.keys(chunk.metadata).length > 0) {
    console.log(`\n${colorize("Metadata:", "dim")}`);
    console.log(JSON.stringify(chunk.metadata, null, 2));
  }
  console.log("");
}

/**
 * Parse command line arguments
 */
function parseArgs(): {
  command: string;
  args: string[];
  options: Record<string, string>;
} {
  const args = process.argv.slice(2);
  const command = args[0] || "help";
  const commandArgs: string[] = [];
  const options: Record<string, string> = {};

  for (let i = 1; i < args.length; i++) {
    const arg = args[i];
    if (arg.startsWith("--")) {
      const [key, value] = arg.substring(2).split("=");
      options[key] = value || "true";
    } else if (arg.startsWith("-")) {
      options[arg.substring(1)] = "true";
    } else {
      commandArgs.push(arg);
    }
  }

  return { command, args: commandArgs, options };
}

/**
 * Main CLI entry point
 */
async function main(): Promise<void> {
  const { command, args, options } = parseArgs();

  try {
    switch (command) {
      case "search": {
        if (args.length === 0) {
          console.error(colorize("Error: Search query required", "red"));
          console.log("Usage: bun run rag-cli.ts search \"<query>\" [--domain=<domain>] [--type=<type>] [--component=<component>] [--top-k=<n>]");
          process.exit(1);
        }

        const query = args[0];
        const filters: SearchFilters = {};

        if (options.domain) filters.domain = options.domain as any;
        if (options.type) filters.type = options.type as any;
        if (options.component) filters.component = options.component;
        if (options.project) filters.project = options.project;
        if (options.version) filters.version = options.version;

        const topK = parseInt(options["top-k"] || options.topK || "10", 10);

        console.log(colorize(`Searching for: ${query}`, "bright"));
        if (Object.keys(filters).length > 0) {
          console.log(colorize(`Filters: ${JSON.stringify(filters)}`, "dim"));
        }

        const results = await search(query, filters, topK);
        printSearchResults(results);
        break;
      }

      case "get-chunk": {
        if (args.length === 0) {
          console.error(colorize("Error: Chunk ID required", "red"));
          console.log("Usage: bun run rag-cli.ts get-chunk <chunk-id>");
          process.exit(1);
        }

        const chunkId = args[0];
        console.log(colorize(`Retrieving chunk: ${chunkId}`, "bright"));

        const chunk = await getChunk(chunkId);
        printChunk(chunk);
        break;
      }

      case "list": {
        const limit = parseInt(options.limit || "100", 10);
        console.log(colorize(`Listing documents (limit: ${limit})`, "bright"));

        const documents = await listDocuments(limit);
        console.log(colorize(`\nFound ${documents.length} document(s):\n`, "bright"));

        documents.forEach((doc, index) => {
          console.log(`${colorize(String(index + 1), "cyan")}. ${colorize(doc.filename, "bright")}`);
          console.log(`   ${colorize("ID:", "dim")} ${doc.doc_id}`);
          console.log(`   ${colorize("Status:", "dim")} ${doc.status}`);
          console.log(`   ${colorize("Uploaded:", "dim")} ${doc.upload_date}`);
          console.log("");
        });
        break;
      }

      case "health": {
        console.log(colorize("Checking RAGFlow health...", "bright"));

        const RAGFLOW_API_URL =
          process.env.MADEINOZ_KNOWLEDGE_RAGFLOW_API_URL || "http://localhost:9380";

        try {
          const response = await fetch(`${RAGFLOW_API_URL}/health`, {
            signal: AbortSignal.timeout(5000),
          });

          if (response.ok) {
            console.log(colorize("✓ RAGFlow service is healthy", "green"));
            process.exit(0);
          } else {
            console.error(colorize(`✗ RAGFlow returned status: ${response.status}`, "red"));
            process.exit(1);
          }
        } catch (error) {
          console.error(colorize(`✗ Cannot connect to RAGFlow at ${RAGFLOW_API_URL}`, "red"));
          console.error(colorize(`  Error: ${(error as Error).message}`, "dim"));
          process.exit(1);
        }
      }

      case "help":
      default:
        console.log(colorize("RAGFlow CLI - Local Knowledge Augmentation Platform\n", "bright"));
        console.log("Usage: bun run rag-cli.ts <command> [args] [options]\n");
        console.log("Commands:");
        console.log("  search <query>       Search documents with semantic query");
        console.log("  get-chunk <id>       Retrieve specific chunk by ID");
        console.log("  list                 List all ingested documents");
        console.log("  health               Check RAGFlow service health");
        console.log("  help                 Show this help message\n");
        console.log("Search Options:");
        console.log("  --domain=<type>      Filter by domain (embedded, security, etc.)");
        console.log("  --type=<type>        Filter by document type (pdf, markdown, etc.)");
        console.log("  --component=<name>   Filter by component name");
        console.log("  --project=<name>     Filter by project name");
        console.log("  --version=<ver>      Filter by version");
        console.log("  --top-k=<n>          Maximum results (default: 10, max: 100)\n");
        console.log("List Options:");
        console.log("  --limit=<n>          Maximum documents to return (default: 100)\n");
        console.log("Examples:");
        console.log("  bun run rag-cli.ts search \"GPIO configuration\" --domain=embedded");
        console.log("  bun run rag-cli.ts get-chunk abc123-def456");
        console.log("  bun run rag-cli.ts list --limit=50");
        console.log("  bun run rag-cli.ts health\n");
        break;
    }
  } catch (error) {
    console.error(colorize(`Error: ${(error as Error).message}`, "red"));
    if ((error as Error).stack) {
      console.error(colorize((error as Error).stack!, "dim"));
    }
    process.exit(1);
  }
}

// Run CLI
if (import.meta.main) {
  main();
}
