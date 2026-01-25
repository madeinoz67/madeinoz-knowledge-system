#!/usr/bin/env bun
/**
 * MCP Knowledge System Test with proper session handling
 */

const MCP_URL = 'http://localhost:8000/mcp';

async function initSession(): Promise<string | null> {
  const res = await fetch(MCP_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: 1,
      method: 'initialize',
      params: {
        protocolVersion: '2024-11-05',
        capabilities: {},
        clientInfo: { name: 'bun-test', version: '1.0' },
      },
    }),
  });

  // Get session ID from header or response
  const sessionId = res.headers.get('mcp-session-id') || res.headers.get('x-session-id');
  const text = await res.text();
  console.log('Init response:', text.slice(0, 200));
  console.log('Headers:', Object.fromEntries(res.headers.entries()));
  return sessionId;
}

async function callTool(sessionId: string | null, tool: string, args: any) {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (sessionId) {
    headers['mcp-session-id'] = sessionId;
    headers['x-session-id'] = sessionId;
  }

  const start = Date.now();
  const res = await fetch(MCP_URL, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: Date.now(),
      method: 'tools/call',
      params: { name: tool, arguments: args },
    }),
  });

  const text = await res.text();
  const duration = Date.now() - start;

  // Parse result
  let result: any = null;
  for (const line of text.split('\n')) {
    if (line.startsWith('data: ')) {
      try {
        const data = JSON.parse(line.slice(6));
        if (data.result) result = data.result;
      } catch {}
    }
  }

  // Also try direct JSON
  if (!result) {
    try {
      const json = JSON.parse(text);
      result = json.result || json;
    } catch {}
  }

  return { result, duration, raw: text, headers: Object.fromEntries(res.headers.entries()) };
}

async function main() {
  console.log('═'.repeat(60));
  console.log('🧪 MCP Session Test');
  console.log('═'.repeat(60));

  // Step 1: Initialize session
  console.log('\n📋 Step 1: Initialize session');
  const sessionId = await initSession();
  console.log(`Session ID: ${sessionId || 'none'}`);

  // Step 2: Call tools/list to see available tools
  console.log('\n📋 Step 2: List available tools');
  const listRes = await fetch(MCP_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(sessionId ? { 'mcp-session-id': sessionId } : {}),
    },
    body: JSON.stringify({
      jsonrpc: '2.0',
      id: 2,
      method: 'tools/list',
      params: {},
    }),
  });
  const listText = await listRes.text();
  console.log('Tools response:', listText.slice(0, 500));

  // Step 3: Try add_memory with session
  console.log('\n📋 Step 3: Test add_memory');
  const addRes = await callTool(sessionId, 'add_memory', {
    name: 'Test Episode',
    episode_body: 'This is a test episode for MCP testing. John works at Acme Corp.',
    source: 'text',
    group_id: 'mcp-test',
  });
  console.log(`Duration: ${addRes.duration}ms`);
  console.log('Response:', addRes.raw.slice(0, 300));
  console.log('Response headers:', addRes.headers);

  // Step 4: Search nodes
  console.log('\n📋 Step 4: Test search_nodes');
  await Bun.sleep(2000); // Wait for processing
  const searchRes = await callTool(sessionId, 'search_nodes', {
    query: 'Acme Corp',
    max_nodes: 5,
  });
  console.log(`Duration: ${searchRes.duration}ms`);
  console.log('Response:', searchRes.raw.slice(0, 500));
}

main();
