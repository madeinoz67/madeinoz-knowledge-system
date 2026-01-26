#!/usr/bin/env bun
/**
 * Comprehensive MCP LLM Test
 * Tests ALL benchmark models for real-life entity extraction via Graphiti
 */

import { $ } from 'bun';

const MCP_URL = 'http://localhost:8000/mcp';
const ACCEPT = 'application/json, text/event-stream';
const ENV_FILE = '../../config/.env';

// All models from benchmark with 100% pass rate (sorted by cost)
const LLM_MODELS = [
  { name: 'Llama 3.1 8B', model: 'meta-llama/llama-3.1-8b-instruct', cost: 0.0145 },
  { name: 'Mistral 7B', model: 'mistralai/mistral-7b-instruct', cost: 0.0167 },
  { name: 'DeepSeek V3', model: 'deepseek/deepseek-chat', cost: 0.0585 },
  { name: 'Llama 3.3 70B', model: 'meta-llama/llama-3.3-70b-instruct', cost: 0.114 },
  { name: 'Gemini 2.0 Flash', model: 'google/gemini-2.0-flash-001', cost: 0.125 },
  { name: 'Qwen 2.5 72B', model: 'qwen/qwen-2.5-72b-instruct', cost: 0.126 },
  { name: 'GPT-4o Mini', model: 'openai/gpt-4o-mini', cost: 0.129 },
  { name: 'Claude 3.5 Haiku', model: 'anthropic/claude-3.5-haiku', cost: 0.816 },
  { name: 'GPT-4o', model: 'openai/gpt-4o', cost: 2.155 },
  { name: 'Claude Sonnet 4', model: 'anthropic/claude-sonnet-4', cost: 4.215 },
];

const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY;
if (!OPENROUTER_API_KEY) {
  console.error('❌ OPENROUTER_API_KEY required');
  console.log('\nUsage: OPENROUTER_API_KEY=sk-or-v1-... bun test-all-llms-mcp.ts');
  process.exit(1);
}

// Test episode - complex enough to test extraction quality
const TEST_EPISODE = {
  name: 'LLM Test Episode',
  body: "During the Q4 planning meeting at TechCorp headquarters in Austin, CEO Sarah Martinez announced a strategic partnership with CloudBase Inc. The $50 million deal, facilitated by Morgan Stanley, will integrate CloudBase's AI platform into TechCorp's enterprise suite by March 2026.",
};

// Expected entities to find
const EXPECTED_ENTITIES = ['TechCorp', 'Sarah Martinez', 'CloudBase', 'Morgan Stanley', 'Austin'];

let sessionId: string | null = null;

async function mcpRequest(method: string, params: any = {}): Promise<any> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: ACCEPT,
  };
  if (sessionId) headers['mcp-session-id'] = sessionId;

  try {
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

    return { result, error };
  } catch (e: any) {
    return { error: { message: e.message } };
  }
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
      const res = await fetch('http://localhost:8000/health', {
        signal: AbortSignal.timeout(2000),
      });
      if (res.ok) return true;
    } catch {}
    await Bun.sleep(2000);
  }
  return false;
}

async function updateEnvAndRestart(modelName: string): Promise<boolean> {
  // Read current env
  const envPath = Bun.file(ENV_FILE);
  let envContent = await envPath.text();

  // Update MODEL_NAME lines
  envContent = envContent.replace(
    /MADEINOZ_KNOWLEDGE_MODEL_NAME=.*/g,
    `MADEINOZ_KNOWLEDGE_MODEL_NAME=${modelName}`
  );
  envContent = envContent.replace(/^MODEL_NAME=.*/gm, `MODEL_NAME=${modelName}`);

  // Write updated env
  await Bun.write(ENV_FILE, envContent);

  // Restart container
  try {
    await $`docker-compose -f docker-compose-neo4j.yml up -d --force-recreate graphiti-mcp`.quiet();
    await Bun.sleep(5000); // Initial wait
    return await waitForHealth();
  } catch (e: any) {
    console.log(`   ❌ Restart failed: ${e.message}`);
    return false;
  }
}

