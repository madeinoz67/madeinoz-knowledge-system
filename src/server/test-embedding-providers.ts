#!/usr/bin/env bun
/**
 * Test embedding models across multiple providers for cost vs performance
 * Evaluates: semantic quality, response time, dimensions, and cost
 *
 * Supported providers:
 * - OpenAI (direct API)
 * - Ollama (local, free)
 * - Together AI
 * - Voyage AI
 *
 * Usage:
 *   OPENAI_API_KEY=sk-... bun run test-embedding-providers.ts
 *   TOGETHER_API_KEY=... bun run test-embedding-providers.ts
 *   VOYAGE_API_KEY=... bun run test-embedding-providers.ts
 */

// API Keys from environment
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY;
const TOGETHER_API_KEY = process.env.TOGETHER_API_KEY;
const VOYAGE_API_KEY = process.env.VOYAGE_API_KEY;
const OLLAMA_HOST = process.env.OLLAMA_HOST || 'http://localhost:11434';

// Embedding models to test with pricing (per 1M tokens)
interface EmbeddingModel {
  id: string;
  name: string;
  provider: 'openai' | 'openrouter' | 'ollama' | 'together' | 'voyage';
  dimensions: number;
  price: number; // $ per 1M tokens
  apiKey?: string;
}

const EMBEDDING_MODELS: EmbeddingModel[] = [
  // OpenRouter models (OpenAI embeddings via OpenRouter - same pricing, works with OpenRouter API key)
  {
    id: 'openai/text-embedding-3-small',
    name: 'OR: Embed 3 Small',
    provider: 'openrouter',
    dimensions: 1536,
    price: 0.02,
  },
  {
    id: 'openai/text-embedding-3-large',
    name: 'OR: Embed 3 Large',
    provider: 'openrouter',
    dimensions: 3072,
    price: 0.13,
  },
  {
    id: 'openai/text-embedding-ada-002',
    name: 'OR: Ada 002',
    provider: 'openrouter',
    dimensions: 1536,
    price: 0.1,
  },

  // Direct OpenAI models (requires OPENAI_API_KEY)
  {
    id: 'text-embedding-3-small',
    name: 'OpenAI Embed 3 Small',
    provider: 'openai',
    dimensions: 1536,
    price: 0.02,
  },
  {
    id: 'text-embedding-3-large',
    name: 'OpenAI Embed 3 Large',
    provider: 'openai',
    dimensions: 3072,
    price: 0.13,
  },
  {
    id: 'text-embedding-ada-002',
    name: 'OpenAI Ada 002',
    provider: 'openai',
    dimensions: 1536,
    price: 0.1,
  },

  // Ollama models (free, local)
  {
    id: 'nomic-embed-text',
    name: 'Nomic Embed Text',
    provider: 'ollama',
    dimensions: 768,
    price: 0,
  },
  {
    id: 'mxbai-embed-large',
    name: 'MxBai Embed Large',
    provider: 'ollama',
    dimensions: 1024,
    price: 0,
  },
  { id: 'all-minilm', name: 'All-MiniLM', provider: 'ollama', dimensions: 384, price: 0 },
  {
    id: 'snowflake-arctic-embed',
    name: 'Snowflake Arctic',
    provider: 'ollama',
    dimensions: 1024,
    price: 0,
  },

  // Together AI models
  {
    id: 'BAAI/bge-large-en-v1.5',
    name: 'BGE Large EN',
    provider: 'together',
    dimensions: 1024,
    price: 0.016,
  },
  {
    id: 'BAAI/bge-base-en-v1.5',
    name: 'BGE Base EN',
    provider: 'together',
    dimensions: 768,
    price: 0.008,
  },
  {
    id: 'togethercomputer/m2-bert-80M-8k-retrieval',
    name: 'M2 BERT 80M',
    provider: 'together',
    dimensions: 768,
    price: 0.008,
  },

  // Voyage AI models
  { id: 'voyage-2', name: 'Voyage 2', provider: 'voyage', dimensions: 1024, price: 0.1 },
  {
    id: 'voyage-large-2',
    name: 'Voyage Large 2',
    provider: 'voyage',
    dimensions: 1536,
    price: 0.12,
  },
  { id: 'voyage-code-2', name: 'Voyage Code 2', provider: 'voyage', dimensions: 1536, price: 0.12 },
];

