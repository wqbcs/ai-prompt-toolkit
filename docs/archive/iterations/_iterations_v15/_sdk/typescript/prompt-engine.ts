/**
 * Prompt Engine SDK - TypeScript Implementation
 * Version: v1.0.0-beta | Date: 2026-05-29
 *
 * Core: PromptEngine, ScenarioLoader, Evaluator, Combinator
 */

// ============ Types & Enums ============

export enum ConstraintLevel {
  ERROR = 'error',
  WARN = 'warn',
  INFO = 'info',
}

export enum OutputFormat {
  TEXT = 'text',
  JSON = 'json',
  MARKDOWN = 'markdown',
  XML = 'xml',
}

export enum ExecutionStatus {
  SUCCESS = 'success',
  PARTIAL = 'partial',
  FAILED = 'failed',
  BLOCKED = 'blocked',
}

// ============ Constraint System ============

export interface ConstraintChecker {
  (value: unknown): boolean;
}

export interface Constraint {
  rule: string;
  level: ConstraintLevel;
  message: string;
  checker?: ConstraintChecker;
}

export interface Violation {
  level: ConstraintLevel;
  message: string;
}

export class ConstraintSet {
  private _constraints: Constraint[] = [];

  add(constraint: Constraint): ConstraintSet {
    this._constraints.push(constraint);
    return this;
  }

  addRule(
    rule: string,
    level: ConstraintLevel = ConstraintLevel.ERROR,
    message: string = '',
    checker?: ConstraintChecker,
  ): ConstraintSet {
    this._constraints.push({ rule, level, message, checker });
    return this;
  }

  validate(value: unknown): Violation[] {
    const violations: Violation[] = [];
    for (const c of this._constraints) {
      if (c.checker && !c.checker(value)) {
        violations.push({ level: c.level, message: c.message || c.rule });
      }
    }
    return violations;
  }

  hasErrors(value: unknown): boolean {
    return this.validate(value).some((v) => v.level === ConstraintLevel.ERROR);
  }

  get constraints(): ReadonlyArray<Constraint> {
    return this._constraints;
  }
}

// ============ Scenario ============

export interface ScenarioVariable {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'array' | 'object';
  required: boolean;
  default?: unknown;
  description: string;
  constraints: Record<string, unknown>[];
}

export interface ScenarioDefinition {
  id: string;
  name: string;
  version: string;
  description: string;
  category: string;
  template: string;
  variables: ScenarioVariable[];
  outputFormat: OutputFormat;
  outputSchema?: Record<string, unknown>;
  constraints: Record<string, unknown>[];
  examples: Record<string, unknown>[];
  metadata: Record<string, unknown>;
}

export class ScenarioLoader {
  private _cache = new Map<string, ScenarioDefinition>();

  constructor(private basePath: string | URL) {}

  async load(scenarioId: string): Promise<ScenarioDefinition> {
    if (this._cache.has(scenarioId)) {
      return this._cache.get(scenarioId)!;
    }
    const url = new URL(`${scenarioId}.json`, this.baseUrl);
    const resp = await fetch(url.toString());
    if (!resp.ok) throw new Error(`Scenario '${scenarioId}' not found`);
    const data: ScenarioDefinition = await resp.json();
    this._cache.set(scenarioId, data);
    return data;
  }

  async loadAll(): Promise<ScenarioDefinition[]> {
    const url = new URL('_index.json', this.baseUrl);
    const resp = await fetch(url.toString());
    if (!resp.ok) return [];
    const ids: string[] = await resp.json();
    return Promise.all(ids.map((id) => this.load(id)));
  }

  clearCache(): void {
    this._cache.clear();
  }

  private get baseUrl(): URL {
    return this.basePath instanceof URL ? this.basePath : new URL(this.basePath);
  }

  resolveTemplate(scenario: ScenarioDefinition, bindings: Record<string, unknown>): string {
    let result = scenario.template;
    for (const v of scenario.variables) {
      const value = bindings[v.name] ?? v.default;
      if (value === undefined && v.required) {
        throw new Error(`Required variable '${v.name}' not provided`);
      }
      result = result.replaceAll(`{{${v.name}}}`, String(value ?? ''));
    }
    return result;
  }
}

// ============ Evaluator ============

export interface EvaluationResult {
  scenarioId: string;
  metricName: string;
  score: number;
  maxScore: number;
  details: Record<string, unknown>;
  passed: boolean;
  normalizedScore: number;
}

export interface IEvaluator {
  evaluate(prompt: string, output: string, expected?: string): EvaluationResult;
}

