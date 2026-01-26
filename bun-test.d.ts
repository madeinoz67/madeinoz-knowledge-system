// Bun test globals for TypeScript
declare global {
  function describe(name: string, fn: () => void): void;
  function it(name: string, fn: () => void | Promise<void>): void;
  function test(name: string, fn: () => void | Promise<void>): void;
  function beforeEach(fn: () => void | Promise<void>): void;
  function afterEach(fn: () => void | Promise<void>): void;
  function beforeAll(fn: () => void | Promise<void>): void;
  function afterAll(fn: () => void | Promise<void>): void;

  const expect: {
    <T>(actual: T): {
      toBe(expected: T): void;
      toEqual(expected: T): void;
      toBeTruthy(): void;
      toBeFalsy(): void;
      toThrow(): void;
      toHaveLength(length: number): void;
      toContain(item: unknown): void;
      toBeGreaterThan(value: number): void;
      toBeGreaterThanOrEqual(value: number): void;
      toBeLessThan(value: number): void;
      toBeLessThanOrEqual(value: number): void;
      toBeCloseTo(value: number, precision?: number): void;
      toMatch(regex: RegExp | string): void;
      toHaveProperty(prop: string | string[], value?: unknown): void;
      toBeDefined(): void;
      toBeNull(): void;
      toBeUndefined(): void;
      toBeNaN(): void;
      toBeInstanceOf<T>(constructor: new (...args: unknown[]) => T): void;
      toHaveBeenCalled(): void;
      toHaveBeenCalledTimes(count: number): void;
      toHaveBeenCalledWith(...args: unknown[]): void;
      toMatchObject(snapshot: Partial<unknown>): void;
      toThrowError(expected?: string | RegExp): void;
      not: {
        toBe(expected: unknown): void;
        toEqual(expected: unknown): void;
        toContain(item: unknown): void;
        toHaveProperty(prop: string | string[], value?: unknown): void;
        toMatch(regex: RegExp | string): void;
        toThrow(): void;
      };
    };
    <T>(actual: () => T): {
      toThrow(): void;
      toThrow(expected: string | RegExp): void;
      not: {
        toThrow(): void;
      };
    };
  };
}

export {};
