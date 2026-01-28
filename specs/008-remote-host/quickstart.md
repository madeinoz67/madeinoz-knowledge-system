# Quick Start: Remote Host Implementation

**Feature**: 008-remote-host | **For**: Developers implementing this feature

---

## Overview

This feature enables the knowledge-cli tool to connect to remote Knowledge MCP servers instead of only localhost. Implementation involves CLI flag parsing, environment variable support, and fetch configuration for HTTP/HTTPS connections.

---

## Implementation Files

### Files to Modify

| File | Changes |
|------|---------|
| `src/server/lib/cli.ts` | Add new flag definitions (`--host`, `--port`, `--insecure`, `--verbose`) |
| `src/server/lib/config.ts` | Add `getRemoteHostConfig()` function |
| `src/skills/server/tools/*.ts` | Update to use remote host config instead of hardcoded localhost |

### Files to Create (New)

| File | Purpose |
|------|---------|
| `src/server/lib/remote-config.ts` *(optional)* | Extracted remote host configuration logic (if complex) |

---

## Implementation Steps

### Step 1: Extend CLI Flag Parsing

**File**: `src/server/lib/cli.ts`

```typescript
// Add to existing flags parsing
export interface CliFlags {
  // ... existing flags
  host?: string;
  port?: string;
  insecure?: boolean;
  verbose?: boolean;
}

export function parseFlags(args: string[]): CliFlags {
  const flags: CliFlags = {
    // ... existing parsing
  };

  // Parse --host flag
  const hostIndex = args.indexOf('--host');
  if (hostIndex !== -1 && args[hostIndex + 1]) {
    flags.host = args[hostIndex + 1];
  }

  // Parse --port flag
  const portIndex = args.indexOf('--port');
  if (portIndex !== -1 && args[portIndex + 1]) {
    flags.port = args[portIndex + 1];
  }

  // Parse boolean flags
  flags.insecure = args.includes('--insecure');
  flags.verbose = args.includes('--verbose');

  return flags;
}
```

### Step 2: Add Remote Host Configuration

**File**: `src/server/lib/config.ts`

```typescript
export interface RemoteHostConfig {
  host: string;
  port: number;
  protocol: 'http' | 'https';
  insecure: boolean;
  verbose: boolean;
  timeout: number;
}

export function getRemoteHostConfig(flags: CliFlags): RemoteHostConfig {
  // Resolve with priority: CLI flag > env var > default
  const host = flags.host
    ?? process.env['MADEINOZ_KNOWLEDGE_HOST']
    ?? 'localhost';

  const portStr = flags.port
    ?? process.env['MADEINOZ_KNOWLEDGE_PORT']
    ?? '8000';

  // Validate port
  const port = validatePort(portStr);

  // Detect protocol from host prefix
  const protocol = host.startsWith('https://') ? 'https' : 'http';

  // Strip protocol from host for URL construction
  const cleanHost = host.replace(/^https?:\/\//, '');

  return {
    host: cleanHost,
    port,
    protocol,
    insecure: flags.insecure ?? false,
    verbose: flags.verbose ?? process.env['MADEINOZ_KNOWLEDGE_VERBOSE'] === 'true',
    timeout: 10000, // 10 seconds
  };
}

function validatePort(portStr: string): number {
  const port = parseInt(portStr, 10);
  if (isNaN(port) || port < 1 || port > 65535) {
    throw new Error(`Invalid port: ${portStr}. Must be between 1-65535.`);
  }
  return port;
}

export function buildMcpUrl(config: RemoteHostConfig): string {
  return `${config.protocol}://${config.host}:${config.port}/mcp`;
}
```

### Step 3: Update MCP Client Calls

**File**: `src/skills/server/tools/start.ts` (and other tool files)

**Before**:
```typescript
const mcpUrl = 'http://localhost:8000/mcp';
```

**After**:
```typescript
import { getRemoteHostConfig, buildMcpUrl } from '@server/lib/config';
import { parseFlags } from '@server/lib/cli';

const flags = parseFlags(process.argv);
const config = getRemoteHostConfig(flags);
const mcpUrl = buildMcpUrl(config);
```

### Step 4: Implement Fetch with Timeout and TLS Options

```typescript
import { fetch } from 'bun';

