/**
 * Unit tests for output-formatter.ts
 * @module tests/unit/output-formatter.test.ts
 */
import { describe, test, expect } from 'bun:test';
import {
  relativeTime,
  truncateUuid,
  truncateText,
  formatSearchNodes,
  formatSearchFacts,
  formatGetEpisodes,
  formatAddMemory,
  formatGetStatus,
  formatDelete,
  formatClearGraph,
  formatOutput,
} from '../../src/server/lib/output-formatter';

describe('output-formatter', () => {
  describe('utility functions', () => {
    describe('relativeTime', () => {
      test('should return "just now" for recent timestamps', () => {
        const now = new Date().toISOString();
        expect(relativeTime(now)).toBe('just now');
      });

      test('should return minutes ago', () => {
        const fiveMinAgo = new Date(Date.now() - 5 * 60 * 1000).toISOString();
        expect(relativeTime(fiveMinAgo)).toBe('5m ago');
      });

      test('should return hours ago', () => {
        const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString();
        expect(relativeTime(twoHoursAgo)).toBe('2h ago');
      });

      test('should return days ago', () => {
        const threeDaysAgo = new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString();
        expect(relativeTime(threeDaysAgo)).toBe('3d ago');
      });

      test('should return months ago', () => {
        const twoMonthsAgo = new Date(Date.now() - 60 * 24 * 60 * 60 * 1000).toISOString();
        expect(relativeTime(twoMonthsAgo)).toBe('2mo ago');
      });
    });

    describe('truncateUuid', () => {
      test('should show last 8 chars with ellipsis', () => {
        const uuid = '550e8400-e29b-41d4-a716-446655440000';
        expect(truncateUuid(uuid)).toBe('...55440000');
      });

      test('should handle short strings', () => {
        expect(truncateUuid('abc')).toBe('abc');
      });

      test('should handle empty string', () => {
        expect(truncateUuid('')).toBe('');
      });
    });

    describe('truncateText', () => {
      test('should truncate at word boundary', () => {
        const text = 'This is a long text that needs truncation';
        expect(truncateText(text, 25)).toBe('This is a long text...');
      });

      test('should not truncate short text', () => {
        const text = 'Short text';
        expect(truncateText(text, 100)).toBe('Short text');
      });

      test('should handle empty string', () => {
        expect(truncateText('', 10)).toBe('');
      });

      test('should handle text with no spaces', () => {
        const text = 'superlongwordwithoutspaces';
        // 10 chars total including ellipsis, so 7 chars + "..."
        expect(truncateText(text, 10)).toBe('superlo...');
      });
    });
  });

  describe('formatSearchNodes', () => {
    test('should format nodes in compact format', () => {
      const data = {
        nodes: [
          { name: 'Graphiti', entity_type: 'Framework', summary: 'Knowledge graph framework' },
          { name: 'FalkorDB', entity_type: 'Database', summary: 'Graph database backend' },
        ],
      };
      const result = formatSearchNodes(data, { query: 'test' });
      expect(result).toContain('Found 2 entities');
      expect(result).toContain('1. Graphiti [Framework]');
      expect(result).toContain('2. FalkorDB [Database]');
    });

    test('should truncate long summaries at 80 chars', () => {
      const longSummary = 'A'.repeat(100);
      const data = {
        nodes: [{ name: 'Test', entity_type: 'Type', summary: longSummary }],
      };
      const result = formatSearchNodes(data, {});
      expect(result.length).toBeLessThan(longSummary.length + 50); // Some overhead for formatting
    });

    test('should handle empty results', () => {
      const data = { nodes: [] };
      const result = formatSearchNodes(data, { query: 'test' });
      expect(result).toContain('No entities found');
    });
  });

  describe('formatSearchFacts', () => {
    test('should format facts with source/target/relation', () => {
      const data = {
        facts: [
          {
            source: { name: 'Graphiti' },
            target: { name: 'FalkorDB' },
            relation: 'uses',
            confidence: 0.95,
          },
        ],
      };
      const result = formatSearchFacts(data, { query: 'test' });
      expect(result).toContain('Graphiti');
      expect(result).toContain('FalkorDB');
      expect(result).toContain('uses');
    });

    test('should include confidence when present', () => {
      const data = {
        facts: [
          {
            source: { name: 'A' },
            target: { name: 'B' },
            relation: 'relates',
            confidence: 0.88,
          },
        ],
      };
      const result = formatSearchFacts(data, {});
      expect(result).toContain('0.88');
    });

    test('should handle empty results', () => {
      const data = { facts: [] };
      const result = formatSearchFacts(data, { query: 'test' });
      expect(result).toContain('No relationships found');
    });
  });

  describe('formatGetEpisodes', () => {
    test('should format episodes with relative time', () => {
      const data = {
        episodes: [
          {
            name: 'Docker Tips',
            content: 'Use --rm flag for containers',
            created_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
          },
        ],
      };
      const result = formatGetEpisodes(data, {});
      expect(result).toContain('Docker Tips');
      expect(result).toContain('2h ago');
    });

    test('should truncate long content at 60 chars', () => {
      const longContent = 'A'.repeat(100);
      const data = {
        episodes: [
          {
            name: 'Test',
            content: longContent,
            created_at: new Date().toISOString(),
          },
        ],
      };
      const result = formatGetEpisodes(data, {});
      expect(result.length).toBeLessThan(longContent.length + 50);
    });

    test('should handle empty results', () => {
      const data = { episodes: [] };
      const result = formatGetEpisodes(data, {});
      expect(result).toContain('No episodes found');
    });
  });

  describe('formatAddMemory', () => {
    test('should show success message from new server format', () => {
      const data = {
        message: "Episode 'Docker Tips' queued for processing in group 'main'",
      };
      const result = formatAddMemory(data, {});
      expect(result).toContain('✓');
      expect(result).toContain('Docker Tips');
      expect(result).toContain('queued');
    });

    test('should handle legacy format with UUID and extraction counts', () => {
      const data = {
        message: 'Episode added',
        uuid: '550e8400-e29b-41d4-a716-446655440000',
        name: 'Test',
        entities_extracted: 3,
        facts_extracted: 2,
      };
      const result = formatAddMemory(data, {});
      expect(result).toContain('✓');
      expect(result).toContain('Test');
      expect(result).toContain('...55440000');
      expect(result).toContain('3 entities');
      expect(result).toContain('2 facts');
    });
  });

  describe('formatGetStatus', () => {
    test('should show status and message from new server format', () => {
      const data = {
        status: 'ok',
        message: 'Connected to neo4j database',
      };
      const result = formatGetStatus(data, {});
      expect(result).toContain('OK');
      expect(result).toContain('Connected to neo4j database');
    });

    test('should handle legacy format with entity and episode counts', () => {
      const data = {
        status: 'HEALTHY',
        message: 'Connected to neo4j database',
        entity_count: 142,
        episode_count: 47,
      };
      const result = formatGetStatus(data, {});
      expect(result).toContain('HEALTHY');
      expect(result).toContain('142');
      expect(result).toContain('47');
    });
  });

  describe('formatDelete', () => {
    test('should show success with truncated UUID', () => {
      const data = {
        success: true,
        uuid: '550e8400-e29b-41d4-a716-446655440000',
      };
      const result = formatDelete(data, {});
      expect(result).toContain('✓');
      expect(result).toContain('...55440000');
    });

    test('should show failure message', () => {
      const data = {
        success: false,
        message: 'Not found',
      };
      const result = formatDelete(data, {});
      expect(result).toContain('✗');
      expect(result).toContain('Not found');
    });
  });

  describe('formatClearGraph', () => {
    test('should show success with counts', () => {
      const data = {
        success: true,
        deleted_entities: 142,
        deleted_episodes: 47,
      };
      const result = formatClearGraph(data, {});
      expect(result).toContain('✓');
      expect(result).toContain('142 entities');
      expect(result).toContain('47 episodes');
    });
  });

  describe('formatOutput', () => {
    test('should route to correct formatter', () => {
      const data = { status: 'ok', message: 'Connected to database' };
      const result = formatOutput('get_status', data);
      expect(result.output).toContain('OK');
      expect(result.usedFallback).toBe(false);
    });

    test('should fallback to JSON on unknown operation', () => {
      const data = { foo: 'bar' };
      const result = formatOutput('unknown_operation', data);
      expect(result.usedFallback).toBe(true);
      expect(result.output).toContain('foo');
    });

    test('should set usedFallback on error', () => {
      // Pass data that will cause formatter to fail
      const result = formatOutput('search_nodes', null);
      expect(result.usedFallback).toBe(true);
    });

    // T024: Additional fallback behavior tests for US2
    test('should return raw JSON when formatter throws', () => {
      const invalidData = { notNodes: [] }; // Missing required 'nodes' property
      const result = formatOutput('search_nodes', invalidData);
      expect(result.usedFallback).toBe(true);
      expect(result.error).toBeDefined();
      expect(result.output).toContain('notNodes'); // Raw JSON preserved
    });

    test('should include error message when fallback used', () => {
      const result = formatOutput('search_nodes', undefined);
      expect(result.usedFallback).toBe(true);
      expect(result.error).toContain('Invalid data format');
    });

    test('should preserve full data in fallback JSON', () => {
      const complexData = {
        nested: { deep: { value: 123 } },
        array: [1, 2, 3],
        string: 'test',
      };
      const result = formatOutput('unknown_op', complexData);
      expect(result.usedFallback).toBe(true);
      const parsed = JSON.parse(result.output);
      expect(parsed).toEqual(complexData);
    });

    test('should collect metrics even on fallback', () => {
      const data = { foo: 'bar' };
      const result = formatOutput('unknown_operation', data, { collectMetrics: true });
      expect(result.usedFallback).toBe(true);
      expect(result.metrics).toBeDefined();
      expect(result.metrics?.rawBytes).toBeGreaterThan(0);
      expect(result.metrics?.savingsPercent).toBe(0); // No savings on fallback
    });
  });
});