// Test pairs for semantic similarity evaluation
const TEST_PAIRS = [
  // Similar pairs (should have high similarity)
  {
    text1: 'The cat sat on the mat',
    text2: 'A feline rested on the rug',
    type: 'similar',
    label: 'Cat/Feline',
  },
  {
    text1: 'Alice is a software engineer',
    text2: 'Alice works as a developer',
    type: 'similar',
    label: 'Job titles',
  },
  {
    text1: 'The stock market crashed today',
    text2: 'Financial markets experienced a major decline',
    type: 'similar',
    label: 'Finance',
  },
  {
    text1: 'Machine learning models require training data',
    text2: 'AI systems need data to learn patterns',
    type: 'similar',
    label: 'ML/AI',
  },
  {
    text1: 'Neo4j is a graph database',
    text2: 'Graph databases store nodes and relationships',
    type: 'similar',
    label: 'Databases',
  },

  // Dissimilar pairs (should have low similarity)
  {
    text1: 'The weather is sunny today',
    text2: 'I love programming in TypeScript',
    type: 'dissimilar',
    label: 'Weather vs Code',
  },
  {
    text1: 'Pizza is delicious',
    text2: 'Quantum physics is complex',
    type: 'dissimilar',
    label: 'Food vs Physics',
  },
  {
    text1: 'The dog ran in the park',
    text2: 'Investment banking strategies',
    type: 'dissimilar',
    label: 'Pets vs Finance',
  },
];

interface EmbeddingResult {
  model: string;
  modelName: string;
  provider: string;
  dimensions: number;
  price: number;
  avgResponseMs: number;
  avgTokens: number;
  costPer1000Calls: number;
  qualityScore: number;
  similarityScores: { label: string; score: number; type: string }[];
  error?: string;
}

function cosineSimilarity(a: number[], b: number[]): number {
  if (a.length !== b.length) {
    throw new Error(`Dimension mismatch: ${a.length} vs ${b.length}`);
  }
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

async function getOpenAIEmbedding(
  model: string,
  text: string
): Promise<{ embedding: number[]; tokens: number; durationMs: number }> {
  if (!OPENAI_API_KEY) throw new Error('OPENAI_API_KEY not set');

  const start = Date.now();
  const response = await fetch('https://api.openai.com/v1/embeddings', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${OPENAI_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ model, input: text }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`OpenAI API error: ${response.status} ${error}`);
  }

  const data = (await response.json()) as any;
  return {
    embedding: data.data[0].embedding,
    tokens: data.usage?.total_tokens || 0,
    durationMs: Date.now() - start,
  };
}

async function getOllamaEmbedding(
  model: string,
  text: string
): Promise<{ embedding: number[]; tokens: number; durationMs: number }> {
  const start = Date.now();
  const response = await fetch(`${OLLAMA_HOST}/api/embeddings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model, prompt: text }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Ollama API error: ${response.status} ${error}`);
  }

  const data = (await response.json()) as any;
  return {
    embedding: data.embedding,
    tokens: text.split(/\s+/).length * 1.3, // Rough token estimate
    durationMs: Date.now() - start,
  };
}

async function getTogetherEmbedding(
  model: string,
  text: string
): Promise<{ embedding: number[]; tokens: number; durationMs: number }> {
  if (!TOGETHER_API_KEY) throw new Error('TOGETHER_API_KEY not set');

  const start = Date.now();
  const response = await fetch('https://api.together.xyz/v1/embeddings', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${TOGETHER_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ model, input: text }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Together API error: ${response.status} ${error}`);
  }

  const data = (await response.json()) as any;
  return {
    embedding: data.data[0].embedding,
    tokens: data.usage?.total_tokens || 0,
    durationMs: Date.now() - start,
  };
}

async function getVoyageEmbedding(
  model: string,
  text: string
): Promise<{ embedding: number[]; tokens: number; durationMs: number }> {
  if (!VOYAGE_API_KEY) throw new Error('VOYAGE_API_KEY not set');

  const start = Date.now();
  const response = await fetch('https://api.voyageai.com/v1/embeddings', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${VOYAGE_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ model, input: [text] }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Voyage API error: ${response.status} ${error}`);
  }

  const data = (await response.json()) as any;
  return {
    embedding: data.data[0].embedding,
    tokens: data.usage?.total_tokens || 0,
    durationMs: Date.now() - start,
  };
}

