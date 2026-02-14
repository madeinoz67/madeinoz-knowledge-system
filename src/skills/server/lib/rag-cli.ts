#!/usr/bin/env bun
/**
 * Qdrant CLI Wrapper for LKAP (Feature 023 - T045)
 * Local Knowledge Augmentation Platform
 *
 * Command-line interface for Qdrant vector database operations:
 * - Search documents with semantic queries
 * - Retrieve specific chunks by ID
 * - Ingest documents into the vector database
 * - List ingested documents
 * - Check system health
 * - Search and list extracted images (Feature 024)
 *
 * Usage:
 *   bun run rag-cli.ts search "GPIO configuration"
 *   bun run rag-cli.ts get-chunk <chunk-id>
 *   bun run rag-cli.ts ingest <file-path>
 *   bun run rag-cli.ts ingest --all
 *   bun run rag-cli.ts list
 *   bun run rag-cli.ts health
 *   bun run rag-cli.ts images search "pinout diagram"
 *   bun run rag-cli.ts images list
 */

// Load environment variables from .env.dev using Bun's native .env support
// Bun automatically loads .env, but we need .env.dev for development
import { existsSync } from "fs";
import { resolve } from "path";

const envDevPath = resolve(import.meta.dir, "..", "..", "..", "..", ".env.dev");
if (existsSync(envDevPath)) {
  // Read and parse .env.dev manually
  const envContent = await Bun.file(envDevPath).text();
  for (const line of envContent.split("\n")) {
    const trimmed = line.trim();
    if (trimmed && !trimmed.startsWith("#")) {
      const [key, ...valueParts] = trimmed.split("=");
      if (key && valueParts.length > 0) {
        const value = valueParts.join("=").trim();
        process.env[key] = value;
      }
    }
  }
}

