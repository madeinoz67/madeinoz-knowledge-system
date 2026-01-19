/**
 * MCP Wrapper Configuration
 * @module wrapper-config
 *
 * Environment Variables:
 * - MADEINOZ_WRAPPER_COMPACT: Set to "false" to disable compact output (default: true)
 * - MADEINOZ_WRAPPER_METRICS: Set to "true" to enable metrics collection (default: false)
 * - MADEINOZ_WRAPPER_METRICS_FILE: Path to write metrics JSONL file
 * - MADEINOZ_WRAPPER_LOG_FILE: Path to write transformation error logs
 * - MADEINOZ_WRAPPER_SLOW_THRESHOLD: Slow processing threshold in ms (default: 50)
 * - MADEINOZ_WRAPPER_TIMEOUT: Processing timeout in ms (default: 100)
 */

export interface OutputFormat {
  formatId: string;
  template: string;
  extractFields: string[];
  transforms?: Record<string, (value: unknown) => string>;
  maxLength?: number;
}

export interface WrapperConfig {
  compactOutput: boolean;
  collectMetrics: boolean;
  metricsFile?: string;
  logFile?: string;
  slowThresholdMs: number;
  timeoutMs: number;
  formatOverrides?: Record<string, OutputFormat>;
}

/**
 * Environment variable names for wrapper configuration
 */
export const ENV_VARS = {
  COMPACT: "MADEINOZ_WRAPPER_COMPACT",
  METRICS: "MADEINOZ_WRAPPER_METRICS",
  METRICS_FILE: "MADEINOZ_WRAPPER_METRICS_FILE",
  LOG_FILE: "MADEINOZ_WRAPPER_LOG_FILE",
  SLOW_THRESHOLD: "MADEINOZ_WRAPPER_SLOW_THRESHOLD",
  TIMEOUT: "MADEINOZ_WRAPPER_TIMEOUT",
} as const;

/**
 * Load configuration from environment variables
 */
function loadFromEnv(): Partial<WrapperConfig> {
  const config: Partial<WrapperConfig> = {};

  // MADEINOZ_WRAPPER_COMPACT (boolean, default: true)
  const compactEnv = process.env[ENV_VARS.COMPACT];
  if (compactEnv !== undefined) {
    config.compactOutput = compactEnv.toLowerCase() !== "false";
  }

  // MADEINOZ_WRAPPER_METRICS (boolean, default: false)
  const metricsEnv = process.env[ENV_VARS.METRICS];
  if (metricsEnv !== undefined) {
    config.collectMetrics = metricsEnv.toLowerCase() === "true";
  }

  // MADEINOZ_WRAPPER_METRICS_FILE (string path)
  const metricsFileEnv = process.env[ENV_VARS.METRICS_FILE];
  if (metricsFileEnv) {
    config.metricsFile = metricsFileEnv;
    // If a metrics file is specified, also enable metrics collection
    config.collectMetrics = true;
  }

  // MADEINOZ_WRAPPER_LOG_FILE (string path)
  const logFileEnv = process.env[ENV_VARS.LOG_FILE];
  if (logFileEnv) {
    config.logFile = logFileEnv;
  }

  // MADEINOZ_WRAPPER_SLOW_THRESHOLD (number in ms)
  const slowThresholdEnv = process.env[ENV_VARS.SLOW_THRESHOLD];
  if (slowThresholdEnv) {
    const parsed = parseInt(slowThresholdEnv, 10);
    if (!isNaN(parsed) && parsed > 0) {
      config.slowThresholdMs = parsed;
    }
  }

  // MADEINOZ_WRAPPER_TIMEOUT (number in ms)
  const timeoutEnv = process.env[ENV_VARS.TIMEOUT];
  if (timeoutEnv) {
    const parsed = parseInt(timeoutEnv, 10);
    if (!isNaN(parsed) && parsed > 0) {
      config.timeoutMs = parsed;
    }
  }

  return config;
}

export const DEFAULT_CONFIG: WrapperConfig = {
  compactOutput: true,
  collectMetrics: false,
  slowThresholdMs: 50,
  timeoutMs: 100,
};

/**
 * Load configuration with the following priority (highest to lowest):
 * 1. Explicit overrides passed as parameter
 * 2. Environment variables
 * 3. Default values
 */
export function loadConfig(overrides?: Partial<WrapperConfig>): WrapperConfig {
  const envConfig = loadFromEnv();
  return { ...DEFAULT_CONFIG, ...envConfig, ...overrides };
}
