/**
 * Connection Profile Management Library
 *
 * Manages connection profiles for remote MCP server access.
 * Loads and validates profiles from YAML configuration files.
 *
 * Profile file locations:
 *   - $PAI_DIR/config/knowledge-profiles.yaml (priority)
 *   - ~/.claude/config/knowledge-profiles.yaml (fallback)
 *
 * @module connection-profile
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import { resolve } from 'node:path';
import yaml from 'js-yaml';

/**
 * Connection profile configuration
 */
export interface ConnectionProfileData {
  /** Unique profile identifier */
  name: string;
  /** Hostname or IP address */
  host: string;
  /** TCP port */
  port: number;
  /** Protocol: http or https */
  protocol: 'http' | 'https';
  /** URL path prefix (default: /mcp) */
  basePath?: string;
  /** Request timeout in milliseconds (default: 30000) */
  timeout?: number;
  /** TLS configuration (required for https) */
  tls?: TLSConfig;
}

/**
 * TLS/SSL configuration for HTTPS connections
 */
export interface TLSConfig {
  /** Enable certificate verification (default: true) */
  verify?: boolean;
  /** Path to CA certificate file (PEM format) */
  ca?: string;
  /** Path to client certificate file (PEM format) */
  cert?: string;
  /** Path to client private key file (PEM format) */
  key?: string;
  /** Minimum TLS protocol version (default: TLSv1.2) */
  minVersion?: 'TLSv1.2' | 'TLSv1.3';
}

/**
 * Profile configuration file structure
 */
export interface ProfileConfigFile {
  /** Config version */
  version: string;
  /** Default profile name */
  default_profile: string;
  /** Profile definitions */
  profiles: Record<string, Omit<ConnectionProfileData, 'name'>>;
}

/**
 * Runtime connection state
 */
export interface ConnectionState {
  /** Active profile name */
  profile: string;
  /** Connection status */
  status: 'connected' | 'disconnected' | 'error' | 'unknown';
  /** Last successful connection time */
  lastConnected?: Date;
  /** Last error message */
  lastError?: string;
  /** MCP server version */
  serverVersion?: string;
  /** Connected host */
  host?: string;
  /** Connected port */
  port?: number;
  /** Connection protocol */
  protocol?: string;
}

/**
 * Profile validation result
 */
export interface ProfileValidationResult {
  /** Whether profile is valid */
  valid: boolean;
  /** Array of validation error messages */
  errors: string[];
}

/**
 * Connection Profile Manager
 *
 * Loads and validates connection profiles from YAML files.
 */
export class ConnectionProfileManager {
  private configPath: string | null = null;
  private configFile: ProfileConfigFile | null = null;

  /**
   * Find the profile configuration file
   * Checks $PAI_DIR/config first, then ~/.claude/config
   */
  private findConfigFile(): string | null {
    // Check $PAI_DIR/config first (priority)
    const paiDir = process.env.PAI_DIR;
    if (paiDir) {
      const paiConfigPath = resolve(paiDir, 'config', 'knowledge-profiles.yaml');
      if (existsSync(paiConfigPath)) {
        return paiConfigPath;
      }
    }

    // Fallback to ~/.claude/config
    const homeDir = process.env.HOME || process.env.USERPROFILE;
    if (homeDir) {
      const claudeConfigPath = resolve(homeDir, '.claude', 'config', 'knowledge-profiles.yaml');
      if (existsSync(claudeConfigPath)) {
        return claudeConfigPath;
      }
    }

    return null;
  }

  /**
   * Load the configuration file
   */
  private loadConfigFile(): void {
    if (this.configFile !== null) {
      return; // Already loaded
    }

    const configPath = this.findConfigFile();
    if (!configPath) {
      this.configFile = null;
      this.configPath = null;
      return;
    }

    this.configPath = configPath;
    try {
      const content = readFileSync(configPath, 'utf-8');
      this.configFile = yaml.load(content) as ProfileConfigFile;
    } catch (_error) {
      // Treat malformed YAML as missing config - fall back to defaults
      this.configFile = null;
      this.configPath = null;
    }
  }

  /**
   * List all available profile names
   * @returns Array of profile names
   */
  listProfiles(): string[] {
    this.loadConfigFile();

    if (!this.configFile) {
      return [];
    }

    return Object.keys(this.configFile.profiles);
  }

  /**
   * Get the default profile name from config
   * @returns Default profile name or 'default'
   */
  getDefaultProfile(): string {
    this.loadConfigFile();

    if (!this.configFile) {
      return 'default';
    }

    return this.configFile.default_profile || 'default';
  }

