/**
 * Anti-Loop Pattern Detection
 *
 * Detects knowledge-derived content to prevent feedback loops.
 * When a knowledge query produces learnings, those learnings should NOT
 * be synced back to the knowledge graph (they're derivative content).
 *
 * Feature: 007-configurable-memory-sync
 *
 * Pattern Types:
 * - MCP tool patterns: Direct tool invocations (mcp__madeinoz-knowledge__)
 * - Natural language patterns: Query phrases (what do I know about)
 * - Output format patterns: Formatted search results (Key Entities:)
 */

/**
 * Pattern match types.
 */
export type PatternMatchType = 'contains' | 'regex';

/**
 * Where to apply the pattern check.
 */
export type PatternScope = 'body' | 'title' | 'both';

/**
 * A pattern used to detect knowledge-derived content.
 */
export interface AntiLoopPattern {
  /** The pattern string to match */
  pattern: string;

  /** Human-readable description of what this catches */
  description: string;

  /** Match type: 'contains' (substring) or 'regex' (full regex) */
  matchType: PatternMatchType;

  /** Where to apply the check */
  scope: PatternScope;
}

/**
 * Built-in anti-loop patterns.
 * These cannot be disabled and are always applied.
 */
export const BUILTIN_ANTI_LOOP_PATTERNS: AntiLoopPattern[] = [
  // MCP tool patterns
  {
    pattern: 'mcp__madeinoz-knowledge__',
    matchType: 'contains',
    scope: 'both',
    description: 'MCP tool invocations',
  },
  {
    pattern: 'search_memory',
    matchType: 'contains',
    scope: 'both',
    description: 'Memory search operations',
  },
  {
    pattern: 'add_memory',
    matchType: 'contains',
    scope: 'both',
    description: 'Memory add operations',
  },
  {
    pattern: 'get_episodes',
    matchType: 'contains',
    scope: 'both',
    description: 'Episode retrieval',
  },
  {
    pattern: 'search_memory_nodes',
    matchType: 'contains',
    scope: 'both',
    description: 'Node search operation',
  },
  {
    pattern: 'search_memory_facts',
    matchType: 'contains',
    scope: 'both',
    description: 'Facts search operation',
  },
  {
    pattern: 'search_nodes',
    matchType: 'contains',
    scope: 'both',
    description: 'Knowledge node search',
  },

  // Natural language patterns (case-insensitive matching)
  {
    pattern: 'knowledge graph',
    matchType: 'contains',
    scope: 'both',
    description: 'Knowledge graph references',
  },
  {
    pattern: 'what do i know',
    matchType: 'contains',
    scope: 'both',
    description: 'Common query phrase',
  },
  {
    pattern: 'what do you know',
    matchType: 'contains',
    scope: 'both',
    description: 'Common query phrase',
  },
  {
    pattern: 'what have i learned',
    matchType: 'contains',
    scope: 'both',
    description: 'Learning query phrase',
  },

  // Output format patterns
  {
    pattern: 'LEARNING: Search',
    matchType: 'contains',
    scope: 'title',
    description: 'Search result learnings',
  },
  {
    pattern: 'Knowledge Found:',
    matchType: 'contains',
    scope: 'body',
    description: 'Formatted search output',
  },
  {
    pattern: 'Key Entities:',
    matchType: 'contains',
    scope: 'body',
    description: 'Knowledge query output',
  },
  {
    pattern: 'Related Facts:',
    matchType: 'contains',
    scope: 'body',
    description: 'Knowledge query output',
  },
  {
    pattern: 'Episodes Found:',
    matchType: 'contains',
    scope: 'body',
    description: 'Episode search results',
  },
];

/**
 * Result of an anti-loop check.
 */
export interface AntiLoopCheckResult {
  /** Whether any pattern matched */
  matches: boolean;

  /** Description of the matched pattern (if any) */
  matchedPattern?: string;

  /** The actual pattern string that matched */
  matchedPatternString?: string;
}

/**
 * Check if a single pattern matches the content.
 */
function matchesPattern(
  pattern: AntiLoopPattern,
  title: string,
  body: string
): boolean {
  const checkTitle = pattern.scope === 'title' || pattern.scope === 'both';
  const checkBody = pattern.scope === 'body' || pattern.scope === 'both';

  if (pattern.matchType === 'contains') {
    const lowerPattern = pattern.pattern.toLowerCase();
    const lowerTitle = title.toLowerCase();
    const lowerBody = body.toLowerCase();

    if (checkTitle && lowerTitle.includes(lowerPattern)) {
      return true;
    }
    if (checkBody && lowerBody.includes(lowerPattern)) {
      return true;
    }
  } else if (pattern.matchType === 'regex') {
    try {
      const regex = new RegExp(pattern.pattern, 'i');
      if (checkTitle && regex.test(title)) {
        return true;
      }
      if (checkBody && regex.test(body)) {
        return true;
      }
    } catch {
      // Invalid regex, skip this pattern
      console.error(`[AntiLoop] Invalid regex pattern: ${pattern.pattern}`);
    }
  }

  return false;
}

/**
 * Check if content matches any anti-loop pattern.
 *
 * @param title - The file title (from frontmatter or filename)
 * @param body - The file body content
 * @param customPatterns - Additional simple substring patterns from configuration
 * @returns Object with match result and matched pattern description
 */
export function checkAntiLoop(
  title: string,
  body: string,
  customPatterns: string[] = []
): AntiLoopCheckResult {
  // Check built-in patterns first
  for (const pattern of BUILTIN_ANTI_LOOP_PATTERNS) {
    if (matchesPattern(pattern, title, body)) {
      return {
        matches: true,
        matchedPattern: pattern.description,
        matchedPatternString: pattern.pattern,
      };
    }
  }

  // Check custom patterns (treated as case-insensitive substring matches on both title and body)
  for (const customPattern of customPatterns) {
    if (!customPattern || customPattern.trim().length === 0) {
      continue;
    }

    const lowerPattern = customPattern.toLowerCase().trim();
    const lowerTitle = title.toLowerCase();
    const lowerBody = body.toLowerCase();

    if (lowerTitle.includes(lowerPattern) || lowerBody.includes(lowerPattern)) {
      return {
        matches: true,
        matchedPattern: `Custom pattern: ${customPattern}`,
        matchedPatternString: customPattern,
      };
    }
  }

  return { matches: false };
}

/**
 * Get all built-in patterns for display/debugging.
 */
export function getBuiltinPatterns(): AntiLoopPattern[] {
  return [...BUILTIN_ANTI_LOOP_PATTERNS];
}

/**
 * Format patterns for display.
 */
export function formatPatterns(): string {
  const lines = ['Anti-Loop Patterns:'];

  for (const pattern of BUILTIN_ANTI_LOOP_PATTERNS) {
    lines.push(`  - ${pattern.description}: "${pattern.pattern}" (${pattern.scope})`);
  }

  return lines.join('\n');
}