async function checkExtractedEntities(groupId: string): Promise<string[]> {
  try {
    const result =
      await $`docker exec madeinoz-knowledge-neo4j cypher-shell -u neo4j -p madeinozknowledge "MATCH (n:Entity {group_id: '${groupId}'}) RETURN n.name as name"`.text();

    // Parse cypher-shell output
    const lines = result.split('\n').slice(1); // Skip header
    const entities: string[] = [];
    for (const line of lines) {
      const name = line.replace(/"/g, '').trim();
      if (name && name !== 'name') entities.push(name);
    }
    return entities;
  } catch {
    return [];
  }
}

async function checkLogs(): Promise<{ success: boolean; error?: string }> {
  try {
    const logs =
      await $`docker-compose -f docker-compose-neo4j.yml logs --tail=30 graphiti-mcp`.text();

    if (logs.includes('Successfully processed episode')) {
      return { success: true };
    }
    if (logs.includes('Failed to process episode')) {
      const match = logs.match(/Failed to process episode.*?: (.+)/);
      return { success: false, error: match?.[1] || 'Unknown error' };
    }
    return { success: false, error: 'Processing not completed' };
  } catch {
    return { success: false, error: 'Could not read logs' };
  }
}

async function testModel(model: (typeof LLM_MODELS)[0], index: number): Promise<any> {
  const groupId = `llm-test-${index}`;
  sessionId = null;

  const result = {
    name: model.name,
    model: model.model,
    cost: model.cost,
    works: false,
    entitiesFound: 0,
    expectedFound: 0,
    error: null as string | null,
    extractionTimeMs: 0,
  };

  // Initialize MCP session
  const initRes = await mcpRequest('initialize', {
    protocolVersion: '2024-11-05',
    capabilities: {},
    clientInfo: { name: 'llm-test', version: '1.0' },
  });

  if (initRes.error) {
    result.error = `Init failed: ${initRes.error.message}`;
    return result;
  }

  await mcpRequest('notifications/initialized', {});

  // Add test episode
  const addStart = Date.now();
  const addRes = await callTool('add_memory', {
    name: TEST_EPISODE.name,
    episode_body: TEST_EPISODE.body,
    source: 'text',
    group_id: groupId,
  });

  if (!addRes.success) {
    result.error = `add_memory failed: ${JSON.stringify(addRes.data).slice(0, 100)}`;
    return result;
  }

  // Wait for async processing (up to 30 seconds)
  console.log('      ⏳ Waiting for extraction...');
  let processed = false;
  for (let i = 0; i < 15; i++) {
    await Bun.sleep(2000);
    const logCheck = await checkLogs();
    if (logCheck.success) {
      processed = true;
      break;
    }
    if (logCheck.error?.includes('validation error')) {
      result.error = logCheck.error;
      return result;
    }
  }

  result.extractionTimeMs = Date.now() - addStart;

  if (!processed) {
    // Check logs for error
    const logCheck = await checkLogs();
    if (!logCheck.success) {
      result.error = logCheck.error || 'Extraction timeout';
      return result;
    }
  }

  // Check extracted entities
  const entities = await checkExtractedEntities(groupId);
  result.entitiesFound = entities.length;

  // Count how many expected entities were found
  for (const expected of EXPECTED_ENTITIES) {
    const found = entities.some(
      (e) =>
        e.toLowerCase().includes(expected.toLowerCase()) ||
        expected.toLowerCase().includes(e.toLowerCase())
    );
    if (found) result.expectedFound++;
  }

  result.works = result.entitiesFound >= 3 && result.expectedFound >= 3;

  return result;
}

async function main() {
  console.log('═'.repeat(70));
  console.log('🧪 Comprehensive MCP LLM Test - All Benchmark Models');
  console.log('═'.repeat(70));
  console.log(`\nTest Episode: "${TEST_EPISODE.body.slice(0, 80)}..."`);
  console.log(`Expected Entities: ${EXPECTED_ENTITIES.join(', ')}`);
  console.log(`\nModels to test: ${LLM_MODELS.length}`);

  const results: any[] = [];

  for (let i = 0; i < LLM_MODELS.length; i++) {
    const model = LLM_MODELS[i];
    console.log(`\n${'─'.repeat(70)}`);
    console.log(`[${i + 1}/${LLM_MODELS.length}] ${model.name} ($${model.cost}/1K)`);
    console.log(`${'─'.repeat(70)}`);

    // Update config and restart
    console.log(`   🔄 Configuring ${model.model}...`);
    const started = await updateEnvAndRestart(model.model);

    if (!started) {
      console.log('   ❌ Container failed to start');
      results.push({
        name: model.name,
        model: model.model,
        cost: model.cost,
        works: false,
        error: 'Container failed',
      });
      continue;
    }

    // Verify model is configured
    const logs =
      await $`docker-compose -f docker-compose-neo4j.yml logs --tail=5 graphiti-mcp`.text();
    if (!logs.includes(model.model)) {
      console.log('   ⚠️  Model not reflected in logs, continuing anyway...');
    }

    console.log('   ✅ Container ready');
    console.log('   📥 Testing entity extraction...');

    const result = await testModel(model, i);
    results.push(result);

    if (result.works) {
      console.log(
        `   ✅ PASS - ${result.entitiesFound} entities, ${result.expectedFound}/${EXPECTED_ENTITIES.length} expected (${result.extractionTimeMs}ms)`
      );
    } else {
      console.log(
        `   ❌ FAIL - ${result.error || `Only ${result.expectedFound}/${EXPECTED_ENTITIES.length} expected entities`}`
      );
    }
  }

  // Summary
  console.log(`\n${'═'.repeat(70)}`);
  console.log('📊 COMPREHENSIVE RESULTS');
  console.log(`${'═'.repeat(70)}`);

  const working = results.filter((r) => r.works);
  const failed = results.filter((r) => !r.works);

  console.log(`\n✅ WORKING MODELS (${working.length}/${results.length}):`);
  console.log('| Model | Cost/1K | Entities | Time |');
  console.log('|-------|---------|----------|------|');
  for (const r of working.sort((a, b) => a.cost - b.cost)) {
    console.log(
      `| ${r.name.padEnd(20)} | $${r.cost.toFixed(4).padStart(6)} | ${r.entitiesFound}/${r.expectedFound} | ${r.extractionTimeMs}ms |`
    );
  }

  if (failed.length > 0) {
    console.log(`\n❌ FAILED MODELS (${failed.length}/${results.length}):`);
    console.log('| Model | Cost/1K | Error |');
    console.log('|-------|---------|-------|');
    for (const r of failed) {
      const error = (r.error || 'Unknown').slice(0, 50);
      console.log(`| ${r.name.padEnd(20)} | $${r.cost.toFixed(4).padStart(6)} | ${error} |`);
    }
  }

  // Save results
  await Bun.write(
    'llm-mcp-comprehensive-results.json',
    JSON.stringify(
      {
        results,
        summary: {
          total: results.length,
          working: working.length,
          failed: failed.length,
          workingModels: working.map((r) => r.model),
          cheapestWorking: working.sort((a, b) => a.cost - b.cost)[0]?.name || 'None',
        },
        testEpisode: TEST_EPISODE,
        expectedEntities: EXPECTED_ENTITIES,
        timestamp: new Date().toISOString(),
      },
      null,
      2
    )
  );

  console.log('\n📁 Results saved to llm-mcp-comprehensive-results.json');

  // Restore to GPT-4o-mini (known working)
  console.log('\n🔄 Restoring GPT-4o-mini configuration...');
  await updateEnvAndRestart('openai/gpt-4o-mini');
}

main().catch(console.error);
