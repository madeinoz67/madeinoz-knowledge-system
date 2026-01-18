#!/usr/bin/env bun
/**
 * Test OpenRouter LLM models for cost vs performance
 * Evaluates: entity extraction quality, response time, and cost
 *
 * Usage: OPENROUTER_API_KEY=sk-or-... bun run test-openrouter-models.ts
 */

const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY;
const OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1";

if (!OPENROUTER_API_KEY) {
  console.error("❌ OPENROUTER_API_KEY environment variable required");
  console.error("   Get your key at: https://openrouter.ai/keys");
  console.error("   Usage: OPENROUTER_API_KEY=sk-or-... bun run test-openrouter-models.ts");
  process.exit(1);
}

// Models to test with their pricing (per 1M tokens as of Jan 2026)
// Prices from https://openrouter.ai/models
const LLM_MODELS = [
  // Top tier - highest quality
  { id: "anthropic/claude-sonnet-4", name: "Claude Sonnet 4", inputPrice: 3.00, outputPrice: 15.00 },
  { id: "openai/gpt-4o", name: "GPT-4o", inputPrice: 2.50, outputPrice: 10.00 },
  { id: "google/gemini-2.0-flash-001", name: "Gemini 2.0 Flash", inputPrice: 0.10, outputPrice: 0.40 },

  // Mid tier - good balance
  { id: "openai/gpt-4o-mini", name: "GPT-4o Mini", inputPrice: 0.15, outputPrice: 0.60 },
  { id: "anthropic/claude-3.5-haiku", name: "Claude 3.5 Haiku", inputPrice: 0.80, outputPrice: 4.00 },
  { id: "google/gemini-flash-1.5", name: "Gemini 1.5 Flash", inputPrice: 0.075, outputPrice: 0.30 },

  // Budget tier - cost effective
  { id: "meta-llama/llama-3.3-70b-instruct", name: "Llama 3.3 70B", inputPrice: 0.40, outputPrice: 0.40 },
  { id: "meta-llama/llama-3.1-8b-instruct", name: "Llama 3.1 8B", inputPrice: 0.055, outputPrice: 0.055 },
  { id: "mistralai/mistral-7b-instruct", name: "Mistral 7B", inputPrice: 0.055, outputPrice: 0.055 },
  { id: "qwen/qwen-2.5-72b-instruct", name: "Qwen 2.5 72B", inputPrice: 0.35, outputPrice: 0.40 },

  // Deep reasoning (may be slower)
  { id: "deepseek/deepseek-r1", name: "DeepSeek R1", inputPrice: 0.55, outputPrice: 2.19 },
  { id: "deepseek/deepseek-chat", name: "DeepSeek V3", inputPrice: 0.14, outputPrice: 0.28 },
];

// Test prompts for entity extraction (similar to Graphiti requirements)
const TEST_CASES = [
  {
    name: "Basic Entity Extraction",
    text: `John Smith works at Acme Corp in New York. He met Sarah Jones yesterday to discuss the Q4 budget.`,
    expectedEntities: ["John Smith", "Acme Corp", "New York", "Sarah Jones"],
    expectedRelationships: ["works_at", "located_in", "met"],
  },
  {
    name: "Technical Content",
    text: `The PAI system uses Neo4j for graph storage and OpenAI for embeddings. It was created by Daniel Miessler to help people build personalized AI infrastructure.`,
    expectedEntities: ["PAI", "Neo4j", "OpenAI", "Daniel Miessler"],
    expectedRelationships: ["uses", "created_by"],
  },
  {
    name: "Complex Relationships",
    text: `Alice, the CTO of TechStart, acquired DataFlow Inc last month. Bob, who was DataFlow's CEO, now reports to Alice. The deal was worth $50M.`,
    expectedEntities: ["Alice", "TechStart", "DataFlow Inc", "Bob"],
    expectedRelationships: ["cto_of", "acquired", "reports_to"],
  },
];