export class StructureEvaluator implements IEvaluator {
  evaluate(prompt: string, output: string, expected?: string): EvaluationResult {
    let score = 0;
    const details: Record<string, boolean> = {};
    if (output.trim()) { score += 5; details.nonEmpty = true; }
    if (output.length > 100) { score += 5; details.sufficientLength = true; }
    if (/##|\*\*/.test(output)) { score += 5; details.hasStructure = true; }
    if (output.includes('\n')) { score += 5; details.multiline = true; }
    const finalScore = Math.min(score, 20);
    return {
      scenarioId: '', metricName: 'structure',
      score: finalScore, maxScore: 20, details,
      passed: finalScore >= 15, normalizedScore: finalScore,
    };
  }
}

export class SafetyEvaluator implements IEvaluator {
  private static DANGEROUS = [/rm\s+-rf/i, /DROP\s+TABLE/i, /eval\(/i, /exec\(/i];

  evaluate(prompt: string, output: string, expected?: string): EvaluationResult {
    const violations: string[] = [];
    for (const p of SafetyEvaluator.DANGEROUS) {
      if (p.test(output)) violations.push(p.source);
    }
    const score = violations.length === 0 ? 20 : Math.max(0, 20 - violations.length * 5);
    return {
      scenarioId: '', metricName: 'safety',
      score, maxScore: 20, details: { violations, safe: violations.length === 0 },
      passed: violations.length === 0, normalizedScore: score,
    };
  }
}

// ============ Combinator ============

export type CombineStrategy = 'concat' | 'hierarchy' | string;

export class Combinator {
  private _strategies = new Map<string, (prompts: string[]) => string>();

  registerStrategy(name: string, strategy: (prompts: string[]) => string): void {
    this._strategies.set(name, strategy);
  }

  generateVariants(
    template: string,
    variables: Record<string, unknown[]>,
  ): string[] {
    const varNames = Object.keys(variables);
    if (varNames.length === 0) return [template];
    const varValues = varNames.map((n) => variables[n]);
    const combos = this.cartesianProduct(varValues);
    return combos.map((combo) => {
      let result = template;
      for (const [name, value] of zip(varNames, combo)) {
        result = result.replaceAll(`{{${name}}}`, String(value));
      }
      return result;
    });
  }

  combinePrompts(prompts: string[], strategy: CombineStrategy = 'concat'): string {
    if (strategy === 'concat') return prompts.join('\n\n---\n\n');
    if (strategy === 'hierarchy') return prompts.join('\n\n## 层级组合\n\n');
    const fn = this._strategies.get(strategy);
    if (fn) return fn(prompts);
    throw new Error(`Unknown strategy: ${strategy}`);
  }

  detectConflicts(constraintSets: ConstraintSet[]): [number, number, string][] {
    const conflicts: [number, number, string][] = [];
    const allRules: [number, string][] = [];
    for (const [i, cs] of constraintSets.entries()) {
      for (const c of cs.constraints) {
        allRules.push([i, c.rule]);
      }
    }
    for (let a = 0; a < allRules.length; a++) {
      for (let b = a + 1; b < allRules.length; b++) {
        if (allRules[a][0] !== allRules[b][0] && allRules[a][1] === allRules[b][1]) {
          conflicts.push([allRules[a][0], allRules[b][0], allRules[a][1]]);
        }
      }
    }
    return conflicts;
  }

  private cartesianProduct<T>(arrays: T[][]): T[][] {
    return arrays.reduce<T[][]>(
      (acc, arr) => acc.flatMap((c) => arr.map((v) => [...c, v])),
      [[]],
    );
  }
}

// ============ Execution Result ============

export interface ExecutionResult {
  scenarioId: string;
  status: ExecutionStatus;
  output: string;
  resolvedPrompt: string;
  evaluationResults: EvaluationResult[];
  constraintsViolations: [string, string][];
  executionTimeMs: number;
  traceId: string;
  metadata: Record<string, unknown>;
}

// ============ PromptEngine ============

export type LLMFn = (prompt: string) => string | Promise<string>;
export type HookFn = (...args: unknown[]) => void | Promise<void>;
export type TraceFn = (result: ExecutionResult) => void;
export type AdapterFn = (resolved: string, scenario: ScenarioDefinition) => string;

export class PromptEngine {
  private _evaluators: IEvaluator[] = [];
  private _combinator = new Combinator();
  private _globalConstraints = new ConstraintSet();
  private _adapter?: AdapterFn;
  private _preHooks: HookFn[] = [];
  private _postHooks: HookFn[] = [];
  private _traceCallback?: TraceFn;

  constructor(private _loader?: ScenarioLoader) {}

  get loader(): ScenarioLoader | undefined { return this._loader; }
  get combinator(): Combinator { return this._combinator; }

  addEvaluator(evaluator: IEvaluator): PromptEngine {
    this._evaluators.push(evaluator);
    return this;
  }

  addConstraint(constraint: Constraint): PromptEngine {
    this._globalConstraints.add(constraint);
    return this;
  }

  setAdapter(adapter: AdapterFn): PromptEngine {
    this._adapter = adapter;
    return this;
  }

  addPreHook(hook: HookFn): PromptEngine {
    this._preHooks.push(hook);
    return this;
  }

  addPostHook(hook: HookFn): PromptEngine {
    this._postHooks.push(hook);
    return this;
  }

  setTraceCallback(callback: TraceFn): PromptEngine {
    this._traceCallback = callback;
    return this;
  }

  async invoke(
    scenarioId: string,
    bindings: Record<string, unknown>,
    llm?: LLMFn,
  ): Promise<ExecutionResult> {
    const start = performance.now();
    const traceId = crypto.randomUUID().slice(0, 16);

    if (!this._loader) throw new Error('No ScenarioLoader configured');
    const scenario = await this._loader.load(scenarioId);

    for (const hook of this._preHooks) await hook(scenario, bindings);

    let resolved = this._loader.resolveTemplate(scenario, bindings);
    if (this._adapter) resolved = this._adapter(resolved, scenario);

    const violations = this._globalConstraints.validate(resolved);
    const errorViolations = violations.filter((v) => v.level === ConstraintLevel.ERROR);
    if (errorViolations.length > 0) {
      return {
        scenarioId, status: ExecutionStatus.BLOCKED, output: '', resolvedPrompt: '',
        evaluationResults: [], constraintsViolations: errorViolations.map((v) => [v.level, v.message]),
        executionTimeMs: performance.now() - start, traceId, metadata: {},
      };
    }

    const output = llm ? await Promise.resolve(llm(resolved)) : resolved;

    const evalResults = this._evaluators.map((e) => e.evaluate(resolved, output));

    for (const hook of this._postHooks) await hook(scenario, output, evalResults);

    const status = evalResults.some((r) => !r.passed) ? ExecutionStatus.PARTIAL : ExecutionStatus.SUCCESS;

    const result: ExecutionResult = {
      scenarioId, status, output, resolvedPrompt: resolved,
      evaluationResults: evalResults,
      constraintsViolations: violations.map((v) => [v.level, v.message]),
      executionTimeMs: performance.now() - start, traceId, metadata: {},
    };

    this._traceCallback?.(result);
    return result;
  }

  async batch(
    requests: [string, Record<string, unknown>][],
    llm?: LLMFn,
  ): Promise<ExecutionResult[]> {
    return Promise.all(requests.map(([id, b]) => this.invoke(id, b, llm)));
  }
}

// ============ Builder ============

export class PromptEngineBuilder {
  private _scenariosPath?: string | URL;
  private _evaluators: IEvaluator[] = [];
  private _constraints: Constraint[] = [];
  private _adapter?: AdapterFn;
  private _preHooks: HookFn[] = [];
  private _postHooks: HookFn[] = [];
  private _traceCallback?: TraceFn;

  withScenarios(path: string | URL): PromptEngineBuilder {
    this._scenariosPath = path;
    return this;
  }

  withEvaluator(evaluator: IEvaluator): PromptEngineBuilder {
    this._evaluators.push(evaluator);
    return this;
  }

  withDefaultEvaluators(): PromptEngineBuilder {
    this._evaluators.push(new StructureEvaluator(), new SafetyEvaluator());
    return this;
  }

  withConstraint(constraint: Constraint): PromptEngineBuilder {
    this._constraints.push(constraint);
    return this;
  }

  withAdapter(adapter: AdapterFn): PromptEngineBuilder {
    this._adapter = adapter;
    return this;
  }

  withPreHook(hook: HookFn): PromptEngineBuilder {
    this._preHooks.push(hook);
    return this;
  }

  withPostHook(hook: HookFn): PromptEngineBuilder {
    this._postHooks.push(hook);
    return this;
  }

  withTracing(callback: TraceFn): PromptEngineBuilder {
    this._traceCallback = callback;
    return this;
  }

  build(): PromptEngine {
    const loader = this._scenariosPath ? new ScenarioLoader(this._scenariosPath) : undefined;
    const engine = new PromptEngine(loader);
    for (const e of this._evaluators) engine.addEvaluator(e);
    for (const c of this._constraints) engine.addConstraint(c);
    if (this._adapter) engine.setAdapter(this._adapter);
    for (const h of this._preHooks) engine.addPreHook(h);
    for (const h of this._postHooks) engine.addPostHook(h);
    if (this._traceCallback) engine.setTraceCallback(this._traceCallback);
    return engine;
  }
}

// ============ Helpers ============

function* zip<K, V>(keys: K[], values: V[]): Generator<[K, V]> {
  for (let i = 0; i < Math.min(keys.length, values.length); i++) {
    yield [keys[i], values[i]];
  }
}
