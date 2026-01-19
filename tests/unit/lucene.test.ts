import { describe, test, expect, beforeEach, afterEach } from "bun:test";
import {
  getDatabaseBackend,
  requiresLuceneSanitization,
  sanitizeGroupId,
  sanitizeGroupIds,
  sanitizeSearchQuery
} from "../../src/server/lib/lucene.js";

describe("lucene sanitization", () => {
  const originalEnv = process.env;

  beforeEach(() => {
    // Reset env before each test
    process.env = { ...originalEnv };
    delete process.env.MADEINOZ_KNOWLEDGE_DATABASE_TYPE;
    delete process.env.DATABASE_TYPE;
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  describe("getDatabaseBackend", () => {
    test("defaults to neo4j when no env set", () => {
      expect(getDatabaseBackend()).toBe("neo4j");
    });

    test("returns falkordb when DATABASE_TYPE=falkordb", () => {
      process.env.DATABASE_TYPE = "falkordb";
      expect(getDatabaseBackend()).toBe("falkordb");
    });

    test("returns neo4j when DATABASE_TYPE=neo4j", () => {
      process.env.DATABASE_TYPE = "neo4j";
      expect(getDatabaseBackend()).toBe("neo4j");
    });

    test("prefers MADEINOZ_KNOWLEDGE_DATABASE_TYPE over DATABASE_TYPE", () => {
      process.env.DATABASE_TYPE = "neo4j";
      process.env.MADEINOZ_KNOWLEDGE_DATABASE_TYPE = "falkordb";
      expect(getDatabaseBackend()).toBe("falkordb");
    });

    test("handles case insensitivity", () => {
      process.env.DATABASE_TYPE = "FALKORDB";
      expect(getDatabaseBackend()).toBe("falkordb");
    });

    test("returns neo4j for unknown values", () => {
      process.env.DATABASE_TYPE = "unknown_db";
      expect(getDatabaseBackend()).toBe("neo4j");
    });
  });

  describe("requiresLuceneSanitization", () => {
    test("returns false for neo4j", () => {
      process.env.DATABASE_TYPE = "neo4j";
      expect(requiresLuceneSanitization()).toBe(false);
    });

    test("returns true for falkordb", () => {
      process.env.DATABASE_TYPE = "falkordb";
      expect(requiresLuceneSanitization()).toBe(true);
    });

    test("returns false when no env set (defaults to neo4j)", () => {
      expect(requiresLuceneSanitization()).toBe(false);
    });
  });

  describe("sanitizeGroupId - Neo4j (no sanitization)", () => {
    beforeEach(() => {
      process.env.DATABASE_TYPE = "neo4j";
    });

    test("returns hyphenated group_id unchanged", () => {
      expect(sanitizeGroupId("my-group-id")).toBe("my-group-id");
    });

    test("returns undefined for undefined input", () => {
      expect(sanitizeGroupId(undefined)).toBeUndefined();
    });

    test("returns complex group_id unchanged", () => {
      expect(sanitizeGroupId("madeinoz-threat-intel")).toBe("madeinoz-threat-intel");
    });

    test("returns underscored group_id unchanged", () => {
      expect(sanitizeGroupId("my_group_id")).toBe("my_group_id");
    });

    test("returns mixed hyphen/underscore group_id unchanged", () => {
      expect(sanitizeGroupId("my-group_id")).toBe("my-group_id");
    });
  });

  describe("sanitizeGroupId - FalkorDB (with sanitization)", () => {
    beforeEach(() => {
      process.env.DATABASE_TYPE = "falkordb";
    });

    test("converts hyphens to underscores", () => {
      expect(sanitizeGroupId("my-group-id")).toBe("my_group_id");
    });

    test("leaves underscored group_id unchanged", () => {
      expect(sanitizeGroupId("my_group_id")).toBe("my_group_id");
    });

    test("returns undefined for undefined input", () => {
      expect(sanitizeGroupId(undefined)).toBeUndefined();
    });

    test("converts multiple hyphens", () => {
      expect(sanitizeGroupId("madeinoz-threat-intel")).toBe("madeinoz_threat_intel");
    });

    test("handles alphanumeric with hyphens", () => {
      expect(sanitizeGroupId("group-123-test")).toBe("group_123_test");
    });
  });

  describe("sanitizeGroupIds - Neo4j (no sanitization)", () => {
    beforeEach(() => {
      process.env.DATABASE_TYPE = "neo4j";
    });

    test("returns array of group_ids unchanged", () => {
      const input = ["group-1", "group-2", "my-test-group"];
      const result = sanitizeGroupIds(input);
      expect(result).toEqual(["group-1", "group-2", "my-test-group"]);
    });

    test("returns undefined for undefined input", () => {
      expect(sanitizeGroupIds(undefined)).toBeUndefined();
    });

    test("returns undefined for empty array", () => {
      expect(sanitizeGroupIds([])).toBeUndefined();
    });
  });

  describe("sanitizeGroupIds - FalkorDB (with sanitization)", () => {
    beforeEach(() => {
      process.env.DATABASE_TYPE = "falkordb";
    });

    test("converts hyphens to underscores in all group_ids", () => {
      const input = ["group-1", "group-2", "my-test-group"];
      const result = sanitizeGroupIds(input);
      expect(result).toEqual(["group_1", "group_2", "my_test_group"]);
    });

    test("returns undefined for undefined input", () => {
      expect(sanitizeGroupIds(undefined)).toBeUndefined();
    });

    test("returns undefined for empty array", () => {
      expect(sanitizeGroupIds([])).toBeUndefined();
    });

    test("preserves underscored group_ids while converting hyphens", () => {
      const input = ["already_ok", "needs-conversion"];
      const result = sanitizeGroupIds(input);
      expect(result).toEqual(["already_ok", "needs_conversion"]);
    });
  });

  describe("sanitizeSearchQuery - Neo4j (no sanitization)", () => {
    beforeEach(() => {
      process.env.DATABASE_TYPE = "neo4j";
    });

    test("returns query with special chars unchanged", () => {
      expect(sanitizeSearchQuery("apt-28")).toBe("apt-28");
      expect(sanitizeSearchQuery("user@domain.com")).toBe("user@domain.com");
    });

    test("returns empty string for empty input", () => {
      expect(sanitizeSearchQuery("")).toBe("");
    });

    test("returns complex CTI query unchanged", () => {
      expect(sanitizeSearchQuery("APT-28 IOC:192.168.1.1")).toBe("APT-28 IOC:192.168.1.1");
    });

    test("returns wildcards unchanged", () => {
      expect(sanitizeSearchQuery("threat*")).toBe("threat*");
      expect(sanitizeSearchQuery("malware?")).toBe("malware?");
    });

    test("returns parentheses unchanged", () => {
      expect(sanitizeSearchQuery("(group AND threat)")).toBe("(group AND threat)");
    });

    test("returns ranges unchanged", () => {
      expect(sanitizeSearchQuery("[2020 TO 2024]")).toBe("[2020 TO 2024]");
    });
  });

  describe("sanitizeSearchQuery - FalkorDB (with sanitization)", () => {
    beforeEach(() => {
      process.env.DATABASE_TYPE = "falkordb";
    });

    test("escapes hyphens", () => {
      expect(sanitizeSearchQuery("apt-28")).toBe("apt\\-28");
    });

    test("escapes at symbol", () => {
      expect(sanitizeSearchQuery("user@domain")).toBe("user\\@domain");
    });

    test("returns empty string for empty input", () => {
      expect(sanitizeSearchQuery("")).toBe("");
    });

    test("escapes colons", () => {
      expect(sanitizeSearchQuery("IOC:192.168.1.1")).toBe("IOC\\:192.168.1.1");
    });

    test("escapes wildcards", () => {
      expect(sanitizeSearchQuery("threat*")).toBe("threat\\*");
      expect(sanitizeSearchQuery("malware?")).toBe("malware\\?");
    });

    test("escapes parentheses", () => {
      expect(sanitizeSearchQuery("(test)")).toBe("\\(test\\)");
    });

    test("escapes brackets", () => {
      expect(sanitizeSearchQuery("[2020 TO 2024]")).toBe("\\[2020 TO 2024\\]");
    });

    test("escapes plus and exclamation", () => {
      expect(sanitizeSearchQuery("+required !excluded")).toBe("\\+required \\!excluded");
    });

    test("escapes backslashes first", () => {
      expect(sanitizeSearchQuery("path\\file")).toBe("path\\\\file");
    });

    test("escapes double ampersand and double pipe", () => {
      // Note: Implementation escapes && first, then individual & chars are escaped again
      // "&&" -> "\&\&" -> "\\&\\&"
      expect(sanitizeSearchQuery("foo && bar")).toBe("foo \\\\&\\\\& bar");
      expect(sanitizeSearchQuery("foo || bar")).toBe("foo \\\\|\\\\| bar");
    });

    test("escapes single ampersand and pipe", () => {
      expect(sanitizeSearchQuery("foo & bar")).toBe("foo \\& bar");
      expect(sanitizeSearchQuery("foo | bar")).toBe("foo \\| bar");
    });

    test("escapes quotes", () => {
      expect(sanitizeSearchQuery('find "malware"')).toBe('find \\"malware\\"');
    });

    test("escapes tilde for fuzzy search", () => {
      expect(sanitizeSearchQuery("threat~2")).toBe("threat\\~2");
    });

    test("escapes caret for boosting", () => {
      expect(sanitizeSearchQuery("important^2")).toBe("important\\^2");
    });

    test("escapes curly braces", () => {
      expect(sanitizeSearchQuery("{1 TO 5}")).toBe("\\{1 TO 5\\}");
    });

    test("escapes hash for tags", () => {
      expect(sanitizeSearchQuery("#malware")).toBe("\\#malware");
    });

    test("escapes dollar sign", () => {
      expect(sanitizeSearchQuery("$variable")).toBe("\\$variable");
    });

    test("escapes percent sign", () => {
      expect(sanitizeSearchQuery("50%")).toBe("50\\%");
    });

    test("escapes comparison operators", () => {
      expect(sanitizeSearchQuery("value<10")).toBe("value\\<10");
      expect(sanitizeSearchQuery("value>5")).toBe("value\\>5");
      expect(sanitizeSearchQuery("value=42")).toBe("value\\=42");
    });

    test("escapes forward slash", () => {
      expect(sanitizeSearchQuery("/regex/")).toBe("\\/regex\\/");
    });

    test("handles complex CTI query with multiple special chars", () => {
      const query = "APT-28 IOC:192.168.1.1 @field";
      const expected = "APT\\-28 IOC\\:192.168.1.1 \\@field";
      expect(sanitizeSearchQuery(query)).toBe(expected);
    });
  });

  describe("sanitizeSearchQuery - default backend (Neo4j)", () => {
    // No env set - should default to neo4j behavior
    test("returns query unchanged when no env set", () => {
      expect(sanitizeSearchQuery("apt-28")).toBe("apt-28");
    });
  });
});
