#!/usr/bin/env bun
/**
 * Real-life MCP Knowledge System Test
 * Tests the actual add_memory, search_nodes, and search_memory_facts operations
 * by calling the MCP server directly via HTTP/SSE protocol
 */

// Test data - realistic knowledge scenarios
const TEST_EPISODES = [
  {
    name: 'Tech Stack Decision',
    body: 'The team decided to use TypeScript with Bun runtime for the new API project. Sarah recommended Hono for the HTTP framework due to its performance and edge compatibility.',
    source: 'text',
    group_id: 'mcp-test',
  },
  {
    name: 'Meeting Notes',
    body: "John Smith from Acme Corp met with our CTO Alice Chen to discuss the Q1 roadmap. They agreed on a partnership to integrate Acme's payment API into our platform.",
    source: 'text',
    group_id: 'mcp-test',
  },
  {
    name: 'Technical Documentation',
    body: "The PAI system uses Neo4j as the graph database backend. OpenAI's gpt-4o-mini is configured for entity extraction, while mxbai-embed-large running on Ollama handles embeddings.",
    source: 'text',
    group_id: 'mcp-test',
  },
];

const SEARCH_QUERIES = [
  { query: 'What technology stack is being used?', expected: ['TypeScript', 'Bun', 'Hono'] },
  { query: 'Who is working with Acme Corp?', expected: ['John Smith', 'Alice Chen', 'Acme Corp'] },
  { query: 'What database does PAI use?', expected: ['Neo4j', 'PAI'] },
];

async function testDirectAPI() {
  console.log('═'.repeat(60));
  console.log('🧪 Real-Life MCP Knowledge System Test');
  console.log('═'.repeat(60));

  // Test 1: Health check
  console.log('\n📋 Test 1: Health Check');
  const health = await fetch('http://localhost:8000/health').then((r) => r.json());
  console.log(`   Status: ${health.status}`);
  console.log(`   Patch: ${health.patch || 'none'}`);

  // For actual MCP testing, we'll use the MCP protocol via curl or a proper client
  console.log('\n📋 Testing via MCP protocol requires session management...');
  console.log('   Using direct curl tests instead:\n');
}

