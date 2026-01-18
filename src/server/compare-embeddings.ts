#!/usr/bin/env bun
/**
 * Compare Ollama mxbai-embed-large vs OpenAI text-embedding-3-small
 */

const OLLAMA_HOST = "http://10.0.0.150:11434";
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;

// Test sentences for semantic similarity
const TEST_PAIRS = [
  { a: "The cat sat on the mat", b: "A feline rested on the rug", label: "Cat/Feline synonyms", expected: "high" },
  { a: "Alice is a software engineer", b: "Alice works as a developer", label: "Job title synonyms", expected: "high" },
  { a: "The weather is sunny today", b: "I love programming in TypeScript", label: "Weather vs Programming", expected: "low" },
  { a: "Machine learning is a subset of AI", b: "Deep learning uses neural networks", label: "ML/DL related", expected: "high" },
  { a: "Paris is the capital of France", b: "Tokyo is in Japan", label: "Different countries", expected: "medium" },
  { a: "The stock market crashed yesterday", b: "My favorite color is blue", label: "Finance vs Personal", expected: "low" },
];

function cosineSimilarity(a: number[], b: number[]): number {
  let dotProduct = 0, normA = 0, normB = 0;
  for (let i = 0; i < a.length; i++) {
    dotProduct += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  return dotProduct / (Math.sqrt(normA) * Math.sqrt(normB));
}

async function getOllamaEmbedding(text: string): Promise<{ embedding: number[]; ms: number }> {
  const start = Date.now();
  const res = await fetch(`${OLLAMA_HOST}/api/embeddings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ model: "mxbai-embed-large", prompt: text }),
  });
  const data = await res.json() as { embedding: number[] };
  return { embedding: data.embedding, ms: Date.now() - start };
}

async function getOpenAIEmbedding(text: string): Promise<{ embedding: number[]; ms: number }> {
  const start = Date.now();
  const res = await fetch("https://api.openai.com/v1/embeddings", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${OPENAI_API_KEY}`,
    },
    body: JSON.stringify({ model: "text-embedding-3-small", input: text }),
  });
  const data = await res.json() as { data: { embedding: number[] }[] };
  return { embedding: data.data[0].embedding, ms: Date.now() - start };
}

async function main() {
  if (!OPENAI_API_KEY) {
    console.error("OPENAI_API_KEY not set");
    process.exit(1);
  }

  console.log("==============================================");
  console.log("Embedding Model Comparison");
  console.log("Ollama mxbai-embed-large vs OpenAI text-embedding-3-small");
  console.log("==============================================\n");

  // Get dimensions
  const ollamaTest = await getOllamaEmbedding("test");
  const openaiTest = await getOpenAIEmbedding("test");

  console.log(`Ollama mxbai-embed-large: ${ollamaTest.embedding.length} dimensions`);
  console.log(`OpenAI text-embedding-3-small: ${openaiTest.embedding.length} dimensions\n`);

  console.log("| Test Case | Expected | Ollama | OpenAI | Winner |");
  console.log("|-----------|----------|--------|--------|--------|");

  let ollamaTotalTime = 0, openaiTotalTime = 0;
  let ollamaScore = 0, openaiScore = 0;

  for (const pair of TEST_PAIRS) {
    // Get embeddings
    const [ollamaA, ollamaB] = await Promise.all([
      getOllamaEmbedding(pair.a),
      getOllamaEmbedding(pair.b),
    ]);
    const [openaiA, openaiB] = await Promise.all([
      getOpenAIEmbedding(pair.a),
      getOpenAIEmbedding(pair.b),
    ]);

    ollamaTotalTime += ollamaA.ms + ollamaB.ms;
    openaiTotalTime += openaiA.ms + openaiB.ms;

    const ollamaSim = cosineSimilarity(ollamaA.embedding, ollamaB.embedding);
    const openaiSim = cosineSimilarity(openaiA.embedding, openaiB.embedding);

    // Score based on expected result
    let winner = "Tie";
    if (pair.expected === "high") {
      // Higher similarity is better
      if (ollamaSim > openaiSim + 0.05) { winner = "Ollama"; ollamaScore++; }
      else if (openaiSim > ollamaSim + 0.05) { winner = "OpenAI"; openaiScore++; }
    } else if (pair.expected === "low") {
      // Lower similarity is better (more discriminating)
      if (ollamaSim < openaiSim - 0.05) { winner = "Ollama"; ollamaScore++; }
      else if (openaiSim < ollamaSim - 0.05) { winner = "OpenAI"; openaiScore++; }
    }

    console.log(`| ${pair.label.padEnd(25)} | ${pair.expected.padEnd(8)} | ${(ollamaSim * 100).toFixed(1)}% | ${(openaiSim * 100).toFixed(1)}% | ${winner} |`);
  }

  console.log("\n==============================================");
  console.log("SUMMARY");
  console.log("==============================================\n");

  console.log(`| Metric | Ollama mxbai | OpenAI small |`);
  console.log(`|--------|--------------|--------------|`);
  console.log(`| Dimensions | ${ollamaTest.embedding.length} | ${openaiTest.embedding.length} |`);
  console.log(`| Avg response | ${Math.round(ollamaTotalTime / (TEST_PAIRS.length * 2))}ms | ${Math.round(openaiTotalTime / (TEST_PAIRS.length * 2))}ms |`);
  console.log(`| Test wins | ${ollamaScore} | ${openaiScore} |`);
  console.log(`| Cost | Free | ~$0.02/1M tokens |`);

  console.log(`\n🏆 ${ollamaScore > openaiScore ? "Ollama mxbai-embed-large" : ollamaScore < openaiScore ? "OpenAI text-embedding-3-small" : "Tie"} wins on quality`);
  console.log(`💰 Ollama is FREE vs OpenAI's paid API`);
}

main();
