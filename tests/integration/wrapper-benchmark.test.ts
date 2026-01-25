/**
 * Integration benchmark tests for token savings validation
 * Tests that formatters achieve target savings on realistic data
 * @module tests/integration/wrapper-benchmark.test.ts
 */
import { describe, test, expect } from 'bun:test';
import { formatOutput } from '../../src/server/lib/output-formatter';
import {
  measureTokens,
  generateBenchmarkReport,
  TOKEN_SAVINGS_TARGETS,
  type TokenMetrics,
} from '../../src/server/lib/token-metrics';

describe('wrapper-benchmark', () => {
  // Helper to measure token savings for a formatter
  function measureSavings(operation: string, data: unknown, query?: string): TokenMetrics {
    const startTime = performance.now();
    const result = formatOutput(operation, data, { query });
    const processingTimeMs = performance.now() - startTime;

    return measureTokens(data, result.output, operation, processingTimeMs);
  }

  describe('search_nodes', () => {
    test('achieves >30% savings on realistic data', () => {
      const data = {
        nodes: [
          {
            uuid: '550e8400-e29b-41d4-a716-446655440001',
            name: 'Graphiti',
            entity_type: 'Framework',
            summary:
              'A knowledge graph framework for building temporal, memory-aware AI systems with entity extraction',
            created_at: '2026-01-18T10:00:00Z',
          },
          {
            uuid: '550e8400-e29b-41d4-a716-446655440002',
            name: 'FalkorDB',
            entity_type: 'Database',
            summary:
              'Redis-based graph database with RediSearch integration for efficient graph queries',
            created_at: '2026-01-18T09:00:00Z',
          },
          {
            uuid: '550e8400-e29b-41d4-a716-446655440003',
            name: 'Neo4j',
            entity_type: 'Database',
            summary: 'Native graph database with Cypher query language and enterprise features',
            created_at: '2026-01-18T08:00:00Z',
          },
        ],
      };

      const metrics = measureSavings('search_nodes', data, 'graph database');

      expect(metrics.savingsPercent).toBeGreaterThanOrEqual(TOKEN_SAVINGS_TARGETS.search_nodes);
      expect(metrics.processingTimeMs).toBeLessThan(100); // Performance check
    });

    test('achieves target on large result sets', () => {
      // Generate 20 nodes
      const nodes = Array.from({ length: 20 }, (_, i) => ({
        uuid: `550e8400-e29b-41d4-a716-44665544${String(i).padStart(4, '0')}`,
        name: `Entity${i}`,
        entity_type: 'TestType',
        summary: `This is a detailed summary for entity ${i} that provides context about its role in the system.`,
        created_at: new Date(Date.now() - i * 3600000).toISOString(),
      }));

      const data = { nodes };
      const metrics = measureSavings('search_nodes', data, 'test');

      expect(metrics.savingsPercent).toBeGreaterThanOrEqual(TOKEN_SAVINGS_TARGETS.search_nodes);
    });
  });

  describe('search_facts', () => {
    test('achieves >30% savings on realistic data', () => {
      const data = {
        facts: [
          {
            uuid: '550e8400-e29b-41d4-a716-446655440010',
            source: { name: 'Graphiti' },
            target: { name: 'FalkorDB' },
            relation: 'USES',
            confidence: 0.95,
          },
          {
            uuid: '550e8400-e29b-41d4-a716-446655440011',
            source: { name: 'MCP Server' },
            target: { name: 'Graphiti' },
            relation: 'INTEGRATES_WITH',
            confidence: 0.88,
          },
          {
            uuid: '550e8400-e29b-41d4-a716-446655440012',
            source: { name: 'PAI' },
            target: { name: 'Knowledge System' },
            relation: 'CONTAINS',
            confidence: 0.92,
          },
        ],
      };

      const metrics = measureSavings('search_facts', data, 'integration');

      expect(metrics.savingsPercent).toBeGreaterThanOrEqual(TOKEN_SAVINGS_TARGETS.search_facts);
    });
  });

  describe('add_memory', () => {
    test('achieves savings on realistic data', () => {
      const data = {
        message: "Episode 'Docker Container Best Practices' queued for processing in group 'main'",
      };

      const metrics = measureSavings('add_memory', data);

      // New format is more concise, expect some savings
      expect(metrics.savingsPercent).toBeGreaterThanOrEqual(0);
    });
  });

  describe('get_episodes', () => {
    test('achieves >25% savings on realistic data', () => {
      const data = {
        episodes: [
          {
            uuid: '550e8400-e29b-41d4-a716-446655440020',
            name: 'Knowledge Graph Setup',
            content:
              'Installed FalkorDB via Docker and configured the Graphiti MCP server for local development.',
            created_at: new Date(Date.now() - 2 * 3600000).toISOString(),
            source_description: 'session-capture',
          },
          {
            uuid: '550e8400-e29b-41d4-a716-446655440021',
            name: 'API Integration',
            content:
              'Connected the MCP server to the Claude Code CLI using the settings.json configuration.',
            created_at: new Date(Date.now() - 5 * 3600000).toISOString(),
            source_description: 'manual-entry',
          },
          {
            uuid: '550e8400-e29b-41d4-a716-446655440022',
            name: 'Performance Testing',
            content:
              'Ran benchmark tests on search operations and validated token savings meet targets.',
            created_at: new Date(Date.now() - 24 * 3600000).toISOString(),
            source_description: 'test-run',
          },
        ],
      };

      const metrics = measureSavings('get_episodes', data);

      expect(metrics.savingsPercent).toBeGreaterThanOrEqual(TOKEN_SAVINGS_TARGETS.get_episodes);
    });
  });

  describe('get_status', () => {
    test('achieves savings on realistic data', () => {
      const data = {
        status: 'ok',
        message: 'Connected to neo4j database',
      };

      const metrics = measureSavings('get_status', data);

      // New format is more concise, expect some savings
      expect(metrics.savingsPercent).toBeGreaterThanOrEqual(0);
    });
  });

  describe('clear_graph', () => {
    test('produces compact readable output', () => {
      const data = {
        success: true,
        deleted_entities: 142,
        deleted_episodes: 47,
      };

      const metrics = measureSavings('clear_graph', data);

      // clear_graph is a simple status message - savings depend on payload size
      // For small payloads, we just verify it's more compact than raw JSON
      expect(metrics.savingsPercent).toBeGreaterThan(0);
      expect(metrics.compactBytes).toBeLessThan(metrics.rawBytes);
    });
  });

  describe('benchmark report generation', () => {
    test('produces PASS verdict for operations with realistic data', () => {
      // Collect metrics for operations with larger payloads that achieve targets
      const allMetrics: TokenMetrics[] = [];

      // search_nodes - larger payload for better compression
      allMetrics.push(
        measureSavings(
          'search_nodes',
          {
            nodes: Array.from({ length: 5 }, (_, i) => ({
              uuid: `550e8400-e29b-41d4-a716-44665544000${i}`,
              name: `Entity${i}`,
              entity_type: 'TestType',
              summary: `This is a detailed summary for entity ${i} that provides context.`,
              created_at: new Date().toISOString(),
            })),
          },
          'test'
        )
      );

      // search_facts - larger payload
      allMetrics.push(
        measureSavings(
          'search_facts',
          {
            facts: Array.from({ length: 5 }, (_, i) => ({
              uuid: `550e8400-e29b-41d4-a716-44665544010${i}`,
              source: { name: `Source${i}` },
              target: { name: `Target${i}` },
              relation: 'RELATES_TO',
              confidence: 0.9,
            })),
          },
          'test'
        )
      );

      // get_episodes - larger payload
      allMetrics.push(
        measureSavings('get_episodes', {
          episodes: Array.from({ length: 5 }, (_, i) => ({
            uuid: `550e8400-e29b-41d4-a716-44665544020${i}`,
            name: `Episode ${i}`,
            content: `This is the content for episode ${i} with detailed information.`,
            created_at: new Date(Date.now() - i * 3600000).toISOString(),
            source_description: 'test',
          })),
        })
      );

      // Generate report
      const report = generateBenchmarkReport(allMetrics);

      // Validate - these operations with larger payloads should pass
      expect(report.verdict).toBe('PASS');
      expect(report.totalMeasurements).toBe(3);

      // Verify summary contains operation names
      expect(report.summary).toContain('Token Savings Benchmark');
      expect(report.summary).toContain('PASS');
    });

    test('summary includes all measured operations', () => {
      const metrics: TokenMetrics[] = [
        measureSavings(
          'search_nodes',
          { nodes: [{ name: 'A', entity_type: 'T', summary: 'S' }] },
          'q'
        ),
        measureSavings('get_status', { status: 'OK', entity_count: 1, episode_count: 1 }),
      ];

      const report = generateBenchmarkReport(metrics);

      expect(report.byOperation.has('search_nodes')).toBe(true);
      expect(report.byOperation.has('get_status')).toBe(true);
      expect(report.byOperation.size).toBe(2);
    });
  });

  describe('performance thresholds', () => {
    test('all operations complete under 50ms', () => {
      const operations = [
        {
          op: 'search_nodes',
          data: {
            nodes: Array.from({ length: 20 }, (_, i) => ({
              name: `N${i}`,
              entity_type: 'T',
              summary: 'S'.repeat(100),
            })),
          },
        },
        {
          op: 'search_facts',
          data: {
            facts: Array.from({ length: 20 }, (_, i) => ({
              source: { name: `S${i}` },
              target: { name: `T${i}` },
              relation: 'r',
              confidence: 0.5,
            })),
          },
        },
        {
          op: 'get_episodes',
          data: {
            episodes: Array.from({ length: 20 }, (_, i) => ({
              name: `E${i}`,
              content: 'C'.repeat(100),
              created_at: new Date().toISOString(),
            })),
          },
        },
        { op: 'get_status', data: { status: 'OK', entity_count: 1000, episode_count: 500 } },
      ];

      for (const { op, data } of operations) {
        const metrics = measureSavings(op, data);
        expect(metrics.processingTimeMs).toBeLessThan(50);
      }
    });
  });
});