async function getOpenRouterEmbedding(
  model: string,
  text: string
): Promise<{ embedding: number[]; tokens: number; durationMs: number }> {
  if (!OPENROUTER_API_KEY) throw new Error('OPENROUTER_API_KEY not set');

  const start = Date.now();
  const response = await fetch('https://openrouter.ai/api/v1/embeddings', {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${OPENROUTER_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ model, input: text }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`OpenRouter API error: ${response.status} ${error}`);
  }

  const data = (await response.json()) as any;
  return {
    embedding: data.data[0].embedding,
    tokens: data.usage?.total_tokens || 0,
    durationMs: Date.now() - start,
  };
}

async function getEmbedding(model: EmbeddingModel, text: string) {
  switch (model.provider) {
    case 'openai':
      return getOpenAIEmbedding(model.id, text);
    case 'openrouter':
      return getOpenRouterEmbedding(model.id, text);
    case 'ollama':
      return getOllamaEmbedding(model.id, text);
    case 'together':
      return getTogetherEmbedding(model.id, text);
    case 'voyage':
      return getVoyageEmbedding(model.id, text);
    default:
      throw new Error(`Unknown provider: ${model.provider}`);
  }
}

function canTestModel(model: EmbeddingModel): boolean {
  switch (model.provider) {
    case 'openai':
      return !!OPENAI_API_KEY;
    case 'openrouter':
      return !!OPENROUTER_API_KEY;
    case 'ollama':
      return true; // Assume Ollama is running
    case 'together':
      return !!TOGETHER_API_KEY;
    case 'voyage':
      return !!VOYAGE_API_KEY;
    default:
      return false;
  }
}

async function testModel(model: EmbeddingModel): Promise<EmbeddingResult> {
  console.log(`\n🔄 Testing: ${model.name} (${model.provider})`);
  console.log(`   ${'─'.repeat(50)}`);

  if (!canTestModel(model)) {
    console.log(`   ⏭️  Skipped: No API key for ${model.provider}`);
    return {
      model: model.id,
      modelName: model.name,
      provider: model.provider,
      dimensions: model.dimensions,
      price: model.price,
      avgResponseMs: 0,
      avgTokens: 0,
      costPer1000Calls: 0,
      qualityScore: 0,
      similarityScores: [],
      error: `No API key for ${model.provider}`,
    };
  }

  try {
    const responseTimes: number[] = [];
    const tokenCounts: number[] = [];
    const similarityScores: EmbeddingResult['similarityScores'] = [];

    for (const pair of TEST_PAIRS) {
      const [emb1, emb2] = await Promise.all([
        getEmbedding(model, pair.text1),
        getEmbedding(model, pair.text2),
      ]);

      responseTimes.push(emb1.durationMs, emb2.durationMs);
      tokenCounts.push(emb1.tokens, emb2.tokens);

      const similarity = cosineSimilarity(emb1.embedding, emb2.embedding);
      similarityScores.push({ label: pair.label, score: similarity, type: pair.type });

      const icon =
        pair.type === 'similar' ? (similarity > 0.7 ? '✅' : '⚠️') : similarity < 0.5 ? '✅' : '⚠️';
      console.log(`   ${icon} ${pair.label}: ${(similarity * 100).toFixed(1)}% (${pair.type})`);

      // Rate limiting
      await new Promise((r) => setTimeout(r, 100));
    }

    const avgResponseMs = Math.round(
      responseTimes.reduce((a, b) => a + b, 0) / responseTimes.length
    );
    const avgTokens = Math.round(tokenCounts.reduce((a, b) => a + b, 0) / tokenCounts.length);

    // Quality score: high similarity for similar pairs, low for dissimilar
    const similarPairs = similarityScores.filter((s) => s.type === 'similar');
    const dissimilarPairs = similarityScores.filter((s) => s.type === 'dissimilar');

    const avgSimilar = similarPairs.reduce((a, s) => a + s.score, 0) / similarPairs.length;
    const avgDissimilar = dissimilarPairs.reduce((a, s) => a + s.score, 0) / dissimilarPairs.length;

    // Quality = (avg similar score) + (1 - avg dissimilar score) / 2
    const qualityScore = ((avgSimilar + (1 - avgDissimilar)) / 2) * 100;

    // Cost per 1000 calls (each call embeds ~20 tokens on average)
    const costPer1000Calls = (avgTokens / 1_000_000) * model.price * 1000;

    console.log(
      `   📊 Quality: ${qualityScore.toFixed(1)}%, Avg: ${avgResponseMs}ms, Cost: $${costPer1000Calls.toFixed(6)}/1K`
    );

    return {
      model: model.id,
      modelName: model.name,
      provider: model.provider,
      dimensions: model.dimensions,
      price: model.price,
      avgResponseMs,
      avgTokens,
      costPer1000Calls,
      qualityScore,
      similarityScores,
    };
  } catch (err: any) {
    console.log(`   ❌ Error: ${err.message}`);
    return {
      model: model.id,
      modelName: model.name,
      provider: model.provider,
      dimensions: model.dimensions,
      price: model.price,
      avgResponseMs: 0,
      avgTokens: 0,
      costPer1000Calls: 0,
      qualityScore: 0,
      similarityScores: [],
      error: err.message,
    };
  }
}

