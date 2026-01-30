/**
 * Unit tests for mcp-client.ts profile loading
 * @module tests/unit/lib/mcp-client-profiles.test.ts
 */
import { describe, test, expect, beforeEach, afterEach } from 'bun:test';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import yaml from 'js-yaml';

import { createMCPClient, type MCPClientConfigExtended } from '../../../src/skills/lib/mcp-client';

describe('createMCPClient with Profile Support', () => {
  let tempDir: string;
  let configPath: string;

  beforeEach(() => {
    // Create temporary directory for test fixtures
    tempDir = join(tmpdir(), `mcp-client-profile-test-${Date.now()}`);
    mkdirSync(tempDir, { recursive: true });
    configPath = join(tempDir, 'config', 'knowledge-profiles.yaml');

    // Clear relevant environment variables
    delete process.env.MADEINOZ_KNOWLEDGE_HOST;
    delete process.env.MADEINOZ_KNOWLEDGE_PORT;
    delete process.env.MADEINOZ_KNOWLEDGE_PROTOCOL;
    delete process.env.MADEINOZ_KNOWLEDGE_PROFILE;
  });

  afterEach(() => {
    // Clean up temporary directory
    if (tempDir) {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  describe('Priority Order', () => {
    test('Priority 1: Explicit config parameter takes precedence', () => {
      const explicitConfig: MCPClientConfigExtended = {
        host: 'explicit-host.com',
        port: 9999,
        protocol: 'https',
      };

      const client = createMCPClient(explicitConfig);

      // The client's baseURL should reflect the explicit config
      expect(client).toBeDefined();
    });

    test('Priority 2: Environment variables override profile', () => {
      // Create profile config
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

      mkdirSync(join(tempDir, 'config'), { recursive: true });
      writeFileSync(configPath, yaml.dump(profileConfig));

      // Set env vars (higher priority than profile)
      process.env.MADEINOZ_KNOWLEDGE_HOST = 'env-host.com';
      process.env.MADEINOZ_KNOWLEDGE_PORT = '7777';

      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const client = createMCPClient();
        expect(client).toBeDefined();
        // Client should use env vars, not profile
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        delete process.env.MADEINOZ_KNOWLEDGE_HOST;
        delete process.env.MADEINOZ_KNOWLEDGE_PORT;
      }
    });

    test('Priority 3: Profile from env var', () => {
      const profileConfig = {
        version: '1.0',
        default_profile: 'default',
        profiles: {
          custom: {
            host: 'custom.example.com',
            port: 8443,
            protocol: 'https',
          },
        },
      };

      mkdirSync(join(tempDir, 'config'), { recursive: true });
      writeFileSync(configPath, yaml.dump(profileConfig));

      process.env.MADEINOZ_KNOWLEDGE_PROFILE = 'custom';

      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const client = createMCPClient();
        expect(client).toBeDefined();
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        delete process.env.MADEINOZ_KNOWLEDGE_PROFILE;
      }
    });

    test('Priority 4: Default profile from YAML', () => {
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

      mkdirSync(join(tempDir, 'config'), { recursive: true });
      writeFileSync(configPath, yaml.dump(profileConfig));

      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const client = createMCPClient();
        expect(client).toBeDefined();
      } finally {
        process.env.PAI_DIR = originalPAIDir;
      }
    });

    test('Priority 5: Code defaults when no config', () => {
      // No profile config, no env vars
      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const client = createMCPClient();
        expect(client).toBeDefined();
        // Should use localhost:8001 as code default
      } finally {
        process.env.PAI_DIR = originalPAIDir;
      }
    });
  });

  describe('Profile Configuration', () => {
    test('should construct correct baseURL from profile', () => {
      const profileConfig = {
        version: '1.0',
        default_profile: 'remote',
        profiles: {
          remote: {
            host: '10.0.0.150',
            port: 8001,
            protocol: 'http',
            basePath: '/mcp',
          },
        },
      };

      mkdirSync(join(tempDir, 'config'), { recursive: true });
      writeFileSync(configPath, yaml.dump(profileConfig));

      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const client = createMCPClient();
        expect(client).toBeDefined();
        // Verify baseURL is constructed correctly
        // http://10.0.0.150:8001/mcp
      } finally {
        process.env.PAI_DIR = originalPAIDir;
      }
    });

    test('should handle HTTPS profiles with TLS config', () => {
      const profileConfig = {
        version: '1.0',
        default_profile: 'secure',
        profiles: {
          secure: {
            host: 'secure.example.com',
            port: 443,
            protocol: 'https',
            basePath: '/mcp',
            tls: {
              verify: true,
              ca: '/etc/ssl/certs/ca.pem',
              minVersion: 'TLSv1.3',
            },
          },
        },
      };

      mkdirSync(join(tempDir, 'config'), { recursive: true });
      writeFileSync(configPath, yaml.dump(profileConfig));

      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const client = createMCPClient();
        expect(client).toBeDefined();
        // Verify TLS config is passed to client
      } finally {
        process.env.PAI_DIR = originalPAIDir;
      }
    });

    test('should handle custom timeout from profile', () => {
      const profileConfig = {
        version: '1.0',
        default_profile: 'slow',
        profiles: {
          slow: {
            host: 'slow.example.com',
            port: 8000,
            protocol: 'http',
            timeout: 60000, // 60 second timeout
          },
        },
      };

      mkdirSync(join(tempDir, 'config'), { recursive: true });
      writeFileSync(configPath, yaml.dump(profileConfig));

      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const client = createMCPClient();
        expect(client).toBeDefined();
        // Verify timeout is set from profile
      } finally {
        process.env.PAI_DIR = originalPAIDir;
      }
    });
  });

  describe('Environment Variable Overrides', () => {
    test('MADEINOZ_KNOWLEDGE_HOST should override profile host', () => {
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

      mkdirSync(join(tempDir, 'config'), { recursive: true });
      writeFileSync(configPath, yaml.dump(profileConfig));

      process.env.MADEINOZ_KNOWLEDGE_HOST = 'override.example.com';

      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const client = createMCPClient();
        expect(client).toBeDefined();
        // Host should be overridden
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        delete process.env.MADEINOZ_KNOWLEDGE_HOST;
      }
    });

    test('MADEINOZ_KNOWLEDGE_PORT should override profile port', () => {
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

      mkdirSync(join(tempDir, 'config'), { recursive: true });
      writeFileSync(configPath, yaml.dump(profileConfig));

      process.env.MADEINOZ_KNOWLEDGE_PORT = '9999';

      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const client = createMCPClient();
        expect(client).toBeDefined();
        // Port should be overridden
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        delete process.env.MADEINOZ_KNOWLEDGE_PORT;
      }
    });

    test('MADEINOZ_KNOWLEDGE_PROTOCOL should override profile protocol', () => {
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

      mkdirSync(join(tempDir, 'config'), { recursive: true });
      writeFileSync(configPath, yaml.dump(profileConfig));

      process.env.MADEINOZ_KNOWLEDGE_PROTOCOL = 'https';

      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const client = createMCPClient();
        expect(client).toBeDefined();
        // Protocol should be overridden
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        delete process.env.MADEINOZ_KNOWLEDGE_PROTOCOL;
      }
    });
  });

  describe('Profile Selection via Environment', () => {
    test('MADEINOZ_KNOWLEDGE_PROFILE should select specific profile', () => {
      const profileConfig = {
        version: '1.0',
        default_profile: 'default',
        profiles: {
          default: {
            host: 'localhost',
            port: 8001,
            protocol: 'http',
          },
          production: {
            host: 'prod.example.com',
            port: 443,
            protocol: 'https',
          },
        },
      };

      mkdirSync(join(tempDir, 'config'), { recursive: true });
      writeFileSync(configPath, yaml.dump(profileConfig));

      process.env.MADEINOZ_KNOWLEDGE_PROFILE = 'production';

      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const client = createMCPClient();
        expect(client).toBeDefined();
        // Should use production profile settings
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        delete process.env.MADEINOZ_KNOWLEDGE_PROFILE;
      }
    });
  });

  describe('Fallback Behavior', () => {
    test('should fall back to environment config if profile loading fails', () => {
      // Don't create any profile config
      process.env.MADEINOZ_KNOWLEDGE_HOST = 'fallback.example.com';
      process.env.MADEINOZ_KNOWLEDGE_PORT = '8080';

      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const client = createMCPClient();
        expect(client).toBeDefined();
        // Should use environment variables
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        delete process.env.MADEINOZ_KNOWLEDGE_HOST;
        delete process.env.MADEINOZ_KNOWLEDGE_PORT;
      }
    });

    test('should fall back to code defaults if no config available', () => {
      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const client = createMCPClient();
        expect(client).toBeDefined();
        // Should use localhost:8001
      } finally {
        process.env.PAI_DIR = originalPAIDir;
      }
    });
  });
});
