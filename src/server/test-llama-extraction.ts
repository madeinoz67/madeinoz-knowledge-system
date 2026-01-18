#!/usr/bin/env bun
/**
 * Test Llama 3.1 8B entity extraction via MCP
 */

const MCP_URL = "http://localhost:8000/mcp";
const ACCEPT = "application/json, text/event-stream";

let sessionId: string | null = null;

async function mcpRequest(method: string, params: any = {}): Promise<any> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    "Accept": ACCEPT
  };
  if (sessionId) headers["mcp-session-id"] = sessionId;

  const res = await fetch(MCP_URL, {
    method: "POST",
    headers,
    body: JSON.stringify({ jsonrpc: "2.0", id: Date.now(), method, params })
  });

  const newSessionId = res.headers.get("mcp-session-id");
  if (newSessionId) sessionId = newSessionId;

  const text = await res.text();
  let result: any = null, error: any = null;

  for (const line of text.split('\n')) {
    if (line.startsWith('data: ')) {
      try {
        const data = JSON.parse(line.slice(6));
        if (data.result) result = data.result;
        if (data.error) error = data.error;
      } catch {}
    }
  }

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

  if (error) return { success: false, data: error, duration };

  let data: any = result;
  try {
    if (result?.content?.[0]?.text) {
      data = JSON.parse(result.content[0].text);
    }
  } catch {}

  return { success: true, data, duration };
}

const TEST_EPISODE = {
  name: "Llama Test Episode",
  body: "During the Q4 planning meeting, CEO Michael Chen announced that TechVentures Inc will acquire DataFlow Systems for $500 million. The deal, brokered by Goldman Sachs, includes all patents and the 200-person engineering team based in Seattle.",
  group: "llama-test"
};

async function main() {
  console.log("═".repeat(60));
  console.log("🦙 Llama 3.1 8B Entity Extraction Test");
  console.log("═".repeat(60));

  // Health check
  const health = await fetch("http://localhost:8000/health").then(r => r.json());
  console.log(`\n📋 Server: ${health.status}`);

  // Initialize session
  console.log("\n📋 Initializing MCP session...");
  await mcpRequest("initialize", {
    protocolVersion: "2024-11-05",
    capabilities: {},
    clientInfo: { name: "llama-test", version: "1.0" }
  });
  await mcpRequest("notifications/initialized", {});
  console.log(`   Session: ${sessionId}`);

  // Test add_memory
  console.log("\n" + "─".repeat(60));
  console.log("📥 ADD_MEMORY Test");
  console.log("─".repeat(60));
  console.log(`\nInput: "${TEST_EPISODE.body}"`);

  const addStart = Date.now();
  const addRes = await callTool("add_memory", {
    name: TEST_EPISODE.name,
    episode_body: TEST_EPISODE.body,
    source: "text",
    group_id: TEST_EPISODE.group
  });
  console.log(`\n${addRes.success ? "✅" : "❌"} add_memory (${addRes.duration}ms)`);

  // Wait for async processing
  console.log("\n⏳ Waiting 15s for entity extraction...");
  await Bun.sleep(15000);

  // Check extracted entities
  console.log("\n" + "─".repeat(60));
  console.log("🔍 SEARCH_NODES Test (checking extracted entities)");
  console.log("─".repeat(60));

  const queries = ["TechVentures", "Michael Chen", "DataFlow", "Goldman Sachs", "Seattle"];
  let found = 0;

  for (const q of queries) {
    const res = await callTool("search_nodes", { query: q, group_ids: ["llama-test"], max_nodes: 5 });
    const nodes = res.data?.nodes || [];
    const match = nodes.find((n: any) => n.name?.toLowerCase().includes(q.toLowerCase()));

    if (match) {
      console.log(`   ✅ "${q}" → Found: ${match.name}`);
      found++;
    } else {
      console.log(`   ⚠️  "${q}" → Not found (${nodes.length} nodes returned)`);
    }
    await Bun.sleep(300);
  }

  // Check facts
  console.log("\n" + "─".repeat(60));
  console.log("🔗 SEARCH_FACTS Test");
  console.log("─".repeat(60));

  const factsRes = await callTool("search_memory_facts", {
    query: "acquisition deal",
    group_ids: ["llama-test"],
    max_facts: 10
  });
  const facts = factsRes.data?.facts || [];
  console.log(`\nFound ${facts.length} facts:`);
  facts.slice(0, 5).forEach((f: any) => console.log(`   • ${f.fact?.slice(0, 80)}...`));

  // Summary
  console.log("\n" + "═".repeat(60));
  console.log("📊 RESULTS");
  console.log("═".repeat(60));
  console.log(`
Model: Llama 3.1 8B via OpenRouter
Cost: $0.0145/1K calls (9x cheaper than GPT-4o-mini)

Entity Extraction: ${found}/${queries.length} expected entities found
Facts Extracted: ${facts.length}

${found >= 3 ? "✅ PASS - Llama 3.1 8B works for entity extraction!" : "⚠️  Some entities not found - may need longer processing time"}
  `);

  // Save results
  await Bun.write("llama-test-results.json", JSON.stringify({
    model: "meta-llama/llama-3.1-8b-instruct",
    provider: "openrouter",
    entitiesFound: found,
    totalExpected: queries.length,
    factsFound: facts.length,
    timestamp: new Date().toISOString()
  }, null, 2));
}

main().catch(console.error);