const EXTRACTION_PROMPT = (text: string) => `Extract entities and relationships from this text. Return ONLY valid JSON, no other text.

Text: "${text}"

Return this exact format:
{"entities": [{"name": "string", "type": "PERSON|ORGANIZATION|LOCATION|CONCEPT"}], "relationships": [{"source": "string", "target": "string", "type": "string"}]}`;

interface ModelResult {
  model: string;
  modelName: string;
  inputPrice: number;
  outputPrice: number;
  avgResponseMs: number;
  avgInputTokens: number;
  avgOutputTokens: number;
  costPer1000Calls: number;
  qualityScore: number;
  passRate: number;
  results: TestCaseResult[];
  error?: string;
}

interface TestCaseResult {
  name: string;
  passed: boolean;
  entities: number;
  relationships: number;
  responseMs: number;
  inputTokens: number;
  outputTokens: number;
  error?: string;
}

function extractJSON(text: string): { entities: any[]; relationships: any[] } | null {
  // Remove markdown code blocks
  let clean = text.replace(/```json\n?/g, "").replace(/```\n?/g, "");

  // Remove thinking tags (DeepSeek uses these)
  clean = clean.replace(/<think>[\s\S]*?<\/think>/g, "");
  clean = clean.trim();

  // Try direct parse
  try {
    const obj = JSON.parse(clean);
    if (obj.entities && obj.relationships) return obj;
  } catch {}

  // Find JSON in response
  const jsonMatch = clean.match(/\{[\s\S]*"entities"[\s\S]*"relationships"[\s\S]*\}/);
  if (jsonMatch) {
    try {
      const obj = JSON.parse(jsonMatch[0]);
      if (obj.entities && obj.relationships) return obj;
    } catch {}
  }

  return null;
}

function calculateQuality(result: { entities: any[]; relationships: any[] }, expected: typeof TEST_CASES[0]): number {
  // Score based on: found expected entities + found relationships + reasonable count
  let score = 0;
  const maxScore = 100;

  // Entity coverage (40 points)
  const foundEntities = result.entities.map(e => e.name.toLowerCase());
  const expectedFound = expected.expectedEntities.filter(e =>
    foundEntities.some(f => f.includes(e.toLowerCase()) || e.toLowerCase().includes(f))
  );
  score += (expectedFound.length / expected.expectedEntities.length) * 40;

  // Relationship presence (30 points)
  const hasRelationships = result.relationships.length > 0;
  const reasonableRelCount = result.relationships.length >= 1 && result.relationships.length <= 10;
  if (hasRelationships) score += 15;
  if (reasonableRelCount) score += 15;

  // Valid structure (30 points)
  const validEntities = result.entities.every(e => e.name && typeof e.name === 'string');
  const validRels = result.relationships.every(r => r.source && r.target && r.type);
  if (validEntities) score += 15;
  if (validRels) score += 15;

  return Math.min(score, maxScore);
}

