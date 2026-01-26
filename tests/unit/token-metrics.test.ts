/**
 * Unit tests for token-metrics.ts
 * @module tests/unit/token-metrics.test.ts
 */
import { describe, test, expect, beforeEach, afterEach } from 'bun:test';
import { mkdir, rm, readFile, writeFile } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import {
  measureTokens,
  estimateTokens,
  formatMetricsReport,
  appendMetrics,
  loadMetrics,
  aggregateMetrics,
  generateBenchmarkReport,
  TOKEN_SAVINGS_TARGETS,
  type TokenMetrics,
  type AggregateStats,
} from '../../src/skills/server/lib/token-metrics';

describe('token-metrics', () => {
  // T032: Unit test for measureTokens
  describe('measureTokens', () => {
    test('should calculate byte savings correctly', () => {
      const rawData = { nodes: [{ name: 'Test', type: 'Entity', summary: 'A test entity' }] };
      const compactOutput = '1. Test [Entity] - A test entity';

      const metrics = measureTokens(rawData, compactOutput, 'search_nodes', 5);

      expect(metrics.rawBytes).toBeGreaterThan(0);
      expect(metrics.compactBytes).toBeGreaterThan(0);
      expect(metrics.rawBytes).toBeGreaterThan(metrics.compactBytes);
    });

    test('should estimate tokens using chars/4', () => {
      const rawData = { status: 'OK' };
      const compactOutput = 'Status: OK';

      const metrics = measureTokens(rawData, compactOutput, 'get_status', 2);

      // Raw JSON is larger than compact output
      const rawJson = JSON.stringify(rawData, null, 2);
      expect(metrics.estimatedTokensBefore).toBe(Math.ceil(rawJson.length / 4));
      expect(metrics.estimatedTokensAfter).toBe(Math.ceil(compactOutput.length / 4));
    });

    test('should record processing time', () => {
      const metrics = measureTokens({ test: true }, 'test', 'test_op', 42);

      expect(metrics.processingTimeMs).toBe(42);
    });

    test('should calculate savings percentage', () => {
      const rawData = { longField: 'x'.repeat(100) };
      const compactOutput = 'Short';

      const metrics = measureTokens(rawData, compactOutput, 'test_op', 1);

      expect(metrics.savingsPercent).toBeGreaterThan(0);
      expect(metrics.savingsPercent).toBeLessThanOrEqual(100);
    });

    test('should set operation and timestamp', () => {
      const before = new Date();
      const metrics = measureTokens({}, '', 'my_operation', 0);
      const after = new Date();

      expect(metrics.operation).toBe('my_operation');
      expect(metrics.timestamp.getTime()).toBeGreaterThanOrEqual(before.getTime());
      expect(metrics.timestamp.getTime()).toBeLessThanOrEqual(after.getTime());
    });

    test('should handle empty compact output (0% savings edge case)', () => {
      const rawData = {};
      const compactOutput = '{}'; // Same as JSON.stringify({})

      const metrics = measureTokens(rawData, compactOutput, 'test_op', 0);

      // When compact is same size or larger, savings should be 0 or negative
      expect(metrics.savingsPercent).toBeDefined();
    });
  });

  // T033: Unit test for estimateTokens
  describe('estimateTokens', () => {
    test('should return chars/4 rounded up', () => {
      expect(estimateTokens('1234')).toBe(1); // 4/4 = 1
      expect(estimateTokens('12345')).toBe(2); // 5/4 = 1.25 → 2
      expect(estimateTokens('12345678')).toBe(2); // 8/4 = 2
      expect(estimateTokens('123456789')).toBe(3); // 9/4 = 2.25 → 3
    });

    test('should handle empty string', () => {
      expect(estimateTokens('')).toBe(0);
    });

    test('should handle long text', () => {
      const text = 'a'.repeat(1000);
      expect(estimateTokens(text)).toBe(250); // 1000/4 = 250
    });

    test('should handle unicode characters', () => {
      const text = '你好世界'; // 4 Chinese characters
      // Each Chinese character is 3 bytes in UTF-8 but we count chars
      expect(estimateTokens(text)).toBe(1); // 4/4 = 1
    });
  });

  // T034: Unit test for formatMetricsReport
  describe('formatMetricsReport', () => {
    test('should format human-readable report', () => {
      const metrics: TokenMetrics = {
        operation: 'search_nodes',
        timestamp: new Date('2026-01-18T12:00:00Z'),
        rawBytes: 1247,
        compactBytes: 298,
        savingsPercent: 76.1,
        estimatedTokensBefore: 312,
        estimatedTokensAfter: 75,
        processingTimeMs: 8,
      };

      const report = formatMetricsReport(metrics);

      expect(report).toContain('Token Metrics');
      expect(report).toContain('search_nodes');
      expect(report).toContain('1,247');
      expect(report).toContain('298');
      expect(report).toContain('76.1%');
      expect(report).toContain('8ms');
    });

    test('should include estimated tokens', () => {
      const metrics: TokenMetrics = {
        operation: 'get_status',
        timestamp: new Date(),
        rawBytes: 400,
        compactBytes: 100,
        savingsPercent: 75,
        estimatedTokensBefore: 100,
        estimatedTokensAfter: 25,
        processingTimeMs: 2,
      };

      const report = formatMetricsReport(metrics);

      expect(report).toContain('100');
      expect(report).toContain('25');
      expect(report).toContain('tokens saved');
    });
  });

  // T035: Unit test for aggregateMetrics
  describe('aggregateMetrics', () => {
    const sampleMetrics: TokenMetrics[] = [
      {
        operation: 'search_nodes',
        timestamp: new Date(),
        rawBytes: 1000,
        compactBytes: 300,
        savingsPercent: 70,
        estimatedTokensBefore: 250,
        estimatedTokensAfter: 75,
        processingTimeMs: 5,
      },
      {
        operation: 'search_nodes',
        timestamp: new Date(),
        rawBytes: 800,
        compactBytes: 200,
        savingsPercent: 75,
        estimatedTokensBefore: 200,
        estimatedTokensAfter: 50,
        processingTimeMs: 3,
      },
      {
        operation: 'get_status',
        timestamp: new Date(),
        rawBytes: 500,
        compactBytes: 150,
        savingsPercent: 70,
        estimatedTokensBefore: 125,
        estimatedTokensAfter: 38,
        processingTimeMs: 2,
      },
    ];

    test('should calculate average savings', () => {
      const stats = aggregateMetrics(sampleMetrics) as AggregateStats;

      expect(stats.count).toBe(3);
      // (70 + 75 + 70) / 3 = 71.67
      expect(stats.avgSavingsPercent).toBeCloseTo(71.67, 1);
    });

    test('should calculate min and max savings', () => {
      const stats = aggregateMetrics(sampleMetrics) as AggregateStats;

      expect(stats.minSavingsPercent).toBe(70);
      expect(stats.maxSavingsPercent).toBe(75);
    });

    test('should calculate median savings', () => {
      const stats = aggregateMetrics(sampleMetrics) as AggregateStats;

      // Sorted: 70, 70, 75 → median is 70
      expect(stats.medianSavingsPercent).toBe(70);
    });

    test('should group by operation', () => {
      const byOperation = aggregateMetrics(sampleMetrics, 'operation') as Map<
        string,
        AggregateStats
      >;

      expect(byOperation).toBeInstanceOf(Map);
      expect(byOperation.size).toBe(2);

      const searchStats = byOperation.get('search_nodes');
      expect(searchStats?.count).toBe(2);
      expect(searchStats?.avgSavingsPercent).toBeCloseTo(72.5, 1);

      const statusStats = byOperation.get('get_status');
      expect(statusStats?.count).toBe(1);
    });

    test('should calculate total bytes', () => {
      const stats = aggregateMetrics(sampleMetrics) as AggregateStats;

      expect(stats.totalBytesBeforeTransform).toBe(2300); // 1000 + 800 + 500
      expect(stats.totalBytesAfterTransform).toBe(650); // 300 + 200 + 150
    });

    test('should calculate average processing time', () => {
      const stats = aggregateMetrics(sampleMetrics) as AggregateStats;

      // (5 + 3 + 2) / 3 = 3.33
      expect(stats.avgProcessingTimeMs).toBeCloseTo(3.33, 1);
    });

    test('should handle empty metrics array', () => {
      const stats = aggregateMetrics([]) as AggregateStats;

      expect(stats.count).toBe(0);
      expect(stats.avgSavingsPercent).toBe(0);
    });
  });

  // Tests for persistence functions
  describe('persistence', () => {
    let testDir: string;
    let testFile: string;

    beforeEach(async () => {
      testDir = join(tmpdir(), `token-metrics-test-${Date.now()}`);
      await mkdir(testDir, { recursive: true });
      testFile = join(testDir, 'metrics.jsonl');
    });

    afterEach(async () => {
      await rm(testDir, { recursive: true, force: true });
    });

    describe('appendMetrics', () => {
      test('should append metrics to JSONL file', async () => {
        const metrics: TokenMetrics = {
          operation: 'search_nodes',
          timestamp: new Date('2026-01-18T12:00:00.000Z'),
          rawBytes: 1000,
          compactBytes: 300,
          savingsPercent: 70,
          estimatedTokensBefore: 250,
          estimatedTokensAfter: 75,
          processingTimeMs: 5,
        };

        await appendMetrics(metrics, testFile);

        const content = await readFile(testFile, 'utf-8');
        const lines = content.trim().split('\n');
        expect(lines.length).toBe(1);

        const parsed = JSON.parse(lines[0]);
        expect(parsed.operation).toBe('search_nodes');
        expect(parsed.rawBytes).toBe(1000);
      });

      test('should append multiple metrics', async () => {
        const metrics1: TokenMetrics = {
          operation: 'op1',
          timestamp: new Date(),
          rawBytes: 100,
          compactBytes: 50,
          savingsPercent: 50,
          estimatedTokensBefore: 25,
          estimatedTokensAfter: 13,
          processingTimeMs: 1,
        };
        const metrics2: TokenMetrics = {
          operation: 'op2',
          timestamp: new Date(),
          rawBytes: 200,
          compactBytes: 100,
          savingsPercent: 50,
          estimatedTokensBefore: 50,
          estimatedTokensAfter: 25,
          processingTimeMs: 2,
        };

        await appendMetrics(metrics1, testFile);
        await appendMetrics(metrics2, testFile);

        const content = await readFile(testFile, 'utf-8');
        const lines = content.trim().split('\n');
        expect(lines.length).toBe(2);
      });

      test('should create directory if not exists', async () => {
        const nestedFile = join(testDir, 'nested', 'dir', 'metrics.jsonl');
        const metrics: TokenMetrics = {
          operation: 'test',
          timestamp: new Date(),
          rawBytes: 100,
          compactBytes: 50,
          savingsPercent: 50,
          estimatedTokensBefore: 25,
          estimatedTokensAfter: 13,
          processingTimeMs: 1,
        };

        await appendMetrics(metrics, nestedFile);

        const content = await readFile(nestedFile, 'utf-8');
        expect(content.length).toBeGreaterThan(0);
      });
    });

    describe('loadMetrics', () => {
      test('should load metrics from JSONL file', async () => {
        const metricsLine = `${JSON.stringify({
          operation: 'search_nodes',
          timestamp: '2026-01-18T12:00:00.000Z',
          rawBytes: 1000,
          compactBytes: 300,
          savingsPercent: 70,
          estimatedTokensBefore: 250,
          estimatedTokensAfter: 75,
          processingTimeMs: 5,
        })}\n`;
        await writeFile(testFile, metricsLine);

        const metrics = await loadMetrics(testFile);

        expect(metrics.length).toBe(1);
        expect(metrics[0].operation).toBe('search_nodes');
        expect(metrics[0].rawBytes).toBe(1000);
        expect(metrics[0].timestamp).toBeInstanceOf(Date);
      });

      test('should return empty array for non-existent file', async () => {
        const metrics = await loadMetrics(join(testDir, 'nonexistent.jsonl'));
        expect(metrics).toEqual([]);
      });

      test('should skip invalid JSON lines', async () => {
        const content = [
          JSON.stringify({
            operation: 'valid',
            timestamp: new Date().toISOString(),
            rawBytes: 100,
            compactBytes: 50,
            savingsPercent: 50,
            estimatedTokensBefore: 25,
            estimatedTokensAfter: 13,
            processingTimeMs: 1,
          }),
          'invalid json line',
          JSON.stringify({
            operation: 'valid2',
            timestamp: new Date().toISOString(),
            rawBytes: 200,
            compactBytes: 100,
            savingsPercent: 50,
            estimatedTokensBefore: 50,
            estimatedTokensAfter: 25,
            processingTimeMs: 2,
          }),
        ].join('\n');
        await writeFile(testFile, content);

        const metrics = await loadMetrics(testFile);

        expect(metrics.length).toBe(2);
      });
    });
  });

  // Tests for generateBenchmarkReport
  describe('generateBenchmarkReport', () => {
    test('should generate PASS verdict when all targets met', () => {
      const metrics: TokenMetrics[] = [
        {
          operation: 'search_nodes',
          timestamp: new Date(),
          rawBytes: 1000,
          compactBytes: 300,
          savingsPercent: 70,
          estimatedTokensBefore: 250,
          estimatedTokensAfter: 75,
          processingTimeMs: 5,
        },
        {
          operation: 'add_memory',
          timestamp: new Date(),
          rawBytes: 500,
          compactBytes: 200,
          savingsPercent: 60,
          estimatedTokensBefore: 125,
          estimatedTokensAfter: 50,
          processingTimeMs: 3,
        },
      ];

      const report = generateBenchmarkReport(metrics);

      expect(report.verdict).toBe('PASS');
      expect(report.underperformingOperations.length).toBe(0);
    });

    test('should generate FAIL verdict when targets not met', () => {
      const metrics: TokenMetrics[] = [
        {
          operation: 'search_nodes',
          timestamp: new Date(),
          rawBytes: 1000,
          compactBytes: 900,
          savingsPercent: 10,
          estimatedTokensBefore: 250,
          estimatedTokensAfter: 225,
          processingTimeMs: 5,
        },
      ];

      const report = generateBenchmarkReport(metrics);

      expect(report.verdict).toBe('FAIL');
      expect(report.underperformingOperations.length).toBeGreaterThan(0);
      expect(report.underperformingOperations[0].operation).toBe('search_nodes');
      expect(report.underperformingOperations[0].target).toBe(TOKEN_SAVINGS_TARGETS.search_nodes);
    });

    test('should include overall stats', () => {
      const metrics: TokenMetrics[] = [
        {
          operation: 'search_nodes',
          timestamp: new Date(),
          rawBytes: 1000,
          compactBytes: 300,
          savingsPercent: 70,
          estimatedTokensBefore: 250,
          estimatedTokensAfter: 75,
          processingTimeMs: 5,
        },
      ];

      const report = generateBenchmarkReport(metrics);

      expect(report.totalMeasurements).toBe(1);
      expect(report.overall.avgSavingsPercent).toBe(70);
      expect(report.generatedAt).toBeInstanceOf(Date);
    });

    test('should break down stats by operation', () => {
      const metrics: TokenMetrics[] = [
        {
          operation: 'search_nodes',
          timestamp: new Date(),
          rawBytes: 1000,
          compactBytes: 300,
          savingsPercent: 70,
          estimatedTokensBefore: 250,
          estimatedTokensAfter: 75,
          processingTimeMs: 5,
        },
        {
          operation: 'get_status',
          timestamp: new Date(),
          rawBytes: 500,
          compactBytes: 150,
          savingsPercent: 70,
          estimatedTokensBefore: 125,
          estimatedTokensAfter: 38,
          processingTimeMs: 2,
        },
      ];

      const report = generateBenchmarkReport(metrics);

      expect(report.byOperation.size).toBe(2);
      expect(report.byOperation.has('search_nodes')).toBe(true);
      expect(report.byOperation.has('get_status')).toBe(true);
    });

    test('should generate human-readable summary', () => {
      const metrics: TokenMetrics[] = [
        {
          operation: 'search_nodes',
          timestamp: new Date(),
          rawBytes: 1000,
          compactBytes: 300,
          savingsPercent: 70,
          estimatedTokensBefore: 250,
          estimatedTokensAfter: 75,
          processingTimeMs: 5,
        },
      ];

      const report = generateBenchmarkReport(metrics);

      expect(report.summary).toContain('Token Savings Benchmark');
      expect(report.summary).toContain('search_nodes');
      expect(typeof report.summary).toBe('string');
    });

    test('should handle empty metrics array', () => {
      const report = generateBenchmarkReport([]);

      expect(report.totalMeasurements).toBe(0);
      expect(report.verdict).toBe('PASS'); // No failures if no measurements
    });
  });
});
