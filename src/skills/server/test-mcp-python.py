#!/usr/bin/env python3
"""
Real-life MCP Knowledge System Test using Python MCP client
Tests add_memory, search_nodes, and search_memory_facts operations
"""

import asyncio
import json
import time
from datetime import datetime

import httpx

MCP_BASE_URL = "http://localhost:8000"

# Test data
TEST_EPISODES = [
    {
        "name": "Tech Stack Decision",
        "body": "The team decided to use TypeScript with Bun runtime for the new API project. Sarah recommended Hono for the HTTP framework due to its performance and edge compatibility.",
        "group_id": "mcp-test"
    },
    {
        "name": "Meeting Notes",
        "body": "John Smith from Acme Corp met with our CTO Alice Chen to discuss the Q1 roadmap. They agreed on a partnership to integrate Acme's payment API into our platform.",
        "group_id": "mcp-test"
    },
    {
        "name": "Technical Documentation",
        "body": "The PAI system uses Neo4j as the graph database backend. OpenAI's gpt-4o-mini is configured for entity extraction, while mxbai-embed-large running on Ollama handles embeddings.",
        "group_id": "mcp-test"
    }
]

SEARCH_QUERIES = [
    {"query": "What technology stack is being used?", "expected": ["TypeScript", "Bun", "Hono"]},
    {"query": "Who is working with Acme Corp?", "expected": ["John Smith", "Alice Chen", "Acme Corp"]},
    {"query": "What database does PAI use?", "expected": ["Neo4j", "PAI"]}
]

results = []


async def call_mcp_tool(client: httpx.AsyncClient, session_id: str, tool_name: str, args: dict) -> dict:
    """Call an MCP tool and return the result."""
    start = time.time()

    # Build the MCP request
    request = {
        "jsonrpc": "2.0",
        "id": int(time.time() * 1000),
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": args
        }
    }

    try:
        response = await client.post(
            f"{MCP_BASE_URL}/mcp",
            json=request,
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                "X-Session-Id": session_id
            },
            timeout=60.0
        )

        duration_ms = int((time.time() - start) * 1000)

        # Parse SSE response
        text = response.text
        result_data = None
        error = None

        for line in text.split('\n'):
            if line.startswith('data: '):
                try:
                    data = json.loads(line[6:])
                    if 'result' in data:
                        result_data = data['result']
                    if 'error' in data:
                        error = data['error']
                except json.JSONDecodeError:
                    pass

        return {
            "success": result_data is not None and error is None,
            "result": result_data,
            "error": error,
            "duration_ms": duration_ms,
            "raw": text[:500] if len(text) > 500 else text
        }

    except Exception as e:
        return {
            "success": False,
            "result": None,
            "error": str(e),
            "duration_ms": int((time.time() - start) * 1000),
            "raw": ""
        }


async def create_session(client: httpx.AsyncClient) -> str:
    """Initialize MCP session."""
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0"}
        }
    }

    try:
        response = await client.post(
            f"{MCP_BASE_URL}/mcp",
            json=request,
            headers={"Content-Type": "application/json"},
            timeout=30.0
        )

        # Extract session ID from response headers or body
        session_id = response.headers.get("X-Session-Id", f"session-{int(time.time())}")
        return session_id
    except Exception as e:
        print(f"Session creation failed: {e}")
        return f"session-{int(time.time())}"


async def test_add_memory(client: httpx.AsyncClient, session_id: str):
    """Test add_memory operations."""
    print("\n" + "=" * 60)
    print("📥 TEST: add_memory operations")
    print("=" * 60)

    for episode in TEST_EPISODES:
        result = await call_mcp_tool(client, session_id, "add_memory", {
            "name": episode["name"],
            "episode_body": episode["body"],
            "source": "text",
            "group_id": episode["group_id"]
        })

        status = "✅" if result["success"] else "❌"
        print(f"\n   {status} \"{episode['name']}\" ({result['duration_ms']}ms)")

        if not result["success"]:
            print(f"      Error: {result.get('error', result.get('raw', 'Unknown'))[:100]}")

        results.append({
            "operation": "add_memory",
            "name": episode["name"],
            "success": result["success"],
            "duration_ms": result["duration_ms"]
        })

        # Wait for async processing
        await asyncio.sleep(3)


