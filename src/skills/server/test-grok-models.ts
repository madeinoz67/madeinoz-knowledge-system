#!/usr/bin/env bun
/**
 * Test Grok models via OpenRouter
 */

const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY;
const OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1';

if (!OPENROUTER_API_KEY) {
  console.error('❌ OPENROUTER_API_KEY required');
  process.exit(1);
}

// Grok models on OpenRouter
const GROK_MODELS = [
  { id: 'x-ai/grok-2-1212', name: 'Grok 2', inputPrice: 2.0, outputPrice: 10.0 },
  { id: 'x-ai/grok-2-vision-1212', name: 'Grok 2 Vision', inputPrice: 2.0, outputPrice: 10.0 },
  { id: 'x-ai/grok-beta', name: 'Grok Beta', inputPrice: 5.0, outputPrice: 15.0 },
];

const TEST_CASES = [
  {
    name: 'Basic Entity Extraction',
    text: 'John Smith works at Acme Corp in New York. He met Sarah Jones yesterday to discuss the Q4 budget.',
  },
  {
    name: 'Technical Content',
    text: 'The PAI system uses Neo4j for graph storage and OpenAI for embeddings. It was created by Daniel Miessler.',
  },
  {
    name: 'Complex Relationships',
    text: `Alice, the CTO of TechStart, acquired DataFlow Inc last month. Bob, who was DataFlow's CEO, now reports to Alice.`,
  },
];

const PROMPT = (
  text: string
) => `Extract entities and relationships from this text. Return ONLY valid JSON.

Text: "${text}"

Format: {"entities": [{"name": "string", "type": "PERSON|ORGANIZATION|LOCATION"}], "relationships": [{"source": "string", "target": "string", "type": "string"}]}`;

function extractJSON(text: string): any | null {
  const clean = text
    .replace(/```json\n?/g, '')
    .replace(/```\n?/g, '')
    .trim();
  try {
    const obj = JSON.parse(clean);
    if (obj.entities && obj.relationships) return obj;
  } catch {}
  const match = clean.match(/\{[\s\S]*"entities"[\s\S]*"relationships"[\s\S]*\}/);
  if (match) {
    try {
      return JSON.parse(match[0]);
    } catch {}
  }
  return null;
}

async function testModel(model: (typeof GROK_MODELS)[0]) {
  console.log(`\n🔄 Testing: ${model.name} (${model.id})`);
  console.log(`   ${'─'.repeat(50)}`);

  let passed = 0;
  let totalMs = 0;
  let totalInput = 0;
  let totalOutput = 0;

  for (const test of TEST_CASES) {
    const start = Date.now();
    try {
      const res = await fetch(`${OPENROUTER_BASE_URL}/chat/completions`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${OPENROUTER_API_KEY}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: model.id,
          messages: [{ role: 'user', content: PROMPT(test.text) }],
          temperature: 0.1,
          max_tokens: 1000,
        }),
      });

      const ms = Date.now() - start;
      totalMs += ms;

      if (!res.ok) {
        const err = await res.text();
        console.log(`   ❌ ${test.name}: HTTP ${res.status} - ${err.slice(0, 80)}`);
        continue;
      }

      const data = (await res.json()) as any;
      const content = data.choices?.[0]?.message?.content || '';
      totalInput += data.usage?.prompt_tokens || 0;
      totalOutput += data.usage?.completion_tokens || 0;

      const json = extractJSON(content);
      if (json) {
        console.log(
          `   ✅ ${test.name}: ${json.entities.length} entities, ${json.relationships.length} rels (${ms}ms)`
        );
        passed++;
      } else {
        console.log(`   ❌ ${test.name}: Invalid JSON (${ms}ms)`);
      }
    } catch (err: any) {
      console.log(`   ❌ ${test.name}: ${err.message}`);
    }
    await new Promise((r) => setTimeout(r, 500));
  }

  const avgMs = Math.round(totalMs / TEST_CASES.length);
  const avgInput = Math.round(totalInput / TEST_CASES.length);
  const avgOutput = Math.round(totalOutput / TEST_CASES.length);
  const cost = ((avgInput / 1e6) * model.inputPrice + (avgOutput / 1e6) * model.outputPrice) * 1000;

  return {
    model: model.name,
    id: model.id,
    passRate: (passed / TEST_CASES.length) * 100,
    avgMs,
    cost,
    inputPrice: model.inputPrice,
    outputPrice: model.outputPrice,
  };
}

async function main() {
  console.log('═'.repeat(60));
  console.log('🧪 Grok Model Test (via OpenRouter)');
  console.log('═'.repeat(60));

  const results = [];
  for (const model of GROK_MODELS) {
    results.push(await testModel(model));
    await new Promise((r) => setTimeout(r, 1000));
  }

  console.log(`\n${'═'.repeat(80)}`);
  console.log('📊 GROK MODELS COMPARISON');
  console.log(`${'═'.repeat(80)}\n`);

  console.log(
    '| Model           | Pass Rate | Avg Time | Input $/M | Output $/M | Cost/1K Calls |'
  );
  console.log(
    '|-----------------|-----------|----------|-----------|------------|---------------|'
  );
  for (const r of results) {
    if (r.passRate > 0) {
      console.log(
        `| ${r.model.padEnd(15)} | ${r.passRate.toFixed(0).padStart(7)}% | ${(`${r.avgMs}ms`).padStart(8)} | $${r.inputPrice.toFixed(2).padStart(7)} | $${r.outputPrice.toFixed(2).padStart(8)} | $${r.cost.toFixed(4).padStart(11)} |`
      );
    } else {
      console.log(
        `| ${r.model.padEnd(15)} | FAILED    | -        | -         | -          | -             |`
      );
    }
  }

  await Bun.write(
    'grok-test-results.json',
    JSON.stringify({ results, timestamp: new Date().toISOString() }, null, 2)
  );
  console.log('\n📁 Results saved to grok-test-results.json');
}

main();
