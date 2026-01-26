#!/usr/bin/env bun
/**
 * Test actual Graphiti add_memory with the configured LLM model
 * This tests against real Pydantic schemas, not just basic JSON
 */

const MCP_URL = 'http://localhost:8000/mcp';

interface MCPRequest {
  jsonrpc: '2.0';
  id: number;
  method: string;
  params?: Record<string, any>;
}

interface MCPResponse {
  jsonrpc: '2.0';
  id: number;
  result?: any;
  error?: { code: number; message: string };
}

let globalSessionId: string | null = null;

async function makeRequest(request: MCPRequest): Promise<MCPResponse> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json, text/event-stream',
  };

  if (globalSessionId) {
    // Server returns mcp-session-id, expects Mcp-Session-Id in requests
    headers['Mcp-Session-Id'] = globalSessionId;
  }

  const res = await fetch(MCP_URL, {
    method: 'POST',
    headers,
    body: JSON.stringify(request),
  });

  // Debug: print all response headers
  if (!globalSessionId) {
    console.log('   Response headers:');
    res.headers.forEach((value, key) => {
      console.log(`     ${key}: ${value}`);
    });
  }

  // Capture session ID from response headers (note: header is mcp-session-id)
  const newSessionId = res.headers.get('mcp-session-id');
  if (newSessionId) {
    globalSessionId = newSessionId;
  }

  const text = await res.text();

  // Parse SSE response
  const lines = text.split('\n');
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = line.slice(6);
      try {
        return JSON.parse(data);
      } catch {}
    }
  }

  // Try direct JSON parse
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`Failed to parse response: ${text}`);
  }
}

async function main() {
  console.log('==============================================');
  console.log('Graphiti Model Integration Test');
  console.log('==============================================\n');

  // Initialize session
  console.log('1. Initializing MCP session...');
  const initResult = await makeRequest({
    jsonrpc: '2.0',
    id: 1,
    method: 'initialize',
    params: {
      protocolVersion: '2024-11-05',
      capabilities: {},
      clientInfo: { name: 'model-test', version: '1.0' },
    },
  });

  if (initResult.error) {
    console.error('   ❌ Init failed:', initResult.error.message);
    process.exit(1);
  }

  console.log(`   ✅ Session: ${globalSessionId?.slice(0, 8) || 'unknown'}...`);
  console.log(
    `   Server: ${initResult.result.serverInfo.name} v${initResult.result.serverInfo.version}`
  );

  // Test add_memory
  console.log('\n2. Testing add_memory with real Graphiti schemas...');
  const testContent =
    'Alice Chen is a software engineer at TechCorp in San Francisco. She collaborated with Bob Martinez on the new authentication system last week.';
  console.log(`   Input: "${testContent}"\n`);

  const startTime = Date.now();

  const addResult = await makeRequest({
    jsonrpc: '2.0',
    id: 2,
    method: 'tools/call',
    params: {
      name: 'add_memory',
      arguments: {
        name: 'Deepseek Integration Test',
        episode_body: testContent,
        group_id: 'deepseek-integration-test',
        source: 'text',
        source_description: 'LLM model integration test',
      },
    },
  });

  const duration = Date.now() - startTime;

  if (addResult.error) {
    console.error('   ❌ add_memory FAILED:', addResult.error.message);
    console.log("\n   This model likely has issues with Graphiti's Pydantic schemas.");
    process.exit(1);
  }

  console.log(`   ✅ add_memory SUCCEEDED (${duration}ms)`);

  // Parse result content
  const resultContent = addResult.result?.content;
  if (resultContent && Array.isArray(resultContent)) {
    for (const item of resultContent) {
      if (item.type === 'text') {
        console.log(`   Result: ${item.text}`);
      }
    }
  }

  // Search for created entities
  console.log('\n3. Verifying entities were extracted...');

  const searchResult = await makeRequest({
    jsonrpc: '2.0',
    id: 3,
    method: 'tools/call',
    params: {
      name: 'search_nodes',
      arguments: {
        query: 'Alice Chen TechCorp',
        group_ids: ['deepseek-integration-test'],
        max_nodes: 10,
      },
    },
  });

  if (searchResult.error) {
    console.error('   ⚠️  search_nodes failed:', searchResult.error.message);
  } else {
    const searchContent = searchResult.result?.content;
    if (searchContent && Array.isArray(searchContent)) {
      for (const item of searchContent) {
        if (item.type === 'text') {
          try {
            const nodes = JSON.parse(item.text);
            console.log(`   Found ${nodes.length} nodes:`);
            for (const node of nodes.slice(0, 5)) {
              console.log(`     - ${node.name} (${node.labels?.join(', ') || 'no labels'})`);
            }
          } catch {
            console.log(`   Result: ${item.text.slice(0, 200)}...`);
          }
        }
      }
    }
  }

  // Cleanup
  console.log('\n4. Cleaning up test data...');

  const clearResult = await makeRequest({
    jsonrpc: '2.0',
    id: 4,
    method: 'tools/call',
    params: {
      name: 'clear_graph',
      arguments: {
        group_ids: ['deepseek-integration-test'],
      },
    },
  });

  if (clearResult.error) {
    console.error('   ⚠️  Cleanup failed:', clearResult.error.message);
  } else {
    console.log('   ✅ Test data cleared');
  }

  console.log('\n==============================================');
  console.log('TEST PASSED - Model works with Graphiti');
  console.log(`Total time: ${duration}ms`);
  console.log('==============================================');
}

main().catch((err) => {
  console.error('Test failed:', err.message);
  process.exit(1);
});
