#!/usr/bin/env bun
/**
 * Test Ollama models for JSON output compatibility with Graphiti
 * Tests entity extraction capability similar to what Graphiti requires
 */

const OLLAMA_HOST = "http://10.0.0.150:11434";

// Test prompt similar to Graphiti's entity extraction
const TEST_PROMPT = `Extract entities from this text and return ONLY valid JSON, no other text:

Text: "John Smith works at Acme Corp in New York. He met Sarah Jones yesterday to discuss the Q4 budget."

Return format:
{"entities": [{"name": "string", "type": "string"}], "relationships": [{"source": "string", "target": "string", "type": "string"}]}`;

// LLM models to test (excluding embedding models)
const MODELS = [
  "tulu3:latest",
  "Qwen3:latest",
  "Qwen3:8b",
  "qwen3-coder:latest",
  "phi4:latest",
  "phi3:medium",
  "mistral:latest",
  "mistral:instruct",
  "Llama3.2:latest",
  "llama3.1:latest",
  "gemma2:9b",
  "dolphin-mistral:7b-v2.6-dpo-laser-q8_0",
  "Deepseek-r1:latest",
  "Deepseek-r1:8b",
  "deepseek-coder-v2:latest",
  "codestral:latest",
];

interface TestResult {
  model: string;
  status: "passed" | "failed";
  entities?: number;
  relationships?: number;
  duration_ms?: number;
  error?: string;
  raw_output?: string;
}

function extractJSON(text: string): { entities: any[]; relationships: any[] } | null {
  // Remove markdown code blocks
  let clean = text.replace(/```json\n?/g, "").replace(/```\n?/g, "");

  // Remove thinking tags (DeepSeek-r1 uses these)
  clean = clean.replace(/<think>[\s\S]*?<\/think>/g, "");

  // Trim whitespace
  clean = clean.trim();

  // Try direct parse first
  try {
    const obj = JSON.parse(clean);
    if (obj.entities && obj.relationships) {
      return obj;
    }
  } catch {}

  // Try to find JSON object in response
  const jsonMatch = clean.match(/\{[\s\S]*"entities"[\s\S]*"relationships"[\s\S]*\}/);
  if (jsonMatch) {
    try {
      const obj = JSON.parse(jsonMatch[0]);
      if (obj.entities && obj.relationships) {
        return obj;
      }
    } catch {}
  }

  // Try line by line to find the JSON
  const lines = clean.split("\n");
  let jsonStr = "";
  let inJson = false;
  let braceCount = 0;

  for (const line of lines) {
    if (line.includes("{") && !inJson) {
      inJson = true;
    }
    if (inJson) {
      jsonStr += line + "\n";
      braceCount += (line.match(/\{/g) || []).length;
      braceCount -= (line.match(/\}/g) || []).length;
      if (braceCount === 0) {
        try {
          const obj = JSON.parse(jsonStr.trim());
          if (obj.entities && obj.relationships) {
            return obj;
          }
        } catch {}
        jsonStr = "";
        inJson = false;
      }
    }
  }

  return null;
}

async function testModel(model: string): Promise<TestResult> {
  console.log(`\nTesting: ${model}`);
  console.log("---");

  const startTime = Date.now();

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 120000); // 2 min timeout

    const response = await fetch(`${OLLAMA_HOST}/api/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        prompt: TEST_PROMPT,
        stream: false,
        options: { temperature: 0.1 },
      }),
      signal: controller.signal,
    });

    clearTimeout(timeout);

    if (!response.ok) {
      const error = await response.text();
      console.log(`  ❌ HTTP Error: ${response.status}`);
      return { model, status: "failed", error: `HTTP ${response.status}: ${error}` };
    }

    const data = await response.json() as { response?: string; error?: string };
    const duration = Date.now() - startTime;

    if (data.error) {
      console.log(`  ❌ API Error: ${data.error}`);
      return { model, status: "failed", error: data.error };
    }

    if (!data.response) {
      console.log(`  ❌ No response content`);
      return { model, status: "failed", error: "No response content" };
    }

    const json = extractJSON(data.response);

    if (json) {
      console.log(`  ✅ VALID JSON - ${json.entities.length} entities, ${json.relationships.length} relationships (${duration}ms)`);
      return {
        model,
        status: "passed",
        entities: json.entities.length,
        relationships: json.relationships.length,
        duration_ms: duration,
      };
    } else {
      console.log(`  ❌ Invalid JSON structure`);
      console.log(`  Preview: ${data.response.slice(0, 150)}...`);
      return {
        model,
        status: "failed",
        error: "Invalid JSON structure",
        raw_output: data.response.slice(0, 300),
      };
    }
  } catch (err: any) {
    if (err.name === "AbortError") {
      console.log(`  ❌ TIMEOUT`);
      return { model, status: "failed", error: "Timeout (>120s)" };
    }
    console.log(`  ❌ Error: ${err.message}`);
    return { model, status: "failed", error: err.message };
  }
}

async function main() {
  console.log("==============================================");
  console.log("Ollama Model JSON Compatibility Test");
  console.log(`Testing ${MODELS.length} models for entity extraction`);
  console.log("==============================================");

  const results: TestResult[] = [];

  for (const model of MODELS) {
    const result = await testModel(model);
    results.push(result);
  }

  const passed = results.filter((r) => r.status === "passed");
  const failed = results.filter((r) => r.status === "failed");

  console.log("\n==============================================");
  console.log("RESULTS SUMMARY");
  console.log("==============================================\n");

  console.log(`✅ PASSED (${passed.length} models):`);
  for (const r of passed) {
    console.log(`   - ${r.model} (${r.entities} entities, ${r.relationships} rels, ${r.duration_ms}ms)`);
  }

  console.log(`\n❌ FAILED (${failed.length} models):`);
  for (const r of failed) {
    console.log(`   - ${r.model} (${r.error})`);
  }

  // Output JSON for documentation
  console.log("\n==============================================");
  console.log("JSON OUTPUT (for documentation)");
  console.log("==============================================");
  console.log(JSON.stringify({ passed, failed }, null, 2));

  // Write results to file
  const outputPath = new URL("./test-results.json", import.meta.url).pathname;
  await Bun.write(outputPath, JSON.stringify({ passed, failed, timestamp: new Date().toISOString() }, null, 2));
  console.log(`\nResults written to: ${outputPath}`);
}

main();