  /**
   * Load a profile by name
   * @param profileName - Profile name to load
   * @returns Profile configuration or null if not found
   */
  loadProfile(profileName: string): ConnectionProfileData | null {
    this.loadConfigFile();

    if (!this.configFile) {
      return null;
    }

    const profileData = this.configFile.profiles[profileName];
    if (!profileData) {
      return null;
    }

    return {
      name: profileName,
      ...profileData,
    };
  }

  /**
   * Load a profile with helpful error if not found
   * @param profileName - Profile name to load
   * @returns Profile configuration
   * @throws Error if profile not found with list of available profiles
   */
  loadProfileOrThrow(profileName: string): ConnectionProfileData {
    this.loadConfigFile();

    if (!this.configFile) {
      throw new Error(
        `Profile '${profileName}' not found. No configuration file found.\n\n` +
          `Expected one of:\n` +
          `  - $PAI_DIR/config/knowledge-profiles.yaml\n` +
          `  - ~/.claude/config/knowledge-profiles.yaml`
      );
    }

    const profileData = this.configFile.profiles[profileName];
    if (!profileData) {
      const available = this.listProfiles();
      throw new Error(
        `Profile '${profileName}' not found.\n\n` +
          `Available profiles: ${available.length > 0 ? available.join(', ') : '(none)'}\n` +
          `Default profile: ${this.getDefaultProfile()}`
      );
    }

    return {
      name: profileName,
      ...profileData,
    };
  }

