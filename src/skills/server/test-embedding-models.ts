#!/usr/bin/env bun
/**
 * Test Ollama embedding models for quality and performance
 * Evaluates: response time, dimensions, and semantic similarity
 */

const OLLAMA_HOST = 'http://10.0.0.150:11434';

const EMBEDDING_MODELS = [
  'nomic-embed-text:latest',
  'nomic-embed-text-v2-moe:latest',
  'mxbai-embed-large:latest',
  'qwen3-embedding:0.6b',
  'embeddinggemma:latest',
];

// Test sentences for semantic similarity
const TEST_PAIRS = [
  {
    similar: ['The cat sat on the mat', 'A feline rested on the rug'],
    label: 'Cat/Feline synonyms',
  },
  {
    similar: ['Alice is a software engineer', 'Alice works as a developer'],
    label: 'Job title synonyms',
  },
  {
    dissimilar: ['The weather is sunny today', 'I love programming in TypeScript'],
    label: 'Weather vs Programming',
  },
];

interface EmbeddingResult {
  model: string;
  dimensions: number;
  avgResponseMs: number;
  similarityScores: { label: string; score: number; type: 'similar' | 'dissimilar' }[];
  error?: string;
}

function cosineSimilarity(a: number[], b: number[]): number {
  let dotProduct = 0;
  let normA = 0;
  let normB = 0;
  for (let i = 0; i < a.length; i++) {
    dotProduct += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
}

async function getEmbedding(
  model: string,
  text: string
): Promise<{ embedding: number[]; durationMs: number }> {
  const start = Date.now();
  const res = await fetch(`${OLLAMA_HOST}/api/embeddings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model, prompt: text }),
  });

  if (!res.ok) {
    throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  }

  const data = (await res.json()) as { embedding: number[] };
  return { embedding: data.embedding, durationMs: Date.now() - start };
}

async function testModel(model: string): Promise<EmbeddingResult> {
  console.log(`\nTesting: ${model}`);
  console.log('---');

  try {
    // Test basic embedding
    const { embedding, durationMs } = await getEmbedding(model, 'Hello world test');
    console.log(`  Dimensions: ${embedding.length}`);
    console.log(`  First call: ${durationMs}ms`);

    // Test multiple calls for average time
    const times: number[] = [durationMs];
    for (let i = 0; i < 3; i++) {
      const { durationMs: t } = await getEmbedding(model, `Test sentence number ${i}`);
      times.push(t);
    }
    const avgTime = Math.round(times.reduce((a, b) => a + b, 0) / times.length);
    console.log(`  Avg response: ${avgTime}ms`);

    // Test semantic similarity
    const similarityScores: EmbeddingResult['similarityScores'] = [];

    for (const pair of TEST_PAIRS) {
      if (pair.similar) {
        const [emb1, emb2] = await Promise.all([
          getEmbedding(model, pair.similar[0]),
          getEmbedding(model, pair.similar[1]),
        ]);
        const score = cosineSimilarity(emb1.embedding, emb2.embedding);
        similarityScores.push({ label: pair.label, score, type: 'similar' });
        console.log(`  Similar "${pair.label}": ${(score * 100).toFixed(1)}%`);
      }
      if (pair.dissimilar) {
        const [emb1, emb2] = await Promise.all([
          getEmbedding(model, pair.dissimilar[0]),
          getEmbedding(model, pair.dissimilar[1]),
        ]);
        const score = cosineSimilarity(emb1.embedding, emb2.embedding);
        similarityScores.push({ label: pair.label, score, type: 'dissimilar' });
        console.log(`  Dissimilar "${pair.label}": ${(score * 100).toFixed(1)}%`);
      }
    }

    return {
      model,
      dimensions: embedding.length,
      avgResponseMs: avgTime,
      similarityScores,
    };
  } catch (err: any) {
    console.log(`  ❌ Error: ${err.message}`);
    return {
      model,
      dimensions: 0,
      avgResponseMs: 0,
      similarityScores: [],
      error: err.message,
    };
  }
}

function calculateQualityScore(result: EmbeddingResult): number {
  if (result.error) return 0;

  // Quality = high similarity for similar pairs + low similarity for dissimilar pairs
  let score = 0;
  for (const s of result.similarityScores) {
    if (s.type === 'similar') {
      score += s.score; // Higher is better
    } else {
      score += 1 - s.score; // Lower similarity is better for dissimilar
    }
  }
  return score / result.similarityScores.length;
}

async function main() {
  console.log('==============================================');
  console.log('Ollama Embedding Model Performance Test');
  console.log(`Testing ${EMBEDDING_MODELS.length} models`);
  console.log('==============================================');

  const results: EmbeddingResult[] = [];

  for (const model of EMBEDDING_MODELS) {
    const result = await testModel(model);
    results.push(result);
  }

  // Sort by quality score
  const validResults = results.filter((r) => !r.error);
  validResults.sort((a, b) => calculateQualityScore(b) - calculateQualityScore(a));

  console.log('\n==============================================');
  console.log('RESULTS SUMMARY (ranked by quality)');
  console.log('==============================================\n');

  console.log('| Rank | Model | Dims | Avg Time | Quality Score |');
  console.log('|------|-------|------|----------|---------------|');

  validResults.forEach((r, i) => {
    const quality = (calculateQualityScore(r) * 100).toFixed(1);
    console.log(`| ${i + 1} | ${r.model} | ${r.dimensions} | ${r.avgResponseMs}ms | ${quality}% |`);
  });

  const failed = results.filter((r) => r.error);
  if (failed.length > 0) {
    console.log('\n❌ Failed models:');
    failed.forEach((r) => console.log(`   - ${r.model}: ${r.error}`));
  }

  // Recommend best model
  if (validResults.length > 0) {
    const best = validResults[0];
    console.log(`\n🏆 RECOMMENDED: ${best.model}`);
    console.log(`   - Dimensions: ${best.dimensions}`);
    console.log(`   - Avg response: ${best.avgResponseMs}ms`);
    console.log(`   - Quality score: ${(calculateQualityScore(best) * 100).toFixed(1)}%`);
  }

  // Output JSON
  const outputPath = new URL('./embedding-test-results.json', import.meta.url).pathname;
  await Bun.write(
    outputPath,
    JSON.stringify({ results, timestamp: new Date().toISOString() }, null, 2)
  );
  console.log(`\nResults saved to: ${outputPath}`);
}

main();