async function runCurlTests() {
  const results: any[] = [];

  // Test add_memory
  console.log('═'.repeat(60));
  console.log('📥 TEST: add_memory operations');
  console.log('═'.repeat(60));

  for (const episode of TEST_EPISODES) {
    const start = Date.now();
    const proc = Bun.spawn([
      'curl',
      '-sf',
      '-X',
      'POST',
      'http://localhost:8000/mcp',
      '-H',
      'Content-Type: application/json',
      '-H',
      'Accept: text/event-stream',
      '-d',
      JSON.stringify({
        jsonrpc: '2.0',
        id: Date.now(),
        method: 'tools/call',
        params: {
          name: 'add_memory',
          arguments: {
            name: episode.name,
            episode_body: episode.body,
            source: episode.source,
            group_id: episode.group_id,
          },
        },
      }),
    ]);

    const output = await new Response(proc.stdout).text();
    const duration = Date.now() - start;

    const success = output.includes('result') && !output.includes('error');
    console.log(`\n   ${success ? '✅' : '❌'} "${episode.name}" (${duration}ms)`);
    if (!success) console.log(`      Response: ${output.slice(0, 200)}`);

    results.push({
      operation: 'add_memory',
      name: episode.name,
      success,
      duration,
    });

    await new Promise((r) => setTimeout(r, 2000)); // Wait for processing
  }

  // Test search_nodes
  console.log(`\n${'═'.repeat(60)}`);
  console.log('🔍 TEST: search_nodes operations');
  console.log('═'.repeat(60));

  for (const search of SEARCH_QUERIES) {
    const start = Date.now();
    const proc = Bun.spawn([
      'curl',
      '-sf',
      '-X',
      'POST',
      'http://localhost:8000/mcp',
      '-H',
      'Content-Type: application/json',
      '-H',
      'Accept: text/event-stream',
      '-d',
      JSON.stringify({
        jsonrpc: '2.0',
        id: Date.now(),
        method: 'tools/call',
        params: {
          name: 'search_nodes',
          arguments: {
            query: search.query,
            group_ids: ['mcp-test'],
            max_nodes: 10,
          },
        },
      }),
    ]);

    const output = await new Response(proc.stdout).text();
    const duration = Date.now() - start;

    // Check if any expected entities were found
    const foundExpected = search.expected.some((e) =>
      output.toLowerCase().includes(e.toLowerCase())
    );
    console.log(`\n   ${foundExpected ? '✅' : '⚠️'} "${search.query}" (${duration}ms)`);

    // Parse and show found nodes
    try {
      const lines = output.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));
          if (data.result?.content?.[0]?.text) {
            const nodes = JSON.parse(data.result.content[0].text);
            if (nodes.nodes?.length > 0) {
              console.log(`      Found ${nodes.nodes.length} nodes:`);
              nodes.nodes.slice(0, 3).forEach((n: any) => {
                console.log(`        - ${n.name} (${n.entity_type})`);
              });
            }
          }
        }
      }
    } catch (_e) {
      // Output parsing failed
    }

    results.push({
      operation: 'search_nodes',
      query: search.query,
      success: foundExpected,
      duration,
    });

    await new Promise((r) => setTimeout(r, 500));
  }

  // Test search_memory_facts
  console.log(`\n${'═'.repeat(60)}`);
  console.log('🔗 TEST: search_memory_facts operations');
  console.log('═'.repeat(60));

  const factQueries = [
    'partnership between companies',
    'technology decisions',
    'database configuration',
  ];

  for (const query of factQueries) {
    const start = Date.now();
    const proc = Bun.spawn([
      'curl',
      '-sf',
      '-X',
      'POST',
      'http://localhost:8000/mcp',
      '-H',
      'Content-Type: application/json',
      '-H',
      'Accept: text/event-stream',
      '-d',
      JSON.stringify({
        jsonrpc: '2.0',
        id: Date.now(),
        method: 'tools/call',
        params: {
          name: 'search_memory_facts',
          arguments: {
            query: query,
            group_ids: ['mcp-test'],
            max_facts: 5,
          },
        },
      }),
    ]);

    const output = await new Response(proc.stdout).text();
    const duration = Date.now() - start;

    const hasFacts = output.includes('facts') && !output.includes('"facts":[]');
    console.log(`\n   ${hasFacts ? '✅' : '⚠️'} "${query}" (${duration}ms)`);

    // Parse and show facts
    try {
      const lines = output.split('\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));
          if (data.result?.content?.[0]?.text) {
            const facts = JSON.parse(data.result.content[0].text);
            if (facts.facts?.length > 0) {
              console.log(`      Found ${facts.facts.length} facts:`);
              facts.facts.slice(0, 3).forEach((f: any) => {
                console.log(`        - ${f.fact?.slice(0, 80)}...`);
              });
            }
          }
        }
      }
    } catch (_e) {
      // Output parsing failed
    }

    results.push({
      operation: 'search_memory_facts',
      query: query,
      success: hasFacts,
      duration,
    });

    await new Promise((r) => setTimeout(r, 500));
  }

  // Summary
  console.log(`\n${'═'.repeat(60)}`);
  console.log('📊 RESULTS SUMMARY');
  console.log('═'.repeat(60));

  const byOperation = results.reduce(
    (acc, r) => {
      if (!acc[r.operation]) acc[r.operation] = { success: 0, total: 0, totalMs: 0 };
      acc[r.operation].total++;
      if (r.success) acc[r.operation].success++;
      acc[r.operation].totalMs += r.duration;
      return acc;
    },
    {} as Record<string, { success: number; total: number; totalMs: number }>
  );

  console.log('\n| Operation          | Success Rate | Avg Duration |');
  console.log('|--------------------|--------------|--------------|');
  for (const [op, stats] of Object.entries(byOperation)) {
    const rate = ((stats.success / stats.total) * 100).toFixed(0);
    const avgMs = Math.round(stats.totalMs / stats.total);
    console.log(`| ${op.padEnd(18)} | ${rate.padStart(10)}% | ${(`${avgMs}ms`).padStart(12)} |`);
  }

  // Save results
  await Bun.write(
    'mcp-test-results.json',
    JSON.stringify(
      {
        results,
        summary: byOperation,
        timestamp: new Date().toISOString(),
        config: {
          llm: 'gpt-4o-mini',
          embedder: 'openai',
          database: 'neo4j',
        },
      },
      null,
      2
    )
  );

  console.log('\n📁 Results saved to mcp-test-results.json');
}

async function main() {
  try {
    await testDirectAPI();
    await runCurlTests();
  } catch (err: any) {
    console.error('Test failed:', err.message);
    process.exit(1);
  }
}

main();
