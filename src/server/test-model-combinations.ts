#!/usr/bin/env bun
/**
 * Test multiple LLM model combinations via MCP
 * Restarts container with different configs for each model
 */

import { $ } from 'bun';

const MCP_URL = 'http://localhost:8000/mcp';
const ACCEPT = 'application/json, text/event-stream';

// Models to test (all 100% pass rate from benchmarks)
const LLM_MODELS = [
  { name: 'Llama 3.1 8B', model: 'meta-llama/llama-3.1-8b-instruct', cost: 0.0145 },
  { name: 'DeepSeek V3', model: 'deepseek/deepseek-chat', cost: 0.0585 },
  { name: 'GPT-4o Mini', model: 'openai/gpt-4o-mini', cost: 0.129 },
  { name: 'Gemini 2.0 Flash', model: 'google/gemini-2.0-flash-001', cost: 0.125 },
];

// Get API keys from environment
const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY;
if (!OPENROUTER_API_KEY) {
  console.error('❌ OPENROUTER_API_KEY not set');
  console.log('\nUsage: OPENROUTER_API_KEY=sk-or-v1-... bun test-model-combinations.ts');
  process.exit(1);
}

const TEST_EPISODES = [
  {
    name: 'Tech Stack',
    body: 'Team uses TypeScript with Bun. Sarah chose Hono for HTTP framework.',
    group: 'model-test',
  },
  {
    name: 'Partnership',
    body: 'John Smith from Acme Corp met CTO Alice Chen about payment API integration.',
    group: 'model-test',
  },
];

let sessionId: string | null = null;

async function mcpRequest(method: string, params: any = {}): Promise<any> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: ACCEPT,
  };
  if (sessionId) headers['mcp-session-id'] = sessionId;

  const res = await fetch(MCP_URL, {
    method: 'POST',
    headers,
    body: JSON.stringify({ jsonrpc: '2.0', id: Date.now(), method, params }),
  });

  const newSessionId = res.headers.get('mcp-session-id');
  if (newSessionId) sessionId = newSessionId;

  const text = await res.text();
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

  if (!result && !error) {
    try {
      const json = JSON.parse(text);
      result = json.result;
      error = json.error;
    } catch {}
  }

  return { result, error, raw: text };
}