async function testModel(model: typeof LLM_MODELS[0]): Promise<ModelResult> {
  console.log(`\n🔄 Testing: ${model.name} (${model.id})`);
  console.log("   " + "─".repeat(50));

  const results: TestCaseResult[] = [];

  for (const testCase of TEST_CASES) {
    const start = Date.now();

    try {
      const response = await fetch(`${OPENROUTER_BASE_URL}/chat/completions`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${OPENROUTER_API_KEY}`,
          "Content-Type": "application/json",
          "HTTP-Referer": "https://pai.dev",
          "X-Title": "PAI Knowledge System Test",
        },
        body: JSON.stringify({
          model: model.id,
          messages: [{ role: "user", content: EXTRACTION_PROMPT(testCase.text) }],
          temperature: 0.1,
          max_tokens: 1000,
        }),
      });

      const responseMs = Date.now() - start;

      if (!response.ok) {
        const error = await response.text();
        console.log(`   ❌ ${testCase.name}: HTTP ${response.status}`);
        results.push({
          name: testCase.name,
          passed: false,
          entities: 0,
          relationships: 0,
          responseMs,
          inputTokens: 0,
          outputTokens: 0,
          error: `HTTP ${response.status}: ${error.slice(0, 100)}`,
        });
        continue;
      }

      const data = await response.json() as any;
      const content = data.choices?.[0]?.message?.content || "";
      const inputTokens = data.usage?.prompt_tokens || 0;
      const outputTokens = data.usage?.completion_tokens || 0;

      const json = extractJSON(content);

      if (json) {
        const quality = calculateQuality(json, testCase);
        console.log(`   ✅ ${testCase.name}: ${json.entities.length} entities, ${json.relationships.length} rels (${responseMs}ms, quality: ${quality.toFixed(0)}%)`);
        results.push({
          name: testCase.name,
          passed: true,
          entities: json.entities.length,
          relationships: json.relationships.length,
          responseMs,
          inputTokens,
          outputTokens,
        });
      } else {
        console.log(`   ❌ ${testCase.name}: Invalid JSON (${responseMs}ms)`);
        results.push({
          name: testCase.name,
          passed: false,
          entities: 0,
          relationships: 0,
          responseMs,
          inputTokens,
          outputTokens,
          error: "Invalid JSON structure",
        });
      }
    } catch (err: any) {
      const responseMs = Date.now() - start;
      console.log(`   ❌ ${testCase.name}: ${err.message}`);
      results.push({
        name: testCase.name,
        passed: false,
        entities: 0,
        relationships: 0,
        responseMs,
        inputTokens: 0,
        outputTokens: 0,
        error: err.message,
      });
    }

    // Rate limiting - wait between calls
    await new Promise(r => setTimeout(r, 500));
  }

  // Calculate aggregates
  const passedTests = results.filter(r => r.passed);
  const avgResponseMs = results.length > 0
    ? Math.round(results.reduce((a, r) => a + r.responseMs, 0) / results.length)
    : 0;
  const avgInputTokens = results.length > 0
    ? Math.round(results.reduce((a, r) => a + r.inputTokens, 0) / results.length)
    : 0;
  const avgOutputTokens = results.length > 0
    ? Math.round(results.reduce((a, r) => a + r.outputTokens, 0) / results.length)
    : 0;

  // Cost per 1000 API calls
  const costPer1000 = (
    (avgInputTokens / 1_000_000) * model.inputPrice * 1000 +
    (avgOutputTokens / 1_000_000) * model.outputPrice * 1000
  );

  // Quality score (average across passed tests)
  let qualityScore = 0;
  if (passedTests.length > 0) {
    // Re-calculate quality for passed tests
    for (let i = 0; i < TEST_CASES.length; i++) {
      if (results[i].passed) {
        qualityScore += calculateQuality(
          { entities: Array(results[i].entities).fill({ name: "x" }), relationships: Array(results[i].relationships).fill({ source: "a", target: "b", type: "c" }) },
          TEST_CASES[i]
        );
      }
    }
    qualityScore = qualityScore / passedTests.length;
  }

  return {
    model: model.id,
    modelName: model.name,
    inputPrice: model.inputPrice,
    outputPrice: model.outputPrice,
    avgResponseMs,
    avgInputTokens,
    avgOutputTokens,
    costPer1000Calls: costPer1000,
    qualityScore,
    passRate: (passedTests.length / results.length) * 100,
    results,
  };
}

function printComparisonTable(results: ModelResult[]) {
  console.log("\n" + "═".repeat(120));
  console.log("📊 COST VS PERFORMANCE COMPARISON TABLE");
  console.log("═".repeat(120) + "\n");

  // Sort by value score (quality / cost)
  const sortedResults = [...results]
    .filter(r => r.passRate > 0)
    .sort((a, b) => {
      const valueA = a.costPer1000Calls > 0 ? a.qualityScore / a.costPer1000Calls : 0;
      const valueB = b.costPer1000Calls > 0 ? b.qualityScore / b.costPer1000Calls : 0;
      return valueB - valueA;
    });

  // Header
  console.log("| Rank | Model                    | Pass Rate | Quality | Avg Time | Input$/M | Output$/M | Cost/1K Calls | Value Score |");
  console.log("|------|--------------------------|-----------|---------|----------|----------|-----------|---------------|-------------|");

  sortedResults.forEach((r, i) => {
    const valueScore = r.costPer1000Calls > 0 ? (r.qualityScore / r.costPer1000Calls).toFixed(1) : "∞";
    console.log(
      `| ${(i + 1).toString().padStart(4)} | ${r.modelName.padEnd(24)} | ${r.passRate.toFixed(0).padStart(7)}% | ${r.qualityScore.toFixed(0).padStart(5)}% | ${(r.avgResponseMs + "ms").padStart(8)} | $${r.inputPrice.toFixed(2).padStart(6)} | $${r.outputPrice.toFixed(2).padStart(9)} | $${r.costPer1000Calls.toFixed(4).padStart(11)} | ${valueScore.toString().padStart(11)} |`
    );
  });

  // Failed models
  const failed = results.filter(r => r.passRate === 0);
  if (failed.length > 0) {
    console.log("\n❌ Failed Models:");
    failed.forEach(r => console.log(`   - ${r.modelName}: ${r.results[0]?.error || "Unknown error"}`));
  }

  // Recommendations
  console.log("\n" + "─".repeat(120));
  console.log("📌 RECOMMENDATIONS");
  console.log("─".repeat(120));

  const bestQuality = sortedResults.reduce((a, b) => a.qualityScore > b.qualityScore ? a : b, sortedResults[0]);
  const bestValue = sortedResults[0]; // Already sorted by value
  const cheapest = sortedResults.reduce((a, b) => a.costPer1000Calls < b.costPer1000Calls ? a : b, sortedResults[0]);
  const fastest = sortedResults.reduce((a, b) => a.avgResponseMs < b.avgResponseMs ? a : b, sortedResults[0]);

  console.log(`\n🏆 Best Quality:     ${bestQuality?.modelName} (${bestQuality?.qualityScore.toFixed(0)}% quality)`);
  console.log(`💰 Best Value:       ${bestValue?.modelName} (${bestValue?.qualityScore.toFixed(0)}% quality at $${bestValue?.costPer1000Calls.toFixed(4)}/1K calls)`);
  console.log(`🪙 Cheapest:         ${cheapest?.modelName} ($${cheapest?.costPer1000Calls.toFixed(4)}/1K calls)`);
  console.log(`⚡ Fastest:          ${fastest?.modelName} (${fastest?.avgResponseMs}ms avg)`);

  // Hybrid recommendation
  console.log(`\n🎯 RECOMMENDED FOR KNOWLEDGE SYSTEM:`);
  console.log(`   Primary (best balance): ${bestValue?.modelName}`);
  console.log(`   Budget option:          ${cheapest?.modelName}`);
  console.log(`   Premium option:         ${bestQuality?.modelName}`);
}

async function main() {
  console.log("═".repeat(60));
  console.log("🧪 OpenRouter LLM Model Comparison Test");
  console.log(`   Testing ${LLM_MODELS.length} models for entity extraction`);
  console.log("═".repeat(60));

  const results: ModelResult[] = [];

  for (const model of LLM_MODELS) {
    try {
      const result = await testModel(model);
      results.push(result);
    } catch (err: any) {
      console.log(`\n❌ ${model.name}: ${err.message}`);
      results.push({
        model: model.id,
        modelName: model.name,
        inputPrice: model.inputPrice,
        outputPrice: model.outputPrice,
        avgResponseMs: 0,
        avgInputTokens: 0,
        avgOutputTokens: 0,
        costPer1000Calls: 0,
        qualityScore: 0,
        passRate: 0,
        results: [],
        error: err.message,
      });
    }

    // Rate limiting between models
    await new Promise(r => setTimeout(r, 1000));
  }

  // Print comparison table
  printComparisonTable(results);

  // Save results to file
  const outputPath = new URL("./openrouter-test-results.json", import.meta.url).pathname;
  await Bun.write(outputPath, JSON.stringify({
    results,
    timestamp: new Date().toISOString(),
    testCases: TEST_CASES.map(t => t.name),
  }, null, 2));
  console.log(`\n📁 Results saved to: ${outputPath}`);
}

main().catch(console.error);
