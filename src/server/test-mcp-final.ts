#!/usr/bin/env bun
/**
 * MCP Knowledge System Test - Final version with correct protocol
 */

const MCP_URL = "http://localhost:8000/mcp";
const ACCEPT = "application/json, text/event-stream";

let sessionId: string | null = null;

async function mcpRequest(method: string, params: any = {}): Promise<any> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "Accept": ACCEPT
  };

  if (sessionId) {
    headers["mcp-session-id"] = sessionId;
  }

  const res = await fetch(MCP_URL, {
    method: "POST",
    headers,
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: Date.now(),
      method,
      params
    })
  });

  // Capture session ID from response
  const newSessionId = res.headers.get("mcp-session-id");
  if (newSessionId) sessionId = newSessionId;

  const text = await res.text();

  // Parse SSE or JSON response
  let result: any = null;
  let error: any = null;

  for (const line of text.split('\n')) {
    if (line.startsWith('data: ')) {
      try {
        const data = JSON.parse(line.slice(6));
        if (data.result) result = data.result;
        if (data.error) error = data.error;
      } catch {}
    }
  }

  // Fallback to direct JSON
  if (!result && !error) {
    try {
      const json = JSON.parse(text);
      result = json.result;
      error = json.error;
    } catch {}
  }

  return { result, error, raw: text };
}

async function callTool(name: string, args: any): Promise<{ success: boolean; data: any; duration: number }> {
  const start = Date.now();
  const { result, error, raw } = await mcpRequest("tools/call", { name, arguments: args });
  const duration = Date.now() - start;

  if (error) {
    return { success: false, data: error, duration };
  }

  // Parse tool result content
  let data: any = result;
  try {
    if (result?.content?.[0]?.text) {
      data = JSON.parse(result.content[0].text);
    }
  } catch {}

  return { success: true, data, duration };
}

const TEST_EPISODES = [
  { name: "Tech Stack", body: "Team uses TypeScript with Bun. Sarah chose Hono for HTTP framework.", group: "mcp-test" },
  { name: "Partnership", body: "John Smith from Acme Corp met CTO Alice Chen about payment API integration.", group: "mcp-test" },
  { name: "PAI System", body: "PAI uses Neo4j graph database. GPT-4o-mini for extraction. Ollama for embeddings.", group: "mcp-test" }
];

async function main() {
  console.log("═".repeat(60));
  console.log("🧪 MCP Knowledge System - Real Life Tests");
  console.log("═".repeat(60));

  // Health check
  const health = await fetch("http://localhost:8000/health").then(r => r.json());
  console.log(`\n📋 Server: ${health.status} | Patch: ${health.patch}`);

  // Initialize session
  console.log("\n📋 Initializing MCP session...");
  const initRes = await mcpRequest("initialize", {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: { name: "bun-test", version: "1.0" }
  });
  console.log(`   Session: ${sessionId}`);
  if (initRes.error) {
    console.log(`   Error: ${initRes.error.message}`);
  }

  // Send initialized notification
  await mcpRequest("notifications/initialized", {});

  const results: any[] = [];

  // ADD_MEMORY Tests
  console.log("\n" + "─".repeat(60));
  console.log("📥 ADD_MEMORY Tests (using gpt-4o-mini for entity extraction)");
  console.log("─".repeat(60));

  for (const ep of TEST_EPISODES) {
    const res = await callTool("add_memory", {
      name: ep.name,
      episode_body: ep.body,
      source: "text",
      group_id: ep.group
    });

    const icon = res.success ? "✅" : "❌";
    console.log(`${icon} ${ep.name} (${res.duration}ms)`);
    if (!res.success) console.log(`   Error: ${JSON.stringify(res.data).slice(0, 100)}`);

    results.push({ op: "add_memory", name: ep.name, success: res.success, duration: res.duration });
    await Bun.sleep(3000); // Wait for async graph processing
  }

  // SEARCH_NODES Tests
  console.log("\n" + "─".repeat(60));
  console.log("🔍 SEARCH_NODES Tests (semantic search via embeddings)");
  console.log("─".repeat(60));

  const nodeQueries = ["TypeScript Bun framework", "Acme Corp partnership", "PAI graph database"];
  for (const q of nodeQueries) {
    const res = await callTool("search_nodes", { query: q, group_ids: ["mcp-test"], max_nodes: 5 });
    const nodes = res.data?.nodes || [];

    const icon = nodes.length > 0 ? "✅" : "⚠️";
    console.log(`${icon} "${q}" → ${nodes.length} nodes (${res.duration}ms)`);
    nodes.slice(0, 3).forEach((n: any) => console.log(`   • ${n.name} (${n.entity_type})`));

    results.push({ op: "search_nodes", query: q, success: nodes.length > 0, nodes: nodes.length, duration: res.duration });
    await Bun.sleep(500);
  }

  // SEARCH_MEMORY_FACTS Tests
  console.log("\n" + "─".repeat(60));
  console.log("🔗 SEARCH_MEMORY_FACTS Tests (relationship queries)");
  console.log("─".repeat(60));

  const factQueries = ["technology decisions", "company partnerships", "database systems"];
  for (const q of factQueries) {
    const res = await callTool("search_memory_facts", { query: q, group_ids: ["mcp-test"], max_facts: 5 });
    const facts = res.data?.facts || [];

    const icon = facts.length > 0 ? "✅" : "⚠️";
    console.log(`${icon} "${q}" → ${facts.length} facts (${res.duration}ms)`);
    facts.slice(0, 2).forEach((f: any) => console.log(`   • ${f.fact?.slice(0, 70)}...`));

    results.push({ op: "search_memory_facts", query: q, success: facts.length > 0, facts: facts.length, duration: res.duration });
    await Bun.sleep(500);
  }

  // Summary
  console.log("\n" + "═".repeat(60));
  console.log("📊 RESULTS SUMMARY");
  console.log("═".repeat(60));

  const ops = ["add_memory", "search_nodes", "search_memory_facts"];
  console.log("\n| Operation           | Success | Avg Time | Notes          |");
  console.log("|---------------------|---------|----------|----------------|");

  for (const op of ops) {
    const opRes = results.filter(r => r.op === op);
    const success = opRes.filter(r => r.success).length;
    const avgMs = Math.round(opRes.reduce((a, r) => a + r.duration, 0) / opRes.length);
    const notes = op === "add_memory" ? "gpt-4o-mini" : "embeddings";
    console.log(`| ${op.padEnd(19)} | ${success}/${opRes.length}     | ${String(avgMs).padStart(6)}ms | ${notes.padEnd(14)} |`);
  }

  // Save results
  await Bun.write("mcp-final-results.json", JSON.stringify({
    results,
    config: { llm: "gpt-4o-mini", embedder: "openai", database: "neo4j" },
    timestamp: new Date().toISOString()
  }, null, 2));

  console.log("\n📁 Results saved to mcp-final-results.json");
}

main().catch(console.error);
