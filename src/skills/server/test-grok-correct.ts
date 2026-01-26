#!/usr/bin/env bun
const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY;

const GROK_MODELS = [
  { id: 'x-ai/grok-4.1-fast', name: 'Grok 4.1 Fast', inputPrice: 0.2, outputPrice: 0.5 },
  { id: 'x-ai/grok-4-fast', name: 'Grok 4 Fast', inputPrice: 0.2, outputPrice: 0.5 },
  { id: 'x-ai/grok-4', name: 'Grok 4', inputPrice: 3.0, outputPrice: 15.0 },
  { id: 'x-ai/grok-3-mini', name: 'Grok 3 Mini', inputPrice: 0.3, outputPrice: 0.5 },
  { id: 'x-ai/grok-3', name: 'Grok 3', inputPrice: 3.0, outputPrice: 15.0 },
];

const TEST_CASES = [
  {
    name: 'Basic',
    text: 'John Smith works at Acme Corp in New York. He met Sarah Jones yesterday.',
  },
  {
    name: 'Technical',
    text: 'The PAI system uses Neo4j for graph storage. It was created by Daniel Miessler.',
  },
  {
    name: 'Complex',
    text: 'Alice, the CTO of TechStart, acquired DataFlow Inc. Bob now reports to Alice.',
  },
];

const PROMPT = (text: string) => `Extract entities and relationships. Return ONLY valid JSON.
Text: "${text}"
Format: {"entities": [{"name": "string", "type": "PERSON|ORG|LOCATION"}], "relationships": [{"source": "string", "target": "string", "type": "string"}]}`;

function extractJSON(text: string): any {
  const clean = text
    .replace(/```json\n?/g, '')
    .replace(/```\n?/g, '')
    .trim();
  try {
    const obj = JSON.parse(clean);
    if (obj.entities) return obj;
  } catch {}
  const match = clean.match(/\{[\s\S]*"entities"[\s\S]*\}/);
  if (match)
    try {
      return JSON.parse(match[0]);
    } catch {}
  return null;
}

async function testModel(model: (typeof GROK_MODELS)[0]) {
  console.log(`\n🔄 ${model.name} (${model.id})`);
  let passed = 0;
  let totalMs = 0;
  let totalIn = 0;
  let totalOut = 0;

  for (const test of TEST_CASES) {
    const start = Date.now();
    try {
      const res = await fetch('https://openrouter.ai/api/v1/chat/completions', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${OPENROUTER_API_KEY}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          model: model.id,
          messages: [{ role: 'user', content: PROMPT(test.text) }],
          temperature: 0.1,
          max_tokens: 500,
        }),
      });
      const ms = Date.now() - start;
      totalMs += ms;
      if (!res.ok) {
        console.log(`   ❌ ${test.name}: HTTP ${res.status}`);
        continue;
      }
      const data = (await res.json()) as any;
      totalIn += data.usage?.prompt_tokens || 0;
      totalOut += data.usage?.completion_tokens || 0;
      const json = extractJSON(data.choices?.[0]?.message?.content || '');
      if (json) {
        console.log(`   ✅ ${test.name}: ${json.entities?.length || 0} entities (${ms}ms)`);
        passed++;
      } else {
        console.log(`   ❌ ${test.name}: Invalid JSON`);
      }
    } catch (e: any) {
      console.log(`   ❌ ${test.name}: ${e.message}`);
    }
    await new Promise((r) => setTimeout(r, 500));
  }

  const avgIn = totalIn / TEST_CASES.length;
  const avgOut = totalOut / TEST_CASES.length;
  const cost = ((avgIn / 1e6) * model.inputPrice + (avgOut / 1e6) * model.outputPrice) * 1000;
  return {
    name: model.name,
    passRate: (passed / TEST_CASES.length) * 100,
    avgMs: Math.round(totalMs / TEST_CASES.length),
    cost,
    inputPrice: model.inputPrice,
    outputPrice: model.outputPrice,
  };
}

async function main() {
  console.log('═'.repeat(60));
  console.log('🧪 Grok Models Test (Correct IDs)');
  console.log('═'.repeat(60));

  const results = [];
  for (const m of GROK_MODELS) {
    results.push(await testModel(m));
    await new Promise((r) => setTimeout(r, 1000));
  }

  console.log(`\n${'═'.repeat(90)}`);
  console.log('📊 GROK MODELS COMPARISON');
  console.log(`${'═'.repeat(90)}\n`);
  console.log(
    '| Model            | Pass Rate | Avg Time | Input $/M | Output $/M | Cost/1K Calls |'
  );
  console.log(
    '|------------------|-----------|----------|-----------|------------|---------------|'
  );
  for (const r of results) {
    if (r.passRate > 0)
      console.log(
        `| ${r.name.padEnd(16)} | ${r.passRate.toFixed(0).padStart(7)}% | ${(`${r.avgMs}ms`).padStart(8)} | $${r.inputPrice.toFixed(2).padStart(7)} | $${r.outputPrice.toFixed(2).padStart(8)} | $${r.cost.toFixed(4).padStart(11)} |`
      );
    else
      console.log(
        `| ${r.name.padEnd(16)} | FAILED    | -        | -         | -          | -             |`
      );
  }
  await Bun.write(
    'grok-results.json',
    JSON.stringify({ results, timestamp: new Date().toISOString() }, null, 2)
  );
}
main();
