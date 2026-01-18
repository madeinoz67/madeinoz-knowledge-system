/**
 * Frontmatter Parser
 *
 * Parses YAML frontmatter from markdown files captured by the PAI Memory System.
 * Updated for Memory System v7.0 (2026-01-12) - handles both old and new schemas.
 *
 * New Memory System schema:
 * - capture_type, timestamp, rating, source, auto_captured, tags
 * - session_id and executor are now optional (extracted from filename in v7.0)
 *
 * Also handles files without frontmatter (e.g., work completion learnings)
 */

export interface MemoryFrontmatter {
  capture_type: 'LEARNING' | 'RESEARCH' | 'WORK' | 'SECURITY' | string;
  timestamp: string;
  // New Memory System fields (v7.0)
  rating?: number;
  source?: 'implicit-sentiment' | 'explicit' | 'hook' | 'manual' | string;
  auto_captured?: boolean;
  tags?: string[];
  // Legacy fields (optional in v7.0 - may be extracted from filename)
  session_id?: string;
  executor?: string;
  agent_completion?: string;
}

export interface ParsedMarkdown {
  frontmatter: MemoryFrontmatter;
  body: string;
  title: string;
  hasFrontmatter: boolean;
}

/**
 * Parse YAML frontmatter from markdown content
 * Handles both frontmatter and non-frontmatter files gracefully
 */
export function parseFrontmatter(content: string): {
  frontmatter: MemoryFrontmatter;
  body: string;
  hasFrontmatter: boolean;
} {
  const match = content.match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);

  if (!match) {
    // No frontmatter - return default structure with full content as body
    return {
      frontmatter: {
        capture_type: 'LEARNING',
        timestamp: new Date().toISOString(),
        auto_captured: true
      },
      body: content.trim(),
      hasFrontmatter: false
    };
  }

  const yamlContent = match[1];
  const body = match[2].trim();

  // Parse YAML manually (simple key: value pairs and arrays)
  const frontmatter: Record<string, any> = {};
  const lines = yamlContent.split('\n');

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;

    const colonIndex = trimmed.indexOf(':');
    if (colonIndex === -1) continue;

    const key = trimmed.slice(0, colonIndex).trim();
    let value = trimmed.slice(colonIndex + 1).trim();

    if (!key) continue;

    // Handle arrays [item1, item2]
    if (value.startsWith('[') && value.endsWith(']')) {
      const arrayContent = value.slice(1, -1);
      frontmatter[key] = arrayContent.split(',').map(s => s.trim().replace(/^['"]|['"]$/g, ''));
    }
    // Handle booleans
    else if (value === 'true') {
      frontmatter[key] = true;
    } else if (value === 'false') {
      frontmatter[key] = false;
    }
    // Handle numbers
    else if (/^\d+$/.test(value)) {
      frontmatter[key] = parseInt(value, 10);
    }
    // Handle strings
    else if (value) {
      frontmatter[key] = value;
    }
  }

  // Only capture_type and timestamp are truly required
  // Set defaults for missing required fields
  if (!frontmatter.capture_type) {
    frontmatter.capture_type = 'LEARNING';
  }
  if (!frontmatter.timestamp) {
    frontmatter.timestamp = new Date().toISOString();
  }

  return {
    frontmatter: frontmatter as MemoryFrontmatter,
    body,
    hasFrontmatter: true
  };
}

/**
 * Extract title from markdown body
 */
export function extractTitle(body: string, fallback: string): string {
  // Try various heading patterns - order matters! More specific patterns first.
  const patterns = [
    // # LEARNING: Title or # RESEARCH: Title (legacy) - MUST be before generic heading
    /^#\s+(?:LEARNING|RESEARCH|DECISION|FEATURE|SESSION|WORK):\s*(.+)$/m,
    // **Title:** pattern from work completion learnings
    /^\*\*Title:\*\*\s*(.+)$/m,
    // # Work Completion Learning or # Implicit Low Rating Detected (generic heading)
    /^#\s+(.+)$/m,
    // **Bold text** at start
    /^\*\*(.+?)\*\*/m,
    // First non-empty line (at least 10 chars)
    /^([^\n#*-].{10,})/m
  ];

  for (const pattern of patterns) {
    const match = body.match(pattern);
    if (match && match[1]) {
      return match[1].trim().slice(0, 100);
    }
  }

  return fallback;
}

/**
 * Extract metadata from filename when frontmatter is missing
 * Memory System v7.0 filename format: YYYY-MM-DD-HHMMSS_TYPE_description.md
 * or: YYYY-MM-DD_HHMM_work_description.md
 */
export function extractMetadataFromFilename(filename: string): Partial<MemoryFrontmatter> {
  const metadata: Partial<MemoryFrontmatter> = {};

  // Try to extract timestamp from filename
  const timestampMatch = filename.match(/^(\d{4}-\d{2}-\d{2})[_-](\d{4,6})/);
  if (timestampMatch) {
    const [, date, time] = timestampMatch;
    const formattedTime = time.length === 6
      ? `${time.slice(0, 2)}:${time.slice(2, 4)}:${time.slice(4, 6)}`
      : `${time.slice(0, 2)}:${time.slice(2, 4)}:00`;
    metadata.timestamp = `${date} ${formattedTime}`;
  }

  // Try to extract type from filename
  const typeMatch = filename.match(/_([A-Z]+)_/i);
  if (typeMatch) {
    metadata.capture_type = typeMatch[1].toUpperCase() as MemoryFrontmatter['capture_type'];
  }

  return metadata;
}

/**
 * Parse markdown file with frontmatter and extract all metadata
 * Handles files with and without frontmatter
 */
export function parseMarkdownFile(content: string, filename?: string): ParsedMarkdown {
  const { frontmatter, body, hasFrontmatter } = parseFrontmatter(content);

  // If no frontmatter and filename provided, try to extract metadata from filename
  if (!hasFrontmatter && filename) {
    const filenameMetadata = extractMetadataFromFilename(filename);
    Object.assign(frontmatter, filenameMetadata);
  }

  const title = extractTitle(body, frontmatter.capture_type);

  return {
    frontmatter,
    body,
    title,
    hasFrontmatter
  };
}

/**
 * Clean markdown body for knowledge storage
 * Removes capture system footer and excessive whitespace
 */
export function cleanBody(body: string): string {
  return body
    // Remove capture footer (with optional blank lines before ---)
    .replace(/\n+---\n+\*Captured by PAI[^*]*\*\s*$/s, '')
    .replace(/\n+---\n+\*Auto-captured by[^*]*\*\s*$/s, '')
    // Remove excessive blank lines
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

// Legacy export for backwards compatibility
export type HistoryFrontmatter = MemoryFrontmatter;