async function connectToMcpServer(url: string, config: RemoteHostConfig) {
  try {
    const response = await fetch(url, {
      signal: AbortSignal.timeout(config.timeout),
      // @ts-ignore - Bun supports this for HTTPS
      rejectUnauthorized: !config.insecure,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return response;

  } catch (error) {
    if (config.verbose) {
      console.error(`Verbose: Connection to ${url} failed`, error);
    }
    throw formatConnectionError(url, config, error);
  }
}

function formatConnectionError(url: string, config: RemoteHostConfig, error: unknown): Error {
  const host = config.host;
  const port = config.port;

  if (error instanceof TypeError && error.message.includes('ECONNREFUSED')) {
    return new Error(
      `Error: Connection to ${host}:${port} was refused.\n` +
      `Verify the server is running.`
    );
  }

  if (error instanceof Error && error.message.includes('timed out')) {
    return new Error(
      `Error: Connection to ${host}:${port} timed out after ${config.timeout}ms.`
    );
  }

  if (error instanceof Error && error.message.includes('certificate')) {
    return new Error(
      `Error: TLS certificate validation failed for ${host}.\n` +
      `Use --insecure to bypass (not recommended for production).`
    );
  }

  return new Error(
    `Error: Connection to ${host}:${port} failed.\n` +
    `Details: ${error instanceof Error ? error.message : String(error)}`
  );
}
```

---

## Testing

### Unit Tests

**File**: `tests/unit/remote-config.test.ts`

```typescript
import { describe, it, expect } from 'bun:test';
import { getRemoteHostConfig, buildMcpUrl, validatePort } from '@server/lib/config';
import { parseFlags } from '@server/lib/cli';

describe('Remote Host Configuration', () => {
  it('should use CLI flags over environment variables', () => {
    process.env['MADEINOZ_KNOWLEDGE_HOST'] = 'env-host.com';
    const flags = parseFlags(['--host', 'cli-host.com']);
    const config = getRemoteHostConfig(flags);
    expect(config.host).toBe('cli-host.com');
  });

  it('should use environment variables when no CLI flag provided', () => {
    process.env['MADEINOZ_KNOWLEDGE_HOST'] = 'env-host.com';
    const flags = parseFlags([]);
    const config = getRemoteHostConfig(flags);
    expect(config.host).toBe('env-host.com');
  });

  it('should default to localhost:8000 when no config provided', () => {
    delete process.env['MADEINOZ_KNOWLEDGE_HOST'];
    delete process.env['MADEINOZ_KNOWLEDGE_PORT'];
    const flags = parseFlags([]);
    const config = getRemoteHostConfig(flags);
    expect(config.host).toBe('localhost');
    expect(config.port).toBe(8000);
  });

  it('should validate port range', () => {
    expect(() => validatePort('0')).toThrow();
    expect(() => validatePort('65536')).toThrow();
    expect(validatePort('8080')).toBe(8080);
  });

  it('should detect HTTPS protocol from host prefix', () => {
    const flags = parseFlags(['--host', 'https://secure.com']);
    const config = getRemoteHostConfig(flags);
    expect(config.protocol).toBe('https');
    expect(config.host).toBe('secure.com');
  });

  it('should build correct MCP URL', () => {
    const config = {
      host: 'example.com',
      port: 9000,
      protocol: 'http' as const,
      insecure: false,
      verbose: false,
      timeout: 10000,
    };
    expect(buildMcpUrl(config)).toBe('http://example.com:9000/mcp');
  });
});
```

### Integration Tests

**File**: `tests/integration/remote-connection.test.ts`

```typescript
import { describe, it, expect, beforeAll, afterAll } from 'bun:test';
import { connectToMcpServer } from '../lib/remote-config';

describe('Remote MCP Connection', () => {
  // Requires running MCP server on localhost:8000

  it('should connect to local server', async () => {
    const config = {
      host: 'localhost',
      port: 8000,
      protocol: 'http' as const,
      insecure: false,
      verbose: false,
      timeout: 10000,
    };
    const response = await connectToMcpServer('http://localhost:8000/mcp', config);
    expect(response.ok).toBe(true);
  });

  it('should timeout on unreachable host', async () => {
    const config = {
      host: '192.0.2.1', // TEST-NET-1 (non-routable)
      port: 9999,
      protocol: 'http' as const,
      insecure: false,
      verbose: false,
      timeout: 10000,
    };
    await expect(connectToMcpServer('http://192.0.2.1:9999/mcp', config))
      .toThrow(/timed out/);
  });
});
```

---

## Verification Checklist

After implementation, verify:

- [ ] `knowledge-cli --host example.com get_status` connects to example.com
- [ ] `knowledge-cli --port 9000 get_status` uses port 9000
- [ ] `knowledge-cli` (no flags) still connects to localhost:8000
- [ ] `export MADEINOZ_KNOWLEDGE_HOST=remote.com; knowledge-cli` uses the env var
- [ ] `knowledge-cli --host https://secure.com` connects via HTTPS
- [ ] `knowledge-cli --host https://self-signed.dev --insecure` bypasses cert validation
- [ ] `knowledge-cli --verbose get_status` shows detailed connection info
- [ ] Invalid port (0, 65536, "abc") shows clear error message
- [ ] Connection timeout shows error after 10 seconds
- [ ] Help text includes new flags and examples

---

## Common Issues

### Issue: "Invalid port" error

**Cause**: Port outside 1-65535 range or non-numeric value.

**Fix**: Validate user input before passing to config function.

### Issue: HTTPS certificate validation fails

**Cause**: Self-signed or invalid certificate on remote server.

**Fix**: Use `--insecure` flag for development (not recommended for production).

### Issue: Connection hangs indefinitely

**Cause**: Missing timeout configuration.

**Fix**: Ensure `AbortSignal.timeout(10000)` is passed to fetch options.

---

## Related Documentation

- **Feature Spec**: `specs/008-remote-host/spec.md`
- **Data Model**: `specs/008-remote-host/data-model.md`
- **CLI Contract**: `specs/008-remote-host/contracts/cli-interface.md`
- **Research Findings**: `specs/008-remote-host/research.md`