async function callTool(
  name: string,
  args: any
): Promise<{ success: boolean; data: any; duration: number }> {
  const start = Date.now();
  const { result, error } = await mcpRequest('tools/call', { name, arguments: args });
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

async function waitForHealth(maxWait = 60000): Promise<boolean> {
  const start = Date.now();
  while (Date.now() - start < maxWait) {
    try {
      const res = await fetch('http://localhost:8000/health');
      if (res.ok) return true;
    } catch {}
    await Bun.sleep(1000);
  }
  return false;
}

async function restartWithModel(modelConfig: (typeof LLM_MODELS)[0]): Promise<boolean> {
  console.log(`\n🔄 Restarting container with ${modelConfig.name}...`);

  // Update .env file for OpenRouter
  const envContent = `# Test configuration for ${modelConfig.name}
OPENAI_API_KEY=${OPENROUTER_API_KEY}
OPENAI_BASE_URL=https://openrouter.ai/api/v1
MODEL_NAME=${modelConfig.model}
LLM_PROVIDER=openai

# Embedder (keep Ollama mxbai)
EMBEDDER_BASE_URL=http://10.0.0.150:11434/v1
EMBEDDER_MODEL=mxbai-embed-large
EMBEDDER_DIMENSIONS=1024
EMBEDDER_PROVIDER=openai

# Neo4j
NEO4J_URI=bolt://neo4j:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=madeinozknowledge
`;

  await Bun.write('../../config/.env.test', envContent);

  // Restart container with test env
  try {
    await $`docker-compose -f docker-compose-neo4j.yml down graphiti-mcp`.quiet();
    await Bun.sleep(2000);

    // Start with test env file
    await $`docker-compose -f docker-compose-neo4j.yml up -d graphiti-mcp`
      .env({
        ...process.env,
        COMPOSE_ENV_FILES: '../../config/.env.test',
      })
      .quiet();

    // Wait for health
    const healthy = await waitForHealth();
    if (!healthy) {
      console.log('   ❌ Container failed to start');
      return false;
    }
    console.log('   ✅ Container ready');
    return true;
  } catch (e: any) {
    console.log(`   ❌ Error: ${e.message}`);
    return false;
  }
}

async function testModel(modelConfig: (typeof LLM_MODELS)[0]): Promise<any> {
  sessionId = null; // Reset session

  // Initialize MCP session
  await mcpRequest('initialize', {
    protocolVersion: '2024-11-05',
    capabilities: {},
    clientInfo: { name: 'model-test', version: '1.0' },
  });
  await mcpRequest('notifications/initialized', {});

  const results = {
    model: modelConfig.name,
    cost: modelConfig.cost,
    add_memory: { success: 0, total: 0, avgMs: 0 },
    search_nodes: { success: 0, total: 0, avgMs: 0, avgResults: 0 },
    search_facts: { success: 0, total: 0, avgMs: 0, avgResults: 0 },
  };

  // Test add_memory
  console.log('   📥 Testing add_memory...');
  let totalAddMs = 0;
  for (const ep of TEST_EPISODES) {
    const res = await callTool('add_memory', {
      name: ep.name,
      episode_body: ep.body,
      source: 'text',
      group_id: ep.group,
    });
    results.add_memory.total++;
    if (res.success) results.add_memory.success++;
    totalAddMs += res.duration;
    await Bun.sleep(3000); // Wait for processing
  }
  results.add_memory.avgMs = Math.round(totalAddMs / TEST_EPISODES.length);

  // Test search_nodes
  console.log('   🔍 Testing search_nodes...');
  const nodeQueries = ['TypeScript', 'Acme Corp'];
  let totalSearchMs = 0;
  let totalNodes = 0;
  for (const q of nodeQueries) {
    const res = await callTool('search_nodes', {
      query: q,
      group_ids: ['model-test'],
      max_nodes: 10,
    });
    results.search_nodes.total++;
    const nodes = res.data?.nodes || [];
    if (nodes.length > 0) results.search_nodes.success++;
    totalSearchMs += res.duration;
    totalNodes += nodes.length;
  }
  results.search_nodes.avgMs = Math.round(totalSearchMs / nodeQueries.length);
  results.search_nodes.avgResults = Math.round(totalNodes / nodeQueries.length);

  // Test search_facts
  console.log('   🔗 Testing search_facts...');
  const factQueries = ['partnership', 'technology'];
  let totalFactMs = 0;
  let totalFacts = 0;
  for (const q of factQueries) {
    const res = await callTool('search_memory_facts', {
      query: q,
      group_ids: ['model-test'],
      max_facts: 10,
    });
    results.search_facts.total++;
    const facts = res.data?.facts || [];
    if (facts.length > 0) results.search_facts.success++;
    totalFactMs += res.duration;
    totalFacts += facts.length;
  }
  results.search_facts.avgMs = Math.round(totalFactMs / factQueries.length);
  results.search_facts.avgResults = Math.round(totalFacts / factQueries.length);

  return results;
}

async function main() {
  console.log('═'.repeat(60));
  console.log('🧪 Model Combination MCP Test');
  console.log('═'.repeat(60));
  console.log(`\nModels to test: ${LLM_MODELS.map((m) => m.name).join(', ')}`);

  const allResults: any[] = [];

  for (const model of LLM_MODELS) {
    console.log(`\n${'─'.repeat(60)}`);
    console.log(`📋 Testing: ${model.name} (${model.model})`);
    console.log(`${'─'.repeat(60)}`);

    const started = await restartWithModel(model);
    if (!started) {
      allResults.push({ model: model.name, error: 'Failed to start' });
      continue;
    }

    const results = await testModel(model);
    allResults.push(results);

    console.log(
      `   ✅ add_memory: ${results.add_memory.success}/${results.add_memory.total} (${results.add_memory.avgMs}ms)`
    );
    console.log(
      `   ✅ search_nodes: ${results.search_nodes.success}/${results.search_nodes.total} (${results.search_nodes.avgMs}ms, avg ${results.search_nodes.avgResults} results)`
    );
    console.log(
      `   ✅ search_facts: ${results.search_facts.success}/${results.search_facts.total} (${results.search_facts.avgMs}ms, avg ${results.search_facts.avgResults} results)`
    );
  }

  // Summary
  console.log(`\n${'═'.repeat(60)}`);
  console.log('📊 RESULTS SUMMARY');
  console.log(`${'═'.repeat(60)}`);
  console.log('\n| Model | Cost/1K | add_memory | search_nodes | search_facts |');
  console.log('|-------|---------|------------|--------------|--------------|');
  for (const r of allResults) {
    if (r.error) {
      console.log(`| ${r.model} | - | ERROR | ERROR | ERROR |`);
    } else {
      console.log(
        `| ${r.model} | $${r.cost.toFixed(4)} | ${r.add_memory.success}/${r.add_memory.total} | ${r.search_nodes.success}/${r.search_nodes.total} | ${r.search_facts.success}/${r.search_facts.total} |`
      );
    }
  }

  // Save results
  await Bun.write(
    'model-combination-results.json',
    JSON.stringify(
      {
        results: allResults,
        timestamp: new Date().toISOString(),
      },
      null,
      2
    )
  );

  console.log('\n📁 Results saved to model-combination-results.json');

  // Restore original config
  console.log('\n🔄 Restoring original configuration...');
  await $`docker-compose -f docker-compose-neo4j.yml down graphiti-mcp`.quiet();
  await $`docker-compose -f docker-compose-neo4j.yml up -d graphiti-mcp`.quiet();
}

main().catch(console.error);
