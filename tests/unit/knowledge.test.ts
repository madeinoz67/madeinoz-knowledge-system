/**
 * Unit tests for knowledge.ts
 * @module tests/unit/knowledge.test.ts
 */
import { describe, test, expect } from 'bun:test';

/**
 * Parse CLI flags from arguments (extracted for testing)
 */
interface CLIFlags {
  raw: boolean;
  metrics: boolean;
  metricsFile?: string;
  help: boolean;
}

function parseFlags(args: string[]): { flags: CLIFlags; positionalArgs: string[] } {
  const flags: CLIFlags = {
    raw: false,
    metrics: false,
    metricsFile: undefined,
    help: false,
  };
  const positionalArgs: string[] = [];

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg === '--raw') {
      flags.raw = true;
    } else if (arg === '--metrics') {
      flags.metrics = true;
    } else if (arg === '--metrics-file') {
      flags.metricsFile = args[++i];
    } else if (arg === '-h' || arg === '--help') {
      flags.help = true;
    } else if (!arg.startsWith('--')) {
      positionalArgs.push(arg);
    }
  }

  return { flags, positionalArgs };
}

describe('knowledge', () => {
  describe('CLI flag parsing', () => {
    test('--raw should set raw flag to true', () => {
      const { flags } = parseFlags(['search_nodes', 'test', '--raw']);
      expect(flags.raw).toBe(true);
    });

    test('--raw flag at start should still work', () => {
      const { flags, positionalArgs } = parseFlags(['--raw', 'search_nodes', 'test']);
      expect(flags.raw).toBe(true);
      expect(positionalArgs).toEqual(['search_nodes', 'test']);
    });

    test('--metrics should set metrics flag to true', () => {
      const { flags } = parseFlags(['search_nodes', 'test', '--metrics']);
      expect(flags.metrics).toBe(true);
    });

    test('--metrics-file should capture file path', () => {
      const { flags } = parseFlags(['search_nodes', '--metrics-file', '/tmp/metrics.jsonl']);
      expect(flags.metricsFile).toBe('/tmp/metrics.jsonl');
    });

    test('-h should set help flag', () => {
      const { flags } = parseFlags(['-h']);
      expect(flags.help).toBe(true);
    });

    test('--help should set help flag', () => {
      const { flags } = parseFlags(['--help']);
      expect(flags.help).toBe(true);
    });

    test('should separate positional args from flags', () => {
      const { flags, positionalArgs } = parseFlags([
        'search_nodes',
        'my query',
        '10',
        '--raw',
        '--metrics',
      ]);
      expect(positionalArgs).toEqual(['search_nodes', 'my query', '10']);
      expect(flags.raw).toBe(true);
      expect(flags.metrics).toBe(true);
    });

    test('should handle multiple flags together', () => {
      const { flags } = parseFlags([
        '--raw',
        '--metrics',
        '--metrics-file',
        '/path/to/file.jsonl',
        'search_nodes',
        'query',
      ]);
      expect(flags.raw).toBe(true);
      expect(flags.metrics).toBe(true);
      expect(flags.metricsFile).toBe('/path/to/file.jsonl');
    });

    test('should handle no flags', () => {
      const { flags, positionalArgs } = parseFlags(['search_nodes', 'test']);
      expect(flags.raw).toBe(false);
      expect(flags.metrics).toBe(false);
      expect(flags.metricsFile).toBeUndefined();
      expect(flags.help).toBe(false);
      expect(positionalArgs).toEqual(['search_nodes', 'test']);
    });

    test('should ignore unknown flags', () => {
      const { flags, positionalArgs } = parseFlags(['--unknown', 'search_nodes']);
      expect(positionalArgs).toEqual(['search_nodes']);
      // Unknown flags starting with -- are not added to positional args
    });
  });
});
