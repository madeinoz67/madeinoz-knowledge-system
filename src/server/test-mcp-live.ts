#!/usr/bin/env bun
/**
 * Real-life MCP Knowledge System Test
 * Uses proper SSE/streaming protocol for MCP communication
 */

const MCP_URL = 'http://localhost:8000/mcp';

interface MCPResult {
  success: boolean;
  duration: number;
  data?: any;
  error?: string;
}

// Test data
const TEST_EPISODES = [
  {
    name: 'Tech Stack Decision',
    body: 'The team decided to use TypeScript with Bun runtime for the new API project. Sarah recommended Hono for the HTTP framework.',
    group_id: 'mcp-test',
  },
  {
    name: 'Meeting Notes',
    body: "John Smith from Acme Corp met with CTO Alice Chen to discuss partnership for integrating Acme's payment API.",
    group_id: 'mcp-test',
  },
  {
    name: 'PAI Documentation',
    body: 'The PAI system uses Neo4j as graph database. OpenAI gpt-4o-mini handles entity extraction. Ollama mxbai-embed-large does embeddings.',
    group_id: 'mcp-test',
  },
];

async function callMCP(method: string, params: any): Promise<MCPResult> {
  const start = Date.now();

  try {
    const response = await fetch(MCP_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json, text/event-stream',
      },
      body: JSON.stringify({
        jsonrpc: '2.0',
        id: Date.now(),
        method,
        params,
      }),
    });

    const text = await response.text();
    const duration = Date.now() - start;

    // Parse response - could be JSON or SSE
    let result: any = null;
    let error: string | undefined;

    // Try direct JSON first
    try {
      const json = JSON.parse(text);
      if (json.result) result = json.result;
      if (json.error) error = json.error.message;
    } catch {
      // Try SSE format
      for (const line of text.split('\n')) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.result) result = data.result;
            if (data.error) error = data.error.message;
          } catch {}
        }
      }
    }

    return { success: !error && result !== null, duration, data: result, error };
  } catch (e: any) {
    return { success: false, duration: Date.now() - start, error: e.message };
  }
}

async function main() {
  console.log('═'.repeat(60));
  console.log('🧪 MCP Knowledge System Real-Life Test');
  console.log('═'.repeat(60));

  // Health check
  const health = await fetch('http://localhost:8000/health').then((r) => r.json());
  console.log(`\n📋 Health: ${health.status} | LLM: gpt-4o-mini | DB: neo4j`);

  const results: any[] = [];

  // Test add_memory
  console.log(`\n${'─'.repeat(60)}`);
  console.log('📥 ADD_MEMORY Tests');
  console.log('─'.repeat(60));

  for (const ep of TEST_EPISODES) {
    const res = await callMCP('tools/call', {
      name: 'add_memory',
      arguments: { name: ep.name, episode_body: ep.body, source: 'text', group_id: ep.group_id },
    });

    console.log(`${res.success ? '✅' : '❌'} ${ep.name} (${res.duration}ms)`);
    if (res.error) console.log(`   Error: ${res.error}`);

    results.push({ op: 'add_memory', name: ep.name, ...res });
    await Bun.sleep(3000); // Wait for processing
  }

  // Test search_nodes
  console.log(`\n${'─'.repeat(60)}`);
  console.log('🔍 SEARCH_NODES Tests');
  console.log('─'.repeat(60));

  const nodeQueries = ['TypeScript Bun', 'Acme Corp partnership', 'Neo4j PAI'];
  for (const q of nodeQueries) {
    const res = await callMCP('tools/call', {
      name: 'search_nodes',
      arguments: { query: q, group_ids: ['mcp-test'], max_nodes: 5 },
    });

    let nodes: any[] = [];
    try {
      const content = res.data?.content?.[0]?.text;
      if (content) nodes = JSON.parse(content).nodes || [];
    } catch {}

    console.log(
      `${nodes.length > 0 ? '✅' : '⚠️'} "${q}" → ${nodes.length} nodes (${res.duration}ms)`
    );
    nodes.slice(0, 2).forEach((n) => console.log(`   • ${n.name} (${n.entity_type})`));

    results.push({ op: 'search_nodes', query: q, nodes: nodes.length, ...res });
    await Bun.sleep(500);
  }

  // Test search_memory_facts
  console.log(`\n${'─'.repeat(60)}`);
  console.log('🔗 SEARCH_MEMORY_FACTS Tests');
  console.log('─'.repeat(60));

  const factQueries = ['technology decisions', 'company partnerships', 'database systems'];
  for (const q of factQueries) {
    const res = await callMCP('tools/call', {
      name: 'search_memory_facts',
      arguments: { query: q, group_ids: ['mcp-test'], max_facts: 5 },
    });

    let facts: any[] = [];
    try {
      const content = res.data?.content?.[0]?.text;
      if (content) facts = JSON.parse(content).facts || [];
    } catch {}

    console.log(
      `${facts.length > 0 ? '✅' : '⚠️'} "${q}" → ${facts.length} facts (${res.duration}ms)`
    );
    facts.slice(0, 2).forEach((f) => console.log(`   • ${f.fact?.slice(0, 70)}...`));

    results.push({ op: 'search_memory_facts', query: q, facts: facts.length, ...res });
    await Bun.sleep(500);
  }

  // Summary
  console.log(`\n${'═'.repeat(60)}`);
  console.log('📊 SUMMARY');
  console.log('═'.repeat(60));

  const ops = ['add_memory', 'search_nodes', 'search_memory_facts'];
  for (const op of ops) {
    const opResults = results.filter((r) => r.op === op);
    const success = opResults.filter((r) => r.success).length;
    const avgMs = Math.round(opResults.reduce((a, r) => a + r.duration, 0) / opResults.length);
    console.log(`${op.padEnd(20)} ${success}/${opResults.length} passed | avg ${avgMs}ms`);
  }

  await Bun.write(
    'mcp-live-results.json',
    JSON.stringify({ results, timestamp: new Date().toISOString() }, null, 2)
  );
  console.log('\n📁 Saved to mcp-live-results.json');
}

main();