import { search, getChunk, listDocuments, healthCheck, ingest, searchImages, getImage, listImages } from "./qdrant.js";
import type { SearchFilters } from "./types.js";
import type { ImageClassification } from "./qdrant.js";

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
  source: string;
  page?: string;
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

    console.log(colorize(`[${index + 1}] ${result.source}`, "cyan"));
    console.log(`  ${colorize("Confidence:", "dim")} ${colorize(result.confidence.toFixed(3), confidenceColor)}`);
    console.log(`  ${colorize("Section:", "dim")} ${result.page || "N/A"}`);
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
  id: string;
  payload: {
    chunk_id: string;
    text: string;
    source?: string;
    doc_id?: string;
    position?: number;
    token_count?: number;
    page_section?: string;
    headings?: string[];
    domain?: string;
    project?: string;
    component?: string;
    type?: string;
  };
} | null): void {
  if (!chunk) {
    console.log(colorize("Chunk not found.", "red"));
    return;
  }

  console.log(colorize("\n=== Chunk Details ===\n", "bright"));
  console.log(`${colorize("Chunk ID:", "dim")} ${chunk.payload.chunk_id}`);
  console.log(`${colorize("Document ID:", "dim")} ${chunk.payload.doc_id || "N/A"}`);
  console.log(`${colorize("Source:", "dim")} ${chunk.payload.source || "N/A"}`);
  console.log(`${colorize("Position:", "dim")} ${chunk.payload.position ?? "N/A"}`);
  console.log(`${colorize("Tokens:", "dim")} ${chunk.payload.token_count ?? "N/A"}`);
  console.log(`${colorize("Section:", "dim")} ${chunk.payload.page_section || "N/A"}`);

  if (chunk.payload.headings && chunk.payload.headings.length > 0) {
    console.log(`${colorize("Headings:", "dim")} ${chunk.payload.headings.join(" > ")}`);
  }

  console.log(`\n${colorize("Text:", "cyan")}`);
  console.log(chunk.payload.text);

  const metadata: Record<string, any> = {};
  if (chunk.payload.domain) metadata.domain = chunk.payload.domain;
  if (chunk.payload.project) metadata.project = chunk.payload.project;
  if (chunk.payload.component) metadata.component = chunk.payload.component;
  if (chunk.payload.type) metadata.type = chunk.payload.type;

  if (Object.keys(metadata).length > 0) {
    console.log(`\n${colorize("Metadata:", "dim")}`);
    console.log(JSON.stringify(metadata, null, 2));
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
          console.log(`${colorize(String(index + 1), "cyan")}. ${colorize(doc.source, "bright")}`);
          console.log(`   ${colorize("Doc ID:", "dim")} ${doc.doc_id}`);
          console.log(`   ${colorize("Chunks:", "dim")} ${doc.count}`);
          console.log("");
        });
        break;
      }

      case "ingest": {
        const ingestAll = options.all === "true";
        const filePath = args[0];

        if (!ingestAll && !filePath) {
          console.error(colorize("Error: File path required (or use --all for batch)", "red"));
          console.log("Usage: bun run rag-cli.ts ingest <file-path>");
          console.log("       bun run rag-cli.ts ingest --all");
          process.exit(1);
        }

        if (ingestAll) {
          console.log(colorize("Ingesting all documents from knowledge/inbox/...", "bright"));
        } else {
          console.log(colorize(`Ingesting: ${filePath}`, "bright"));
        }

        try {
          const result = await ingest(filePath, ingestAll);

          if (Array.isArray(result)) {
            // Batch ingestion
            const successful = result.filter(r => r.success).length;
            const failed = result.filter(r => !r.success).length;

            console.log(colorize(`\nIngestion complete:`, "bright"));
            console.log(`  ${colorize("Successful:", "green")} ${successful}`);
            if (failed > 0) {
              console.log(`  ${colorize("Failed:", "red")} ${failed}`);
            }
            console.log(`\n${colorize("Details:", "dim")}`);
            result.forEach((r, i) => {
              const statusColor = r.success ? "green" : "red";
              console.log(`  ${i + 1}. ${colorize(r.filename, "cyan")} - ${colorize(r.status, statusColor)} (${r.chunk_count} chunks)`);
              if (r.error_message) {
                console.log(`     ${colorize("Error:", "red")} ${r.error_message}`);
              }
            });
          } else {
            // Single file ingestion
            if (result.success) {
              console.log(colorize("\n✓ Ingestion successful", "green"));
              console.log(`  ${colorize("Document ID:", "dim")} ${result.doc_id}`);
              console.log(`  ${colorize("Filename:", "dim")} ${result.filename}`);
              console.log(`  ${colorize("Chunks created:", "dim")} ${result.chunk_count}`);
              console.log(`  ${colorize("Processing time:", "dim")} ${result.processing_time_ms}ms`);
            } else {
              console.error(colorize("\n✗ Ingestion failed", "red"));
              console.error(`  ${colorize("Error:", "dim")} ${result.error_message}`);
              process.exit(1);
            }
          }
        } catch (error) {
          console.error(colorize(`\n✗ Ingestion error`, "red"));
          console.error(colorize(`  ${(error as Error).message}`, "dim"));
          process.exit(1);
        }
        break;
      }

      case "health": {
        console.log(colorize("Checking Qdrant health...", "bright"));

        try {
          const health = await healthCheck();

          if (health.connected) {
            console.log(colorize("✓ Qdrant service is healthy", "green"));
            console.log(`  Collection: ${health.collection_name}`);
            console.log(`  Collection exists: ${health.collection_exists ? "Yes" : "No"}`);
            console.log(`  Vector count: ${health.vector_count}`);
            process.exit(0);
          } else {
            console.error(colorize("✗ Qdrant service is not responding", "red"));
            process.exit(1);
          }
        } catch (error) {
          console.error(colorize(`✗ Cannot connect to Qdrant`, "red"));
          console.error(colorize(`  Error: ${(error as Error).message}`, "dim"));
          process.exit(1);
        }
        break;
      }

      case "images": {
        const subCommand = args[0] || "help";

        switch (subCommand) {
          case "search": {
            if (args.length < 2) {
              console.error(colorize("Error: Search query required", "red"));
              console.log("Usage: bun run rag-cli.ts images search \"<query>\" [--type=<classification>]");
              console.log("\nClassifications: schematic, pinout, waveform, photo, table, graph, flowchart");
              process.exit(1);
            }

            const query = args[1];
            const classification = options.type as ImageClassification | undefined;
            const topK = parseInt(options["top-k"] || options.topK || "10", 10);

            console.log(colorize(`Searching images for: ${query}`, "bright"));
            if (classification) {
              console.log(colorize(`Filter: ${classification}`, "dim"));
            }

            const results = await searchImages(query, classification, topK);

            if (results.length === 0) {
              console.log(colorize("No images found.", "yellow"));
              break;
            }

            console.log(colorize(`\nFound ${results.length} image(s):\n`, "bright"));

            results.forEach((result, index) => {
              const confidenceColor = result.confidence >= 0.85 ? "green" :
                                     result.confidence >= 0.70 ? "yellow" : "red";

              console.log(colorize(`[${index + 1}] ${result.source}`, "cyan"));
              console.log(`  ${colorize("Type:", "dim")} ${colorize(result.classification, "bright")}`);
              console.log(`  ${colorize("Confidence:", "dim")} ${colorize(result.confidence.toFixed(3), confidenceColor)}`);
              console.log(`  ${colorize("Page:", "dim")} ${result.source_page ?? "N/A"}`);
              console.log(`  ${colorize("Image ID:", "dim")} ${result.image_id}`);
              console.log(`  ${colorize("Description:", "dim")} ${result.description.substring(0, 150)}${result.description.length > 150 ? "..." : ""}`);
              console.log("");
            });
            break;
          }

          case "get": {
            if (args.length < 2) {
              console.error(colorize("Error: Image ID required", "red"));
              console.log("Usage: bun run rag-cli.ts images get <image-id>");
              process.exit(1);
            }

            const imageId = args[1];
            console.log(colorize(`Retrieving image: ${imageId}`, "bright"));

            const image = await getImage(imageId);

            if (!image) {
              console.log(colorize("Image not found.", "red"));
              break;
            }

            console.log(colorize("\n=== Image Details ===\n", "bright"));
            console.log(`${colorize("Image ID:", "dim")} ${image.image_id}`);
            console.log(`${colorize("Document ID:", "dim")} ${image.doc_id}`);
            console.log(`${colorize("Source:", "dim")} ${image.source}`);
            console.log(`${colorize("Page:", "dim")} ${image.source_page ?? "N/A"}`);
            console.log(`${colorize("Type:", "dim")} ${image.classification}`);
            console.log(`${colorize("Format:", "dim")} ${image.image_format}`);
            console.log(`\n${colorize("Description:", "cyan")}`);
            console.log(image.description);

            if (image.headings && image.headings.length > 0) {
              console.log(`\n${colorize("Headings:", "dim")} ${image.headings.join(" > ")}`);
            }

            if (image.image_data) {
              const sizeKB = Math.ceil((image.image_data.length * 3) / 4 / 1024); // Base64 to KB
              console.log(`\n${colorize("Image Data:", "dim")} ${sizeKB}KB (base64 encoded)`);
              console.log(colorize("  Use --save flag to save to file", "dim"));
            }
            console.log("");
            break;
          }

          case "list": {
            const docId = options["doc-id"] || options.docId;
            const classification = options.type as ImageClassification | undefined;
            const limit = parseInt(options.limit || "50", 10);

            console.log(colorize(`Listing images (limit: ${limit})`, "bright"));
            if (docId) console.log(colorize(`  Document: ${docId}`, "dim"));
            if (classification) console.log(colorize(`  Type: ${classification}`, "dim"));

            const images = await listImages(docId, classification, limit);

            if (images.length === 0) {
              console.log(colorize("No images found.", "yellow"));
              break;
            }

            console.log(colorize(`\nFound ${images.length} image(s):\n`, "bright"));

            images.forEach((image, index) => {
              console.log(`${colorize(String(index + 1), "cyan")}. ${colorize(image.classification, "bright")} - ${image.source}`);
              console.log(`   ${colorize("Image ID:", "dim")} ${image.image_id}`);
              console.log(`   ${colorize("Page:", "dim")} ${image.source_page ?? "N/A"}`);
              console.log(`   ${colorize("Description:", "dim")} ${image.description.substring(0, 80)}${image.description.length > 80 ? "..." : ""}`);
              console.log("");
            });
            break;
          }

          case "help":
          default:
            console.log(colorize("Image Commands - Multimodal Search (Feature 024)\n", "bright"));
            console.log("Usage: bun run rag-cli.ts images <command> [args] [options]\n");
            console.log("Commands:");
            console.log("  search <query>    Search images by description");
            console.log("  get <image-id>    Get specific image details");
            console.log("  list              List all images\n");
            console.log("Search Options:");
            console.log("  --type=<type>     Filter by classification:");
            console.log("                    schematic, pinout, waveform, photo, table, graph, flowchart");
            console.log("  --top-k=<n>       Maximum results (default: 10)\n");
            console.log("List Options:");
            console.log("  --doc-id=<id>     Filter by document ID");
            console.log("  --type=<type>     Filter by classification");
            console.log("  --limit=<n>       Maximum results (default: 50)\n");
            console.log("Examples:");
            console.log("  bun run rag-cli.ts images search \"GPIO pinout\"");
            console.log("  bun run rag-cli.ts images search \"timing diagram\" --type=waveform");
            console.log("  bun run rag-cli.ts images get abc123-def456");
            console.log("  bun run rag-cli.ts images list --type=schematic");
            console.log("");
            break;
        }
        break;
      }

      case "help":
      default:
        console.log(colorize("Qdrant CLI - Local Knowledge Augmentation Platform\n", "bright"));
        console.log("Usage: bun run rag-cli.ts <command> [args] [options]\n");
        console.log("Commands:");
        console.log("  search <query>       Search documents with semantic query");
        console.log("  get-chunk <id>       Retrieve specific chunk by ID");
        console.log("  ingest <path>        Ingest a document (PDF, markdown, text)");
        console.log("  ingest --all         Ingest all documents in knowledge/inbox/");
        console.log("  list                 List all ingested documents");
        console.log("  images <cmd>         Image search commands (search, get, list)");
        console.log("  health               Check Qdrant service health");
        console.log("  help                 Show this help message\n");
        console.log("Search Options:");
        console.log("  --domain=<type>      Filter by domain (embedded, security, etc.)");
        console.log("  --type=<type>        Filter by document type (pdf, markdown, etc.)");
        console.log("  --component=<name>   Filter by component name");
        console.log("  --project=<name>     Filter by project name");
        console.log("  --version=<ver>      Filter by version");
        console.log("  --top-k=<n>          Maximum results (default: 10, max: 100)\n");
        console.log("Image Commands:");
        console.log("  images search <q>    Search images by description");
        console.log("  images get <id>      Get specific image details");
        console.log("  images list          List all images\n");
        console.log("List Options:");
        console.log("  --limit=<n>          Maximum documents to return (default: 100)\n");
        console.log("Examples:");
        console.log("  bun run rag-cli.ts search \"GPIO configuration\" --domain=embedded");
        console.log("  bun run rag-cli.ts get-chunk abc123-def456");
        console.log("  bun run rag-cli.ts ingest knowledge/inbox/datasheet.pdf");
        console.log("  bun run rag-cli.ts ingest --all");
        console.log("  bun run rag-cli.ts list --limit=50");
        console.log("  bun run rag-cli.ts images search \"pinout diagram\" --type=pinout");
        console.log("  bun run rag-cli.ts images list --type=schematic");
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