  /**
   * Validate profile configuration
   * @param profile - Profile to validate
   * @returns Validation result with errors if invalid
   */
  validateProfile(profile: ConnectionProfileData): ProfileValidationResult {
    const errors: string[] = [];

    // Validate name
    if (!profile.name || typeof profile.name !== 'string') {
      errors.push('Profile name is required and must be a string');
    } else if (!/^[a-zA-Z0-9_-]+$/.test(profile.name)) {
      errors.push('Profile name must contain only alphanumeric characters, hyphens, and underscores');
    }

    // Validate host
    if (!profile.host || typeof profile.host !== 'string') {
      errors.push('Host is required and must be a string');
    } else {
      // Basic hostname validation (allows IP addresses and hostnames)
      const hostPattern = /^[a-zA-Z0-9.-]+$/;
      if (!hostPattern.test(profile.host)) {
        errors.push('Host must be a valid hostname or IP address');
      }
    }

    // Validate port
    if (!profile.port || typeof profile.port !== 'number') {
      errors.push('Port is required and must be a number');
    } else if (profile.port < 1 || profile.port > 65535) {
      errors.push('Port must be between 1 and 65535');
    }

    // Validate protocol
    if (profile.protocol !== 'http' && profile.protocol !== 'https') {
      errors.push('Protocol must be either "http" or "https"');
    }

    // Validate timeout if provided
    if (profile.timeout !== undefined) {
      if (typeof profile.timeout !== 'number') {
        errors.push('Timeout must be a number');
      } else if (profile.timeout <= 0) {
        errors.push('Timeout must be greater than 0');
      }
    }

    // Validate TLS if protocol is https
    if (profile.protocol === 'https' && !profile.tls) {
      errors.push('TLS configuration is required when using HTTPS protocol');
    }

    // Validate TLS config if provided
    if (profile.tls) {
      if (profile.tls.ca && typeof profile.tls.ca !== 'string') {
        errors.push('TLS CA path must be a string');
      }
      if (profile.tls.cert && typeof profile.tls.cert !== 'string') {
        errors.push('TLS cert path must be a string');
      }
      if (profile.tls.key && typeof profile.tls.key !== 'string') {
        errors.push('TLS key path must be a string');
      }
      // Mutual TLS: both cert and key required
      if ((profile.tls.cert && !profile.tls.key) || (!profile.tls.cert && profile.tls.key)) {
        errors.push('Both TLS cert and key must be provided for mutual TLS');
      }
      if (profile.tls.minVersion && profile.tls.minVersion !== 'TLSv1.2' && profile.tls.minVersion !== 'TLSv1.3') {
        errors.push('TLS minVersion must be either "TLSv1.2" or "TLSv1.3"');
      }
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }

  /**
   * Get the config file path (for debugging)
   */
  getConfigPath(): string | null {
    this.loadConfigFile();
    return this.configPath;
  }

  /**
   * Save or update a profile in the configuration file
   * Creates the config file if it doesn't exist
   * @param profile - Profile to save (name is included in the profile object)
   * @param makeDefault - Whether to make this the default profile (default: false for new profiles, true when updating default)
   * @returns The path to the config file that was created/updated
   */
  saveProfile(profile: ConnectionProfileData, makeDefault: boolean = false): string {
    const { name, ...profileData } = profile;
    const paiDir = process.env.PAI_DIR;
    const homeDir = process.env.HOME || process.env.USERPROFILE;

    // Determine config directory: $PAI_DIR/config takes priority
    let configDir: string;
    if (paiDir) {
      configDir = resolve(paiDir, 'config');
    } else {
      configDir = resolve(homeDir || '', '.claude', 'config');
    }

    // Ensure config directory exists
    if (!existsSync(configDir)) {
      mkdirSync(configDir, { recursive: true });
    }

    const configPath = resolve(configDir, 'knowledge-profiles.yaml');

    // Load existing config or create new one
    let configFile: ProfileConfigFile;
    if (existsSync(configPath)) {
      try {
        const content = readFileSync(configPath, 'utf-8');
        configFile = yaml.load(content) as ProfileConfigFile;
      } catch (_error) {
        // If parse fails, create new config
        configFile = {
          version: '1.0',
          default_profile: name,
          profiles: {},
        };
      }
    } else {
      // Create new config file
      configFile = {
        version: '1.0',
        default_profile: name,
        profiles: {},
      };
    }

    // Update profile data
    configFile.profiles[name] = profileData;

    // Update default profile if requested
    if (makeDefault) {
      configFile.default_profile = name;
    }

    // Write back to file
    const yamlContent = yaml.dump(configFile, { indent: 2, lineWidth: 120 });
    writeFileSync(configPath, yamlContent, 'utf-8');

    // Reload our cached config
    this.configFile = null;
    this.configPath = null;
    this.loadConfigFile();

    return configPath;
  }

  /**
   * Create or update multiple profiles at once
   * Useful for setting up both local and development profiles
   * @param profiles - Array of profiles to save
   * @param defaultProfileName - Which profile should be the default
   * @returns The path to the config file that was created/updated
   */
  saveProfiles(profiles: ConnectionProfileData[], defaultProfileName: string): string {
    const paiDir = process.env.PAI_DIR;
    const homeDir = process.env.HOME || process.env.USERPROFILE;

    // Determine config directory: $PAI_DIR/config takes priority
    let configDir: string;
    if (paiDir) {
      configDir = resolve(paiDir, 'config');
    } else {
      configDir = resolve(homeDir || '', '.claude', 'config');
    }

    // Ensure config directory exists
    if (!existsSync(configDir)) {
      mkdirSync(configDir, { recursive: true });
    }

    const configPath = resolve(configDir, 'knowledge-profiles.yaml');

    // Create config file with all profiles
    const configFile: ProfileConfigFile = {
      version: '1.0',
      default_profile: defaultProfileName,
      profiles: {},
    };

    for (const profile of profiles) {
      const { name, ...profileData } = profile;
      configFile.profiles[name] = profileData;
    }

    // Write to file
    const yamlContent = yaml.dump(configFile, { indent: 2, lineWidth: 120 });
    writeFileSync(configPath, yamlContent, 'utf-8');

    // Reload our cached config
    this.configFile = null;
    this.configPath = null;
    this.loadConfigFile();

    return configPath;
  }
}

/**
 * Environment variable to profile field mappings
 */
const ENV_MAPPINGS: Record<string, keyof ConnectionProfileData | string> = {
  MADEINOZ_KNOWLEDGE_HOST: 'host',
  MADEINOZ_KNOWLEDGE_PORT: 'port',
  MADEINOZ_KNOWLEDGE_PROTOCOL: 'protocol',
  MADEINOZ_KNOWLEDGE_BASE_PATH: 'basePath',
  MADEINOZ_KNOWLEDGE_TIMEOUT: 'timeout',
  MADEINOZ_KNOWLEDGE_TLS_VERIFY: 'tls.verify',
  MADEINOZ_KNOWLEDGE_TLS_CA: 'tls.ca',
  MADEINOZ_KNOWLEDGE_TLS_CERT: 'tls.cert',
  MADEINOZ_KNOWLEDGE_TLS_KEY: 'tls.key',
};

/**
 * Parse environment variable value to appropriate type
 */
function parseEnvValue(key: string, value: string): string | number | boolean {
  if (key === 'MADEINOZ_KNOWLEDGE_PORT' || key === 'MADEINOZ_KNOWLEDGE_TIMEOUT') {
    return Number.parseInt(value, 10);
  }
  if (key === 'MADEINOZ_KNOWLEDGE_TLS_VERIFY') {
    return value.toLowerCase() === 'true' || value === '1';
  }
  return value;
}

/**
 * Set nested object property using dot notation
 * Guards against prototype pollution by validating key names
 */
function setNestedProperty(obj: Record<string, unknown>, path: string, value: unknown): void {
  // Dangerous properties that could lead to prototype pollution
  const DANGEROUS_PROPERTIES = new Set([
    '__proto__',
    'constructor',
    'prototype',
    'toString',
    'toLocaleString',
    'valueOf',
    'hasOwnProperty',
    'isPrototypeOf',
    'propertyIsEnumerable',
  ]);

  // Ensure we only ever traverse and mutate plain objects
  const isPlainObject = (candidate: unknown): candidate is Record<string, unknown> => {
    if (candidate === null || typeof candidate !== 'object') {
      return false;
    }
    if (Object.prototype.toString.call(candidate) !== '[object Object]') {
      return false;
    }
    const proto = Object.getPrototypeOf(candidate);
    return proto === Object.prototype || proto === null;
  };

  if (!isPlainObject(obj)) {
    throw new Error('setNestedProperty can only be used with plain object targets.');
  }

  const keys = path.split('.');
  let current: Record<string, unknown> = obj;

  for (let i = 0; i < keys.length - 1; i++) {
    const key = keys[i];

    // Guard against prototype pollution: block dangerous properties explicitly
    if (DANGEROUS_PROPERTIES.has(key)) {
      throw new Error(`Invalid property name: "${key}". This property is not allowed for security reasons.`);
    }

    // Additional validation: only allow alphanumeric characters and underscores
    // First char must be letter or underscore, subsequent can include numbers
    if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(key)) {
      throw new Error(`Invalid property name: "${key}". Property names must be alphanumeric.`);
    }

    if (!isPlainObject(current)) {
      throw new Error('Encountered non-plain object while setting nested property.');
    }

    if (!(key in current)) {
      current[key] = {};
    }

    const next = current[key];
    if (!isPlainObject(next)) {
      // Prevent overwriting non-plain objects or mutating unexpected prototypes
      throw new Error(`Cannot create nested property "${key}" on non-plain object.`);
    }

    current = next;
  }