async def test_search_nodes(client: httpx.AsyncClient, session_id: str):
    """Test search_nodes operations."""
    print("\n" + "=" * 60)
    print("🔍 TEST: search_nodes operations")
    print("=" * 60)

    for search in SEARCH_QUERIES:
        result = await call_mcp_tool(client, session_id, "search_nodes", {
            "query": search["query"],
            "group_ids": ["mcp-test"],
            "max_nodes": 10
        })

        # Check if expected entities were found
        found_expected = False
        found_nodes = []

        if result["result"] and "content" in result["result"]:
            try:
                content = result["result"]["content"]
                if content and len(content) > 0:
                    nodes_data = json.loads(content[0].get("text", "{}"))
                    found_nodes = nodes_data.get("nodes", [])
                    for node in found_nodes:
                        if any(exp.lower() in node.get("name", "").lower() for exp in search["expected"]):
                            found_expected = True
                            break
            except:
                pass

        status = "✅" if found_expected else "⚠️"
        print(f"\n   {status} \"{search['query']}\" ({result['duration_ms']}ms)")

        if found_nodes:
            print(f"      Found {len(found_nodes)} nodes:")
            for node in found_nodes[:3]:
                print(f"        - {node.get('name', 'N/A')} ({node.get('entity_type', 'N/A')})")

        results.append({
            "operation": "search_nodes",
            "query": search["query"],
            "success": found_expected,
            "duration_ms": result["duration_ms"],
            "nodes_found": len(found_nodes)
        })

        await asyncio.sleep(0.5)


async def test_search_facts(client: httpx.AsyncClient, session_id: str):
    """Test search_memory_facts operations."""
    print("\n" + "=" * 60)
    print("🔗 TEST: search_memory_facts operations")
    print("=" * 60)

    fact_queries = [
        "partnership between companies",
        "technology decisions",
        "database configuration"
    ]

    for query in fact_queries:
        result = await call_mcp_tool(client, session_id, "search_memory_facts", {
            "query": query,
            "group_ids": ["mcp-test"],
            "max_facts": 5
        })

        found_facts = []
        if result["result"] and "content" in result["result"]:
            try:
                content = result["result"]["content"]
                if content and len(content) > 0:
                    facts_data = json.loads(content[0].get("text", "{}"))
                    found_facts = facts_data.get("facts", [])
            except:
                pass

        status = "✅" if found_facts else "⚠️"
        print(f"\n   {status} \"{query}\" ({result['duration_ms']}ms)")

        if found_facts:
            print(f"      Found {len(found_facts)} facts:")
            for fact in found_facts[:3]:
                fact_text = fact.get("fact", "N/A")[:80]
                print(f"        - {fact_text}...")

        results.append({
            "operation": "search_memory_facts",
            "query": query,
            "success": len(found_facts) > 0,
            "duration_ms": result["duration_ms"],
            "facts_found": len(found_facts)
        })

        await asyncio.sleep(0.5)


async def main():
    print("=" * 60)
    print("🧪 Real-Life MCP Knowledge System Test (Python)")
    print("=" * 60)

    # Health check
    async with httpx.AsyncClient() as client:
        health = await client.get(f"{MCP_BASE_URL}/health")
        health_data = health.json()
        print(f"\n📋 Health Check:")
        print(f"   Status: {health_data.get('status')}")
        print(f"   Patch: {health_data.get('patch', 'none')}")

        # Create session
        print("\n📋 Creating MCP session...")
        session_id = await create_session(client)
        print(f"   Session: {session_id}")

        # Run tests
        await test_add_memory(client, session_id)
        await test_search_nodes(client, session_id)
        await test_search_facts(client, session_id)

    # Summary
    print("\n" + "=" * 60)
    print("📊 RESULTS SUMMARY")
    print("=" * 60)

    by_operation = {}
    for r in results:
        op = r["operation"]
        if op not in by_operation:
            by_operation[op] = {"success": 0, "total": 0, "total_ms": 0}
        by_operation[op]["total"] += 1
        if r["success"]:
            by_operation[op]["success"] += 1
        by_operation[op]["total_ms"] += r["duration_ms"]

    print("\n| Operation          | Success Rate | Avg Duration |")
    print("|--------------------|--------------|--------------|")
    for op, stats in by_operation.items():
        rate = (stats["success"] / stats["total"]) * 100 if stats["total"] > 0 else 0
        avg_ms = stats["total_ms"] // stats["total"] if stats["total"] > 0 else 0
        print(f"| {op:18} | {rate:10.0f}% | {avg_ms:10}ms |")

    # Save results
    output = {
        "results": results,
        "summary": by_operation,
        "timestamp": datetime.now().isoformat(),
        "config": {
            "llm": "gpt-4o-mini",
            "embedder": "openai",
            "database": "neo4j"
        }
    }

    with open("mcp-test-results.json", "w") as f:
        json.dump(output, f, indent=2)

    print("\n📁 Results saved to mcp-test-results.json")


if __name__ == "__main__":
    asyncio.run(main())
