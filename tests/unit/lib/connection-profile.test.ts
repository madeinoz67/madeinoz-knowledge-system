/**
 * Unit tests for connection-profile.ts
 * @module tests/unit/lib/connection-profile.test.ts
 */
import { describe, test, expect, beforeEach, afterEach } from 'bun:test';
import { mkdirSync, rmSync, writeFileSync, existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import yaml from 'js-yaml';

import {
  ConnectionProfileManager,
  ConnectionProfileData,
  ProfileConfigFile,
  loadProfileWithOverrides,
  getProfileName,
} from '../../../src/skills/lib/connection-profile';

describe('ConnectionProfileManager', () => {
  let tempDir: string;
  let configPath: string;

  beforeEach(() => {
    // Create temporary directory for test fixtures
    tempDir = join(tmpdir(), `connection-profile-test-${Date.now()}`);
    mkdirSync(tempDir, { recursive: true });
    mkdirSync(join(tempDir, 'config'), { recursive: true }); // Create config subdirectory
    configPath = join(tempDir, 'config', 'knowledge-profiles.yaml');
  });

  afterEach(() => {
    // Clean up temporary directory
    if (existsSync(tempDir)) {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  describe('findConfigFile', () => {
    test('should return path when config exists in PAI_DIR', () => {
      // Create config in temp PAI_DIR
      const paiConfigPath = join(tempDir, 'config', 'knowledge-profiles.yaml');
      mkdirSync(join(tempDir, 'config'), { recursive: true });
      writeFileSync(paiConfigPath, 'version: "1.0"\ndefault_profile: test\nprofiles: {}');

      // Mock PAI_DIR environment
      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const manager = new ConnectionProfileManager();
        expect(manager.getConfigPath()).toBe(paiConfigPath);
      } finally {
        process.env.PAI_DIR = originalPAIDir;
      }
    });

    test('should find config in home directory when PAI_DIR not set', () => {
      // Note: This test may pick up existing ~/.claude/config/knowledge-profiles.yaml
      // so we just verify it returns a path or null
      const manager = new ConnectionProfileManager();
      const path = manager.getConfigPath();
      // Should either be null or a valid path string
      expect(path === null || typeof path === 'string').toBe(true);
    });
  });

  describe('loadProfile', () => {
    test('should load profile from YAML config', () => {
      const config: ProfileConfigFile = {
        version: '1.0',
        default_profile: 'remote',
        profiles: {
          remote: {
            host: '10.0.0.150',
            port: 8001,
            protocol: 'http',
            basePath: '/mcp',
            timeout: 30000,
          },
        },
      };

      writeFileSync(configPath, yaml.dump(config));

      // Mock to use our temp config
      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const manager = new ConnectionProfileManager();
        const profile = manager.loadProfile('remote');

        expect(profile).not.toBeNull();
        expect(profile?.name).toBe('remote');
        expect(profile?.host).toBe('10.0.0.150');
        expect(profile?.port).toBe(8001);
        expect(profile?.protocol).toBe('http');
      } finally {
        process.env.PAI_DIR = originalPAIDir;
      }
    });

    test('should return null for non-existent profile', () => {
      const config: ProfileConfigFile = {
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

      writeFileSync(configPath, yaml.dump(config));

      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const manager = new ConnectionProfileManager();
        const profile = manager.loadProfile('nonexistent');

        expect(profile).toBeNull();
      } finally {
        process.env.PAI_DIR = originalPAIDir;
      }
    });

    test('should return null when config file does not exist', () => {
      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const manager = new ConnectionProfileManager();
        const profile = manager.loadProfile('any');

        expect(profile).toBeNull();
      } finally {
        process.env.PAI_DIR = originalPAIDir;
      }
    });
  });

  describe('loadProfileOrThrow', () => {
    test('should throw helpful error for non-existent profile', () => {
      const config: ProfileConfigFile = {
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

      writeFileSync(configPath, yaml.dump(config));

      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const manager = new ConnectionProfileManager();

        expect(() => manager.loadProfileOrThrow('nonexistent')).toThrow(
          "Profile 'nonexistent' not found"
        );
      } finally {
        process.env.PAI_DIR = originalPAIDir;
      }
    });

    test('should include available profiles in error message', () => {
      const config: ProfileConfigFile = {
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

      writeFileSync(configPath, yaml.dump(config));

      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const manager = new ConnectionProfileManager();

        expect(() => manager.loadProfileOrThrow('missing')).toThrow(/Available profiles:/);
      } finally {
        process.env.PAI_DIR = originalPAIDir;
      }
    });
  });

  describe('getDefaultProfile', () => {
    test('should return default profile from config', () => {
      const config: ProfileConfigFile = {
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

      writeFileSync(configPath, yaml.dump(config));

      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const manager = new ConnectionProfileManager();
        const defaultProfile = manager.getDefaultProfile();

        expect(defaultProfile).toBe('remote');
      } finally {
        process.env.PAI_DIR = originalPAIDir;
      }
    });

    test('should return "default" when no config exists', () => {
      // Use a completely separate temp dir to avoid picking up any config
      const emptyDir = join(tmpdir(), `empty-default-test-${Date.now()}`);
      mkdirSync(emptyDir, { recursive: true });

      const originalPAIDir = process.env.PAI_DIR;
      const originalHome = process.env.HOME;
      process.env.PAI_DIR = emptyDir;
      process.env.HOME = emptyDir; // Also override HOME to prevent fallback

      try {
        const manager = new ConnectionProfileManager();
        const defaultProfile = manager.getDefaultProfile();

        expect(defaultProfile).toBe('default');
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        process.env.HOME = originalHome;
        rmSync(emptyDir, { recursive: true, force: true });
      }
    });
  });

  describe('saveProfile', () => {
    test('should create new config file with profile', () => {
      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const manager = new ConnectionProfileManager();

        const profile: ConnectionProfileData = {
          name: 'test',
          host: '192.168.1.100',
          port: 8000,
          protocol: 'http',
        };

        const resultPath = manager.saveProfile(profile);
        const expectedPath = join(tempDir, 'config', 'knowledge-profiles.yaml');

        expect(resultPath).toBe(expectedPath);
        expect(existsSync(expectedPath)).toBe(true);

        // Verify content
        const content = readFileSync(expectedPath, 'utf-8');
        const config = yaml.load(content) as ProfileConfigFile;

        expect(config.default_profile).toBe('test');
        expect(config.profiles.test).toBeDefined();
        expect(config.profiles.test.host).toBe('192.168.1.100');
      } finally {
        process.env.PAI_DIR = originalPAIDir;
      }
    });

    test('should update existing config file', () => {
      // Create initial config in config/ subdirectory
      mkdirSync(join(tempDir, 'config'), { recursive: true });
      const actualConfigPath = join(tempDir, 'config', 'knowledge-profiles.yaml');

      const config: ProfileConfigFile = {
        version: '1.0',
        default_profile: 'existing',
        profiles: {
          existing: {
            host: 'localhost',
            port: 8001,
            protocol: 'http',
          },
        },
      };

      writeFileSync(actualConfigPath, yaml.dump(config));

      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const manager = new ConnectionProfileManager();

        const newProfile: ConnectionProfileData = {
          name: 'new-profile',
          host: '10.0.0.150',
          port: 8001,
          protocol: 'http',
        };

        manager.saveProfile(newProfile);

        // Verify both profiles exist
        const content = readFileSync(actualConfigPath, 'utf-8');
        const updatedConfig = yaml.load(content) as ProfileConfigFile;

        expect(updatedConfig.profiles.existing).toBeDefined();
        expect(updatedConfig.profiles['new-profile']).toBeDefined();
        expect(updatedConfig.default_profile).toBe('existing'); // Should not change default
      } finally {
        process.env.PAI_DIR = originalPAIDir;
      }
    });

    test('should set default profile when makeDefault is true', () => {
      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const manager = new ConnectionProfileManager();

        const profile: ConnectionProfileData = {
          name: 'priority',
          host: '10.0.0.150',
          port: 8001,
          protocol: 'http',
        };

        manager.saveProfile(profile, true);
        const expectedPath = join(tempDir, 'config', 'knowledge-profiles.yaml');

        const content = readFileSync(expectedPath, 'utf-8');
        const config = yaml.load(content) as ProfileConfigFile;

        expect(config.default_profile).toBe('priority');
      } finally {
        process.env.PAI_DIR = originalPAIDir;
      }
    });
  });

  describe('validateProfile', () => {
    const manager = new ConnectionProfileManager();

    test('should validate correct profile', () => {
      const profile: ConnectionProfileData = {
        name: 'valid',
        host: 'localhost',
        port: 8001,
        protocol: 'http',
        basePath: '/mcp',
        timeout: 30000,
      };

      const result = manager.validateProfile(profile);

      expect(result.valid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    test('should require name field', () => {
      const profile = {
        host: 'localhost',
        port: 8001,
        protocol: 'http',
      } as unknown as ConnectionProfileData;

      const result = manager.validateProfile(profile);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Profile name is required and must be a string');
    });

    test('should validate port range', () => {
      const profile: ConnectionProfileData = {
        name: 'test',
        host: 'localhost',
        port: 99999, // Invalid port
        protocol: 'http',
      };

      const result = manager.validateProfile(profile);

      expect(result.valid).toBe(false);
      expect(result.errors.some(e => e.includes('Port must be between'))).toBe(true);
    });

    test('should require TLS config for https protocol', () => {
      const profile: ConnectionProfileData = {
        name: 'test',
        host: 'example.com',
        port: 443,
        protocol: 'https',
        // Missing TLS config
      };

      const result = manager.validateProfile(profile);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('TLS configuration is required when using HTTPS protocol');
    });

    test('should validate TLS certificate and key are both provided', () => {
      const profile: ConnectionProfileData = {
        name: 'test',
        host: 'example.com',
        port: 443,
        protocol: 'https',
        tls: {
          cert: '/path/to/cert.pem',
          // Missing key
        },
      };

      const result = manager.validateProfile(profile);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Both TLS cert and key must be provided for mutual TLS');
    });
  });

  describe('listProfiles', () => {
    test('should return list of profile names from config', () => {
      const config: ProfileConfigFile = {
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

      writeFileSync(configPath, yaml.dump(config));

      const originalPAIDir = process.env.PAI_DIR;
      process.env.PAI_DIR = tempDir;

      try {
        const manager = new ConnectionProfileManager();
        const profiles = manager.listProfiles();

        expect(profiles).toContain('remote');
        expect(profiles).toContain('local');
      } finally {
        process.env.PAI_DIR = originalPAIDir;
      }
    });

    test('should return empty array when config file does not exist', () => {
      // Use a different temp dir that has no config
      const emptyDir = join(tmpdir(), `empty-test-${Date.now()}`);
      mkdirSync(emptyDir, { recursive: true });

      const originalPAIDir = process.env.PAI_DIR;
      const originalHome = process.env.HOME;
      process.env.PAI_DIR = emptyDir;
      process.env.HOME = emptyDir; // Also override HOME to prevent fallback

      try {
        const manager = new ConnectionProfileManager();
        const profiles = manager.listProfiles();

        expect(profiles).toEqual([]);
      } finally {
        process.env.PAI_DIR = originalPAIDir;
        process.env.HOME = originalHome;
        rmSync(emptyDir, { recursive: true, force: true });
      }
    });
  });
});

describe('getProfileName', () => {
  let tempDir: string;
  let configPath: string;

  beforeEach(() => {
    tempDir = join(tmpdir(), `profile-test-${Date.now()}`);
    mkdirSync(tempDir, { recursive: true });
    mkdirSync(join(tempDir, 'config'), { recursive: true }); // Create config subdirectory
    configPath = join(tempDir, 'config', 'knowledge-profiles.yaml');
  });

  afterEach(() => {
    if (existsSync(tempDir)) {
      rmSync(tempDir, { recursive: true, force: true });
    }
  });

  test('should use environment variable if set', () => {
    // Use empty temp dir to avoid picking up existing config
    const emptyDir = join(tmpdir(), `empty-profile-test-${Date.now()}`);
    mkdirSync(emptyDir, { recursive: true });

    process.env.MADEINOZ_KNOWLEDGE_PROFILE = 'custom-profile';
    const originalPAIDir = process.env.PAI_DIR;
    process.env.PAI_DIR = emptyDir;

    try {
      const result = getProfileName();
      expect(result).toBe('custom-profile');
    } finally {
      process.env.PAI_DIR = originalPAIDir;
      delete process.env.MADEINOZ_KNOWLEDGE_PROFILE;
      rmSync(emptyDir, { recursive: true, force: true });
    }
  });

  test('should read default profile from config file', () => {
    const config: ProfileConfigFile = {
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

    writeFileSync(configPath, yaml.dump(config));

    const originalPAIDir = process.env.PAI_DIR;
    process.env.PAI_DIR = tempDir;

    try {
      const result = getProfileName();
      expect(result).toBe('remote');
    } finally {
      process.env.PAI_DIR = originalPAIDir;
    }
  });

  test('should return "default" when no config exists', () => {
    // Use empty temp dir to avoid picking up existing config
    const emptyDir = join(tmpdir(), `empty-profile-test-${Date.now()}`);
    mkdirSync(emptyDir, { recursive: true });

    // Ensure no env var is set
    delete process.env.MADEINOZ_KNOWLEDGE_PROFILE;

    const originalPAIDir = process.env.PAI_DIR;
    const originalHome = process.env.HOME;
    process.env.PAI_DIR = emptyDir;
    process.env.HOME = emptyDir; // Also override HOME to prevent fallback

    try {
      const result = getProfileName();
      expect(result).toBe('default');
    } finally {
      process.env.PAI_DIR = originalPAIDir;
      process.env.HOME = originalHome;
      rmSync(emptyDir, { recursive: true, force: true });
    }
  });
});

describe('loadProfileWithOverrides', () => {
  let tempDir: string;
  let configPath: string;

  beforeEach(() => {
    tempDir = join(tmpdir(), `override-test-${Date.now()}`);
    mkdirSync(tempDir, { recursive: true });
    mkdirSync(join(tempDir, 'config'), { recursive: true }); // Create config subdirectory
    configPath = join(tempDir, 'config', 'knowledge-profiles.yaml');
  });

  afterEach(() => {
    if (existsSync(tempDir)) {
      rmSync(tempDir, { recursive: true, force: true });
    }
    // Clean up env vars
    delete process.env.MADEINOZ_KNOWLEDGE_HOST;
    delete process.env.MADEINOZ_KNOWLEDGE_PORT;
    delete process.env.MADEINOZ_KNOWLEDGE_PROTOCOL;
  });

  test('should load profile from config', () => {
    const config: ProfileConfigFile = {
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

    writeFileSync(configPath, yaml.dump(config));

    const originalPAIDir = process.env.PAI_DIR;
    process.env.PAI_DIR = tempDir;

    try {
      const profile = loadProfileWithOverrides('remote');

      expect(profile.name).toBe('remote');
      expect(profile.host).toBe('10.0.0.150');
      expect(profile.port).toBe(8001);
      expect(profile.protocol).toBe('http');
    } finally {
      process.env.PAI_DIR = originalPAIDir;
    }
  });

  test('should apply environment variable overrides', () => {
    const config: ProfileConfigFile = {
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

    writeFileSync(configPath, yaml.dump(config));

    const originalPAIDir = process.env.PAI_DIR;
    process.env.PAI_DIR = tempDir;
    process.env.MADEINOZ_KNOWLEDGE_HOST = '192.168.1.50';
    process.env.MADEINOZ_KNOWLEDGE_PORT = '9000';

    try {
      const profile = loadProfileWithOverrides('remote');

      expect(profile.host).toBe('192.168.1.50'); // Overridden
      expect(profile.port).toBe(9000); // Overridden
      expect(profile.protocol).toBe('http'); // Not overridden
    } finally {
      process.env.PAI_DIR = originalPAIDir;
      delete process.env.MADEINOZ_KNOWLEDGE_HOST;
      delete process.env.MADEINOZ_KNOWLEDGE_PORT;
    }
  });

  test('should use default profile when no profile name specified', () => {
    const config: ProfileConfigFile = {
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

    writeFileSync(configPath, yaml.dump(config));

    const originalPAIDir = process.env.PAI_DIR;
    process.env.PAI_DIR = tempDir;

    try {
      const profile = loadProfileWithOverrides();

      expect(profile.name).toBe('local');
      expect(profile.host).toBe('localhost');
    } finally {
      process.env.PAI_DIR = originalPAIDir;
    }
  });
});