function printComparisonTable(results: EmbeddingResult[]) {
  console.log(`\n${'═'.repeat(130)}`);
  console.log('📊 EMBEDDING MODEL COMPARISON TABLE');
  console.log(`${'═'.repeat(130)}\n`);

  // Filter and sort by value (quality / cost, with free models ranked by quality)
  const validResults = results.filter((r) => !r.error);
  const sortedResults = [...validResults].sort((a, b) => {
    // Free models: sort by quality only
    if (a.price === 0 && b.price === 0) return b.qualityScore - a.qualityScore;
    if (a.price === 0) return -1; // Free models first
    if (b.price === 0) return 1;
    // Paid models: sort by value (quality/cost)
    const valueA =
      a.costPer1000Calls > 0 ? a.qualityScore / a.costPer1000Calls : Number.POSITIVE_INFINITY;
    const valueB =
      b.costPer1000Calls > 0 ? b.qualityScore / b.costPer1000Calls : Number.POSITIVE_INFINITY;
    return valueB - valueA;
  });

  console.log(
    '| Rank | Model                    | Provider | Dims  | Quality | Avg Time | $/1M Tokens | Cost/1K Calls | Value Score |'
  );
  console.log(
    '|------|--------------------------|----------|-------|---------|----------|-------------|---------------|-------------|'
  );

  sortedResults.forEach((r, i) => {
    const valueScore =
      r.price === 0
        ? 'FREE'
        : r.costPer1000Calls > 0
          ? (r.qualityScore / r.costPer1000Calls).toFixed(0)
          : '∞';
    const priceStr = r.price === 0 ? 'FREE' : `$${r.price.toFixed(3)}`;
    const costStr = r.price === 0 ? 'FREE' : `$${r.costPer1000Calls.toFixed(6)}`;

    console.log(
      `| ${(i + 1).toString().padStart(4)} | ${r.modelName.padEnd(24)} | ${r.provider.padEnd(8)} | ${r.dimensions.toString().padStart(5)} | ${r.qualityScore.toFixed(1).padStart(5)}% | ${(`${r.avgResponseMs}ms`).padStart(8)} | ${priceStr.padStart(11)} | ${costStr.padStart(13)} | ${valueScore.toString().padStart(11)} |`
    );
  });

  // Skipped/failed models
  const skipped = results.filter((r) => r.error);
  if (skipped.length > 0) {
    console.log('\n⏭️  Skipped Models:');
    skipped.forEach((r) => console.log(`   - ${r.modelName} (${r.provider}): ${r.error}`));
  }

  // Recommendations
  console.log(`\n${'─'.repeat(130)}`);
  console.log('📌 RECOMMENDATIONS FOR KNOWLEDGE SYSTEM');
  console.log('─'.repeat(130));

  const freeModels = sortedResults.filter((r) => r.price === 0);
  const paidModels = sortedResults.filter((r) => r.price > 0);

  if (freeModels.length > 0) {
    const bestFree = freeModels[0];
    console.log(
      `\n🆓 Best Free (Ollama):    ${bestFree.modelName} (${bestFree.qualityScore.toFixed(1)}% quality, ${bestFree.avgResponseMs}ms)`
    );
  }

  if (paidModels.length > 0) {
    const bestPaid = paidModels.reduce((a, b) => (a.qualityScore > b.qualityScore ? a : b));
    const bestValue = paidModels[0]; // Already sorted by value
    const cheapest = paidModels.reduce((a, b) => (a.costPer1000Calls < b.costPer1000Calls ? a : b));

    console.log(
      `🏆 Best Quality (Paid):   ${bestPaid.modelName} (${bestPaid.qualityScore.toFixed(1)}% quality)`
    );
    console.log(
      `💰 Best Value (Paid):     ${bestValue.modelName} ($${bestValue.costPer1000Calls.toFixed(6)}/1K at ${bestValue.qualityScore.toFixed(1)}%)`
    );
    console.log(
      `🪙 Cheapest (Paid):       ${cheapest.modelName} ($${cheapest.costPer1000Calls.toFixed(6)}/1K)`
    );
  }

  console.log('\n🎯 HYBRID RECOMMENDATION (Best for Knowledge System):');
  if (freeModels.length > 0) {
    console.log(`   Use Ollama ${freeModels[0].modelName} for embeddings - FREE and high quality!`);
  }
  if (paidModels.length > 0) {
    const recommended = paidModels.find((r) => r.qualityScore > 75) || paidModels[0];
    console.log(`   Cloud fallback: ${recommended.modelName} ($${recommended.price}/1M tokens)`);
  }
}

