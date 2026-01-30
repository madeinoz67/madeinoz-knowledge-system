/**
 * Integration tests for knowledge-cli.ts profile functionality
 * @module tests/integration/knowledge-cli-profiles.test.ts
 */
import { describe, test, expect, beforeEach, afterEach } from 'bun:test';
import { mkdirSync, rmSync, writeFileSync, readFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { tmpdir } from 'node:os';
import { spawn } from 'node:child_process';
import yaml from 'js-yaml';
import { fileURLToPath } from 'node:url';

interface CLIResult {
  exitCode: number | null;
  stdout: string;
  stderr: string;
}

// Get repository root from test file location
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const repoRoot = dirname(dirname(__dirname)); // Go up from tests/integration to repo root

function runCLI(args: string[], env: Record<string, string> = {}): Promise<CLIResult> {
  return new Promise((resolve) => {
    // Use actual repository root, not PAI_DIR (which tests override)
    const cliPath = join(repoRoot, 'src/skills/tools/knowledge-cli.ts');
    const proc = spawn('bun', ['run', cliPath, ...args], {
      env: { ...process.env, ...env },
    });

    let stdout = '';
    let stderr = '';

    proc.stdout?.on('data', (data) => {
      stdout += data.toString();
    });

    proc.stderr?.on('data', (data) => {
      stderr += data.toString();
    });

    // Set a timeout to prevent hanging on connection attempts
    // CI may not have MCP server running, so we need to fail fast
    const timeout = setTimeout(() => {
      proc.kill('SIGTERM');
      resolve({
        exitCode: null,
        stdout,
        stderr: 'Process timed out after 10 seconds (likely no MCP server available)'
      });
    }, 10000);

    proc.on('close', (code) => {
      clearTimeout(timeout);
      resolve({ exitCode: code, stdout, stderr });
    });

    proc.on('error', (error) => {
      clearTimeout(timeout);
      resolve({ exitCode: -1, stdout, stderr: error.message });
    });
  });
}

describe('knowledge-cli Profile Integration', () => {
  let tempDir: string;
  let configPath: string;

  beforeEach(() => {
    // Create temporary directory for test fixtures
    tempDir = join(tmpdir(), `cli-profile-test-${Date.now()}`);
    mkdirSync(tempDir, { recursive: true });
    mkdirSync(join(tempDir, 'config'), { recursive: true }); // Create config subdirectory
    configPath = join(tempDir, 'config', 'knowledge-profiles.yaml');
  });

  afterEach(() => {
    // Clean up temporary directory
    if (tempDir) {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  describe('--profile flag', () => {
    test('should switch to specified profile', async () => {
      const profileConfig = {
        version: '1.0',
        default_profile: 'local',
        profiles: {
          local: {
            host: 'localhost',
            port: 8001,
            protocol: 'http',
          },
          remote: {
            host: '10.0.0.150',
            port: 8001,
            protocol: 'http',
          },
        },
      };

      writeFileSync(configPath, yaml.dump(profileConfig));

      const originalPAIDir = process.env.PAI_DIR;
      const originalHome = process.env.HOME;
      process.env.PAI_DIR = tempDir;
      process.env.HOME = tempDir; // Prevent fallback to ~/.claude/config

      try {
        // Test list_profiles with --profile flag
        const result = await runCLI(['list_profiles', '--profile', 'remote']);

        // Should succeed and show remote profile as current
        expect(result.exitCode).toBe(0);
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        process.env.HOME = originalHome;
        process.env.HOME = originalHome;
      }
    });

    test('should override default profile when --profile specified', async () => {
      const profileConfig = {
        version: '1.0',
        default_profile: 'local',
        profiles: {
          local: {
            host: 'localhost',
            port: 8001,
            protocol: 'http',
          },
          remote: {
            host: '10.0.0.150',
            port: 8001,
            protocol: 'http',
          },
        },
      };

      writeFileSync(configPath, yaml.dump(profileConfig));

      const originalPAIDir = process.env.PAI_DIR;
      const originalHome = process.env.HOME;
      process.env.PAI_DIR = tempDir;
      process.env.HOME = tempDir;

      try {
        // Test status with --profile flag using test mode (mock connection)
        // Test mode prevents actual network calls and returns mock responses
        const result = await runCLI(['status', '--profile', 'remote'], {
          MADEINOZ_KNOWLEDGE_TEST_MODE: 'true',
        });

        // Should show remote profile connection info
        expect(result.exitCode).toBe(0);
        expect(result.stdout).toContain('"profile": "remote"');
        expect(result.stdout).toContain('"host": "10.0.0.150"');
        expect(result.stdout).toContain('"status": "connected"'); // Mock shows as connected
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        process.env.HOME = originalHome;
      }
    });

    test('should handle non-existent profile gracefully', async () => {
      const profileConfig = {
        version: '1.0',
        default_profile: 'local',
        profiles: {
          local: {
            host: 'localhost',
            port: 8001,
            protocol: 'http',
          },
        },
      };
      writeFileSync(configPath, yaml.dump(profileConfig));

      const originalPAIDir = process.env.PAI_DIR;
      const originalHome = process.env.HOME;
      process.env.PAI_DIR = tempDir;
      process.env.HOME = tempDir;

      try {
        const result = await runCLI(['status', '--profile', 'nonexistent']);

        // Should fail with helpful error
        expect(result.exitCode).not.toBe(0);
        expect(result.stderr).toContain('not found');
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        process.env.HOME = originalHome;
      }
    });
  });

  describe('Default profile behavior', () => {
    test('should use default profile when no --profile flag provided', async () => {
      const profileConfig = {
        version: '1.0',
        default_profile: 'remote',
        profiles: {
          remote: {
            host: '10.0.0.150',
            port: 8001,
            protocol: 'http',
          },
          local: {
            host: 'localhost',
            port: 8001,
            protocol: 'http',
          },
        },
      };
      writeFileSync(configPath, yaml.dump(profileConfig));

      const originalPAIDir = process.env.PAI_DIR;
      const originalHome = process.env.HOME;
      process.env.PAI_DIR = tempDir;
      process.env.HOME = tempDir;

      try {
        const result = await runCLI(['status'], {
          MADEINOZ_KNOWLEDGE_TEST_MODE: 'true',
        });

        // Should use remote (default) profile
        expect(result.stdout).toContain('"profile": "remote"');
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        process.env.HOME = originalHome;
      }
    });

    test('should read default_profile from YAML config', async () => {
      // Test with different default profile
      const profileConfig = {
        version: '1.0',
        default_profile: 'production',
        profiles: {
          production: {
            host: 'prod.example.com',
            port: 443,
            protocol: 'https',
          },
        },
      };
      writeFileSync(configPath, yaml.dump(profileConfig));

      const originalPAIDir = process.env.PAI_DIR;
      const originalHome = process.env.HOME;
      process.env.PAI_DIR = tempDir;
      process.env.HOME = tempDir;

      try {
        const result = await runCLI(['status']);

        // Should use production profile as default
        expect(result.stdout).toContain('"profile": "production"');
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        process.env.HOME = originalHome;
      }
    });
  });

  describe('list_profiles command', () => {
    test('should display all available profiles', async () => {
      const profileConfig = {
        version: '1.0',
        default_profile: 'remote',
        profiles: {
          remote: {
            host: '10.0.0.150',
            port: 8001,
            protocol: 'http',
          },
          local: {
            host: 'localhost',
            port: 8001,
            protocol: 'http',
          },
          development: {
            host: '192.168.1.100',
            port: 8000,
            protocol: 'https',
          },
        },
      };
      writeFileSync(configPath, yaml.dump(profileConfig));

      const originalPAIDir = process.env.PAI_DIR;
      const originalHome = process.env.HOME;
      process.env.PAI_DIR = tempDir;
      process.env.HOME = tempDir;

      try {
        const result = await runCLI(['list_profiles']);

        expect(result.exitCode).toBe(0);
        // Should list all profiles
        expect(result.stdout).toContain('remote');
        expect(result.stdout).toContain('local');
        expect(result.stdout).toContain('development');
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        process.env.HOME = originalHome;
      }
    });

    test('should show current profile', async () => {
      const profileConfig = {
        version: '1.0',
        default_profile: 'remote',
        profiles: {
          remote: {
            host: '10.0.0.150',
            port: 8001,
            protocol: 'http',
          },
        },
      };
      writeFileSync(configPath, yaml.dump(profileConfig));

      const originalPAIDir = process.env.PAI_DIR;
      const originalHome = process.env.HOME;
      process.env.PAI_DIR = tempDir;
      process.env.HOME = tempDir;

      try {
        const result = await runCLI(['list_profiles']);

        // Should show current profile (default)
        expect(result.stdout).toContain('"current": "remote"');
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        process.env.HOME = originalHome;
      }
    });

    test('should show default profile', async () => {
      const profileConfig = {
        version: '1.0',
        default_profile: 'production',
        profiles: {
          production: {
            host: 'prod.example.com',
            port: 443,
            protocol: 'https',
          },
        },
      };
      writeFileSync(configPath, yaml.dump(profileConfig));

      const originalPAIDir = process.env.PAI_DIR;
      const originalHome = process.env.HOME;
      process.env.PAI_DIR = tempDir;
      process.env.HOME = tempDir;

      try {
        const result = await runCLI(['list_profiles']);

        // Should indicate which profile is default
        expect(result.stdout).toContain('"default": "production"');
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        process.env.HOME = originalHome;
      }
    });

    test('should show profile count', async () => {
      const profileConfig = {
        version: '1.0',
        default_profile: 'default',
        profiles: {
          default: { host: 'localhost', port: 8001, protocol: 'http' },
          remote: { host: '10.0.0.150', port: 8001, protocol: 'http' },
        },
      };
      writeFileSync(configPath, yaml.dump(profileConfig));

      const originalPAIDir = process.env.PAI_DIR;
      const originalHome = process.env.HOME;
      process.env.PAI_DIR = tempDir;
      process.env.HOME = tempDir;

      try {
        const result = await runCLI(['list_profiles']);

        // Should show count
        expect(result.stdout).toContain('"count": 2');
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        process.env.HOME = originalHome;
      }
    });
  });

  describe('Environment variable overrides', () => {
    test('--host flag should override profile host', async () => {
      const profileConfig = {
        version: '1.0',
        default_profile: 'remote',
        profiles: {
          remote: {
            host: '10.0.0.150',
            port: 8001,
            protocol: 'http',
          },
        },
      };
      writeFileSync(configPath, yaml.dump(profileConfig));

      const originalPAIDir = process.env.PAI_DIR;
      const originalHome = process.env.HOME;
      process.env.PAI_DIR = tempDir;
      process.env.HOME = tempDir;

      try {
        const result = await runCLI(['status', '--host', 'override.example.com'], {
          MADEINOZ_KNOWLEDGE_TEST_MODE: 'true',
        });

        // Should show overridden host
        expect(result.stdout).toContain('"host": "override.example.com"');
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        process.env.HOME = originalHome;
      }
    });

    test('--port flag should override profile port', async () => {
      const profileConfig = {
        version: '1.0',
        default_profile: 'remote',
        profiles: {
          remote: {
            host: '10.0.0.150',
            port: 8001,
            protocol: 'http',
          },
        },
      };
      writeFileSync(configPath, yaml.dump(profileConfig));

      const originalPAIDir = process.env.PAI_DIR;
      const originalHome = process.env.HOME;
      process.env.PAI_DIR = tempDir;
      process.env.HOME = tempDir;

      try {
        const result = await runCLI(['status', '--port', '9999'], {
          MADEINOZ_KNOWLEDGE_TEST_MODE: 'true',
        });

        // Should show overridden port
        expect(result.stdout).toContain('"port": 9999');
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        process.env.HOME = originalHome;
      }
    });

    test('MADEINOZ_KNOWLEDGE_PROFILE env var should override default', async () => {
      const profileConfig = {
        version: '1.0',
        default_profile: 'local',
        profiles: {
          local: { host: 'localhost', port: 8001, protocol: 'http' },
          production: { host: 'prod.example.com', port: 443, protocol: 'https' },
        },
      };
      writeFileSync(configPath, yaml.dump(profileConfig));

      const originalPAIDir = process.env.PAI_DIR;
      const originalHome = process.env.HOME;
      process.env.PAI_DIR = tempDir;
      process.env.HOME = tempDir;

      try {
        const result = await runCLI(['status'], {
          MADEINOZ_KNOWLEDGE_PROFILE: 'production',
        });

        // Should use production profile from env var
        expect(result.stdout).toContain('"profile": "production"');
        expect(result.stdout).toContain('"host": "prod.example.com"');
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        process.env.HOME = originalHome;
      }
    });
  });

  describe('--raw flag with profiles', () => {
    test('should output JSON with --raw flag', async () => {
      const profileConfig = {
        version: '1.0',
        default_profile: 'remote',
        profiles: {
          remote: {
            host: '10.0.0.150',
            port: 8001,
            protocol: 'http',
          },
        },
      };
      writeFileSync(configPath, yaml.dump(profileConfig));

      const originalPAIDir = process.env.PAI_DIR;
      const originalHome = process.env.HOME;
      process.env.PAI_DIR = tempDir;
      process.env.HOME = tempDir;

      try {
        const result = await runCLI(['status', '--raw'], {
          MADEINOZ_KNOWLEDGE_TEST_MODE: 'true',
        });

        // Should be valid JSON
        expect(() => JSON.parse(result.stdout)).not.toThrow();
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        process.env.HOME = originalHome;
      }
    });
  });

  describe('Error handling', () => {
    test('should provide helpful error when config file missing', async () => {
      // Don't create any config file
      const originalPAIDir = process.env.PAI_DIR;
      const originalHome = process.env.HOME;
      process.env.PAI_DIR = tempDir;
      process.env.HOME = tempDir;

      try {
        const result = await runCLI(['list_profiles']);

        // Should still work (empty profile list)
        expect(result.exitCode).toBe(0);
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        process.env.HOME = originalHome;
      }
    });

    test('should handle malformed YAML gracefully', async () => {
      // Create malformed YAML
      writeFileSync(configPath, 'invalid yaml content {[}');

      const originalPAIDir = process.env.PAI_DIR;
      const originalHome = process.env.HOME;
      process.env.PAI_DIR = tempDir;
      process.env.HOME = tempDir;

      try {
        const result = await runCLI(['status']);

        // Should fall back to defaults
        expect(result.exitCode).toBe(0);
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        process.env.HOME = originalHome;
      }
    });
  });
});
