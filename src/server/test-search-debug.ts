#!/usr/bin/env bun
/**
 * Debug search_nodes and search_memory_facts
 * Data is confirmed in Neo4j - need to understand why searches fail
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

async function callTool(name: string, args: any): Promise<{ success: boolean; data: any; duration: number; raw: string }> {
  const start = Date.now();
  const { result, error, raw } = await mcpRequest("tools/call", { name, arguments: args });
  const duration = Date.now() - start;

  if (error) {
    return { success: false, data: error, duration, raw };
  }

  // Parse tool result content
  let data: any = result;
  try {
    if (result?.content?.[0]?.text) {
      data = JSON.parse(result.content[0].text);
    }
  } catch {}

  return { success: true, data, duration, raw };
}

async function main() {
  console.log("═".repeat(60));
  console.log("🔍 Search Debug Test - Data confirmed in Neo4j");
  console.log("═".repeat(60));

  // Initialize session
  console.log("\n📋 Initializing MCP session...");
  const initRes = await mcpRequest("initialize", {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: { name: "search-debug", version: "1.0" }
  });
  console.log(`   Session: ${sessionId}`);

  await mcpRequest("notifications/initialized", {});

  // Test 1: Search for exact entity names that exist
  console.log("\n" + "─".repeat(60));
  console.log("Test 1: Search exact entity names");
  console.log("─".repeat(60));

  const exactQueries = ["TypeScript", "Acme Corp", "Sarah", "Neo4j"];
  for (const q of exactQueries) {
    const res = await callTool("search_nodes", {
      query: q,
      group_ids: ["mcp-test"],
      max_nodes: 10
    });

    const nodes = res.data?.nodes || [];
    console.log(`\n"${q}" → ${nodes.length} nodes (${res.duration}ms)`);

    if (nodes.length > 0) {
      nodes.slice(0, 3).forEach((n: any) => console.log(`   ✅ ${n.name} (${n.entity_type})`));
    } else {
      console.log(`   ⚠️  No results. Raw response sample:`);
      console.log(`   ${res.raw.slice(0, 200)}`);
    }

    await Bun.sleep(300);
  }

  // Test 2: Search without group_id filter
  console.log("\n" + "─".repeat(60));
  console.log("Test 2: Search without group_id filter");
  console.log("─".repeat(60));

  const res2 = await callTool("search_nodes", {
    query: "TypeScript",
    max_nodes: 10
  });
  const nodes2 = res2.data?.nodes || [];
  console.log(`\n"TypeScript" (no group filter) → ${nodes2.length} nodes (${res2.duration}ms)`);
  nodes2.slice(0, 3).forEach((n: any) => console.log(`   ✅ ${n.name}`));

  // Test 3: Search facts
  console.log("\n" + "─".repeat(60));
  console.log("Test 3: Search facts");
  console.log("─".repeat(60));

  const factQueries = ["partnership", "technology", "framework"];
  for (const q of factQueries) {
    const res = await callTool("search_memory_facts", {
      query: q,
      group_ids: ["mcp-test"],
      max_facts: 10
    });

    const facts = res.data?.facts || [];
    console.log(`\n"${q}" → ${facts.length} facts (${res.duration}ms)`);

    if (facts.length > 0) {
      facts.slice(0, 2).forEach((f: any) => console.log(`   ✅ ${f.fact?.slice(0, 80)}...`));
    } else {
      console.log(`   ⚠️  No results`);
    }

    await Bun.sleep(300);
  }

  // Test 4: Get episodes to verify data
  console.log("\n" + "─".repeat(60));
  console.log("Test 4: Get episodes via MCP");
  console.log("─".repeat(60));

  const epRes = await callTool("get_episodes", {
    group_ids: ["mcp-test"],
    max_episodes: 10
  });

  const episodes = epRes.data?.episodes || [];
  console.log(`\nEpisodes in mcp-test: ${episodes.length}`);
  episodes.forEach((ep: any) => console.log(`   📄 ${ep.name || ep.uuid}`));

  // Summary
  console.log("\n" + "═".repeat(60));
  console.log("📊 DEBUG SUMMARY");
  console.log("═".repeat(60));
  console.log(`
Data exists in Neo4j (verified via cypher-shell):
- Entities: TypeScript, Bun, Sarah, Hono, John Smith, Acme Corp, Alice Chen
- Episodes: Tech Stack, Partnership, PAI System
- Group: mcp-test

If searches return 0 results, possible causes:
1. Embedding dimension mismatch between storage and query
2. Vector index not created or not matching
3. Group ID filter issue in search query
  `);
}

main().catch(console.error);