async function main() {
  console.log('═'.repeat(60));
  console.log('🧪 Embedding Model Comparison Test');
  console.log('═'.repeat(60));

  // Show available providers
  console.log('\n📋 Available API Keys:');
  console.log(
    `   OpenRouter: ${OPENROUTER_API_KEY ? '✅ Set' : '❌ Not set (OPENROUTER_API_KEY)'}`
  );
  console.log(`   OpenAI:     ${OPENAI_API_KEY ? '✅ Set' : '❌ Not set (OPENAI_API_KEY)'}`);
  console.log(`   Ollama:     ✅ Local (${OLLAMA_HOST})`);
  console.log(`   Together:   ${TOGETHER_API_KEY ? '✅ Set' : '❌ Not set (TOGETHER_API_KEY)'}`);
  console.log(`   Voyage:     ${VOYAGE_API_KEY ? '✅ Set' : '❌ Not set (VOYAGE_API_KEY)'}`);

  console.log(`\n📊 Testing ${EMBEDDING_MODELS.length} embedding models...`);

  const results: EmbeddingResult[] = [];

  for (const model of EMBEDDING_MODELS) {
    const result = await testModel(model);
    results.push(result);

    // Rate limiting between models
    await new Promise((r) => setTimeout(r, 500));
  }

  // Print comparison table
  printComparisonTable(results);

  // Save results
  const outputPath = new URL('./embedding-provider-results.json', import.meta.url).pathname;
  await Bun.write(
    outputPath,
    JSON.stringify(
      {
        results,
        timestamp: new Date().toISOString(),
        testPairs: TEST_PAIRS.length,
        apiKeysAvailable: {
          openrouter: !!OPENROUTER_API_KEY,
          openai: !!OPENAI_API_KEY,
          ollama: true,
          together: !!TOGETHER_API_KEY,
          voyage: !!VOYAGE_API_KEY,
        },
      },
      null,
      2
    )
  );
  console.log(`\n📁 Results saved to: ${outputPath}`);
}

main().catch(console.error);