  const finalKey = keys[keys.length - 1];

  // Validate final key against dangerous properties
  if (DANGEROUS_PROPERTIES.has(finalKey)) {
    throw new Error(`Invalid property name: "${finalKey}". This property is not allowed for security reasons.`);
  }

  // Validate final key format
  if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(finalKey)) {
    throw new Error(`Invalid property name: "${finalKey}". Property names must be alphanumeric.`);
  }

  if (!isPlainObject(current)) {
    throw new Error('Encountered non-plain object while setting final nested property.');
  }

  current[finalKey] = value;
}

/**
 * Load profile with environment variable overrides
 * @param profileName - Profile name to load (defaults to MADEINOZ_KNOWLEDGE_PROFILE env var or 'default')
 * @returns Profile configuration with env vars applied
 */
export function loadProfileWithOverrides(profileName?: string): ConnectionProfileData {
  const manager = new ConnectionProfileManager();

  // Determine which profile to load
  const envProfile = process.env.MADEINOZ_KNOWLEDGE_PROFILE;
  const targetProfile = profileName || envProfile || manager.getDefaultProfile();

  // Load the profile, fall back to defaults only for missing/malformed config
  let profile: ConnectionProfileData;
  try {
    profile = manager.loadProfileOrThrow(targetProfile);
  } catch (error) {
    // Only fall back to defaults if the error is about missing/malformed config file
    // Re-throw errors for specific profile not found in valid config
    const errorMessage = error instanceof Error ? error.message : String(error);
    if (errorMessage.includes('not found') && !errorMessage.includes('No configuration file found')) {
      // Profile name not found in valid config - re-throw
      throw error;
    }
    // Missing or malformed config file - fall back to code defaults
    profile = {
      name: targetProfile,
      host: 'localhost',
      port: 8001,
      protocol: 'http',
    };
  }

  // Apply environment variable overrides
  for (const [envKey, profilePath] of Object.entries(ENV_MAPPINGS)) {
    const envValue = process.env[envKey];
    if (envValue !== undefined) {
      const parsedValue = parseEnvValue(envKey, envValue);
      setNestedProperty(profile as unknown as Record<string, unknown>, profilePath, parsedValue);
    }
  }

  return profile;
}

/**
 * Get connection profile name from environment
 * @returns Profile name from environment, or default profile from config, or 'default' as final fallback
 */
export function getProfileName(): string {
  const envProfile = process.env.MADEINOZ_KNOWLEDGE_PROFILE;
  if (envProfile) {
    return envProfile;
  }

  // Read default profile from config file
  const manager = new ConnectionProfileManager();
  return manager.getDefaultProfile();
}

/**
 * Export singleton instance
 */
export const profileManager = new ConnectionProfileManager();
