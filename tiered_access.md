Research Synthesis: Context Efficiency for Agent-Orchestrated Development

  The Numbers That Matter

  I researched how Claude Code (what I am right now) actually works under the hood. Here's the token cost reality:

  ┌───────────────────────────────┬───────────────────┬────────────────┐
  │       What agent reads        │ Tokens per module │ For 50 modules │
  ├───────────────────────────────┼───────────────────┼────────────────┤
  │ Full source (Tier 2)          │ 1,500-2,200       │ 75K-110K       │
  ├───────────────────────────────┼───────────────────┼────────────────┤
  │ base.py interface (Tier 1)    │ 300-800           │ 15K-40K        │
  ├───────────────────────────────┼───────────────────┼────────────────┤
  │ __init__.py manifest (Tier 0) │ 100-300           │ 5K-15K         │
  ├───────────────────────────────┼───────────────────┼────────────────┤
  │ Grep for `class               │ def` lines        │ 50-100         │
  ├───────────────────────────────┼───────────────────┼────────────────┤
  │ Glob paths only               │ 10-20             │ 500-1K         │
  └───────────────────────────────┴───────────────────┴────────────────┘

  Your tiered model already provides a 75-97% context saving vs reading everything. The architecture is sound. The question is: can we squeeze
  more out of it, and where are the leaky abstractions?

  Key Insight 1: Grep IS a Tier 0 mechanism

  Claude Code's Grep tool returns matching lines — not full files. When I grep for ^class  across all base.py files, I get ~50-100 tokens for the
   entire project's interface inventory. This is even more compact than reading __init__.py manifests.

  But — Grep gives you WHAT exists, not WHY it exists or HOW things connect. Manifests encode dependency rationale, usage patterns, and design
  notes that no tool can extract automatically. This is the genuine value of __init__.py manifests.

  Key Insight 2: The Tier 1 gap

  Right now Tier 0 (__init__.py) tells you what exists, and Tier 1 (base.py) tells you how to use it. But reading base.py can cost 300-800 tokens
   — especially with the deliberately verbose docstrings from Step 4. There's a gap between "I know module X exists" (Tier 0, 100 tokens) and "I
  know how to call module X's API" (Tier 1, 500+ tokens).

  What if __init__.py re-exports included one-line interface summaries?

  from .base import (
      Parser,        # parse(source: str, config: ParseConfig) -> AST
      ParseError,    # location: SourceLocation, message: str
      ParseConfig,   # max_depth: int = 100, strict: bool = False
  )

  This gives you Tier 0.5 — enough to know if you even need to open base.py, at ~150 tokens per module instead of ~500.

  Key Insight 3: AST extraction is an 85-90% compression over source

  A Python script using ast module can extract signatures + docstrings from any .py file without executing it. For a typical module:
  - Full source: 2000 tokens
  - AST extract (signatures + first-line docstrings): 200-350 tokens
  - AST extract (signatures only): 100-200 tokens

  This could be a simple script in the repo (tools/inspect_interface.py) that agents call via Bash, or an MCP server for native integration.

  Key Insight 4: MCP servers for code intelligence exist

  Several production MCP servers bridge LSP to Claude Code's tool system:
  - lsp-mcp: Wraps Pyright, gives hover/definition/references as structured compact data
  - ast-grep MCP: Structural code search using AST patterns
  - code-graph-mcp: Builds dependency graphs across codebases

  These could formalize the tiered model as native tools rather than conventions.

  Key Insight 5: Subagent context isolation already maps to tiered access

  Claude Code subagents get completely isolated context windows. The parent sends a task description, the child works independently and returns a
   result. This is exactly the Tier model:
  - Orchestrator (parent): operates at Tier 0
  - Implementer (subagent): receives Tier 0 + Tier 1, loads Tier 2 for its module
  - No context leaks between modules

  The model is already structurally compatible.

  ---
  The Six Open Questions

  I want to walk through these with you to determine what's worth pursuing:

⏺ User answered Claude's questions:
  ⎿  · What's our first priority? I've identified six design avenues. Which should we dig into first? → All what you mention sticks to my
     proposals, maybe you can come up with something even more efficient and aligned with how you work. On top of that let's go through all
     proposals
     · What's the target scale we're optimizing for? This affects which solutions are worth the complexity. → Scale-agnostic






⏺ Great — scale-agnostic design and you want me to think beyond the proposals. Let me go deep. I'll think from first principles about how I
  actually work as Claude Code, then walk through each area.

  ---
  First: What I Actually Wish I Had (Novel Ideas)

  Before walking through your proposals, let me share what I notice causes the most context waste when I work on codebases — things your tiered
  model doesn't yet address:

  Novel Idea 1: CLAUDE.md as the Tier 0 Map (Zero-Cost Tier 0)

  Right now, __init__.py manifests are the Tier 0 vehicle. But reading them requires tool calls — one Glob to find them, then one Read per file.
  For 50 modules, that's 51 tool calls and 5-15K tokens of context consumed.

  Claude Code auto-loads CLAUDE.md at session start — for free. It's injected into my system prompt before I even start thinking. What if the
  project's Tier 0 map lived there?

  # CLAUDE.md

  ## Module Map
  - `parser/` → Parser: parse(str, ParseConfig) → AST. Depends: tokenizer
  - `tokenizer/` → Tokenizer: tokenize(str) → TokenStream. No deps.
  - `optimizer/` → Optimizer: optimize(AST, OptLevel) → AST. Depends: parser, analyzer

  Cost: ~500-2000 tokens for 50 modules, loaded before the first tool call, zero round trips. Every agent session in the project starts with the
  complete Tier 0 map already in context.

  Compare: current approach requires discovering and reading __init__.py files, costing 51 tool calls + 5-15K tokens + multiple inference rounds.

  The tradeoff: CLAUDE.md can drift from reality (same as manifests). But Step 8 (Reconciliation) already exists to fix drift. You just add
  "update CLAUDE.md module map" to Step 8's checklist.

  Novel Idea 2: Hierarchical CLAUDE.md Files as Tiered Context

  Claude Code has a feature most people don't use: directory-level CLAUDE.md files load on-demand when I read files in that directory. This maps
  perfectly to tiered access:

  project/
  ├── CLAUDE.md              # Tier 0: module inventory + dependency graph
  ├── parser/
  │   ├── CLAUDE.md          # Tier 0.5: parser's API surface, usage patterns
  │   ├── __init__.py        # Re-exports only (minimal)
  │   ├── base.py            # Tier 1: full behavioral contracts
  │   └── implementation_v1/
  │       ├── CLAUDE.md      # Tier 2 guidance: implementation notes
  │       └── impl.py        # Tier 2: full source

  When an agent starts working on parser, the parser-level CLAUDE.md auto-loads with interface summaries. No tool call needed. The agent only
  opens base.py if it needs full behavioral contracts.

  This is Claude Code's native mechanism for exactly the problem you're solving. But nobody uses it for structured API metadata — they use it for
   style guides and workflow notes.

  Novel Idea 3: Read with line limits as Tier 1

  Here's something I can do that your templates never mention: Read(file, limit=N). I can read just the first 30 lines of a file.

  If every base.py starts with a structured header:

  """
  Module: parser.base
  Public Interfaces:
      Parser: parse(source: str, config: ParseConfig) -> AST
      Validator: validate(ast: AST) -> ValidationResult
  Error Types:
      ParseError(location: SourceLocation, message: str)
  Domain Types:
      ParseConfig(max_depth: int = 100, strict: bool = False)
      AST (immutable, tree structure)
  Dependencies:
      tokenizer.TokenStream (input to Parser.parse via internal tokenization)
  """

  Then Read(base.py, limit=15) gives Tier 1 for ~50 tokens. Full read for behavioral contracts is only needed when you're actually implementing
  against it.

  This requires zero tooling — just a convention. And it's something I can actually exploit with my existing tools.

  Novel Idea 4: The Context Budget Protocol

  Instead of just saying "use Tier 0/1/2", what if templates gave agents explicit context budgets?

  ## Context Budget
  You have ~100K effective working tokens. Plan your reads:
  - Tier 0 (CLAUDE.md auto-loaded): ~2K tokens — FREE
  - Each Tier 1 module (base.py header): ~50-100 tokens via Read(limit=15)
  - Each Tier 1 full contract (base.py full): ~300-800 tokens
  - Each Tier 2 module (full source): ~1,500-3,000 tokens

  For this task (implementing module X):
  - Read Tier 1 headers for ALL adjacent modules: ~500 tokens (5 modules × 100)
  - Read Tier 1 full for modules you directly call: ~1,500 tokens (3 modules × 500)
  - Read Tier 2 for your own module: ~2,000 tokens
  - Total context for code understanding: ~4,000 tokens
  - Remaining for thinking/output: ~96K tokens

  This makes agents reason about context as a finite resource, not an infinite tape.

  ---
  Now let me walk through each of your original proposals with this context:

  Proposal 1: __init__.py Content Design

  Current State

  Your __init__.py files serve as manifests: English prose describing the module, its submodules, public API, dependencies, and design notes.
  Agents reading only __init__.py should understand the full project.

  What's Working

  The concept is right. Manifests are cheap (~100-300 tokens) and encode information tools can't extract: why decisions were made, how modules
  relate semantically, when to use one approach vs another.

  What's Not Working

  1. Double maintenance — manifest prose can drift from code reality
  2. No signatures — knowing "Parser exists" without knowing parse(str, ParseConfig) -> AST forces opening base.py
  3. Not auto-loaded — requires tool calls to discover and read

  My Recommendation

  Split __init__.py responsibilities:

  __init__.py handles Python-level concerns only:
  """Parser module — transforms source text into AST."""
  from .base import Parser, ParseError, ParseConfig, AST
  __all__ = ["Parser", "ParseError", "ParseConfig", "AST"]

  Tier 0 map lives in root CLAUDE.md (auto-loaded, free):
  ## parser/
  Parser: parse(source: str, config: ParseConfig) -> AST
  Depends on: tokenizer (TokenStream)
  Errors: ParseError(location, message)

  Tier 0.5 detail lives in parser/CLAUDE.md (auto-loaded when working in parser/):
  ## Parser Interface
  - Parser.parse(source, config) -> AST: Main entry point. Tokenizes internally.
  - Parser.validate(ast) -> ValidationResult: Post-parse validation.
  Design: Composition over inheritance. Parser wraps Tokenizer internally.
  Usage: `parser = create_parser(config); ast = parser.parse(source)`

  Why this is better:
  - Zero tool calls for Tier 0 (auto-loaded)
  - Zero tool calls for Tier 0.5 when working in that directory
  - __init__.py stays simple and Python-idiomatic
  - Design rationale and usage patterns still captured (in CLAUDE.md, not prose manifests)
  - Drift is detectable (Step 8 checks CLAUDE.md against reality)

  The Tradeoff

  You lose the "single source of truth" elegance of __init__.py-as-manifest. Now Tier 0 info lives in two places: CLAUDE.md (for agents) and
  __init__.py (for Python). But __init__.py was already doing two jobs poorly — Python import mechanism AND manifest. Splitting them lets each do
   its job well.

  What's your reaction to this split? Does putting Tier 0 in CLAUDE.md feel like it sacrifices the self-documenting codebase property?

  ---
  Proposal 2: Interface Documentation for Minimal Source Reading

  Current State

  Step 4 produces deliberately verbose docstrings in base.py. Step 8 trims them. Between Steps 4-8, docstrings serve as implementation
  blueprints.

  The Problem

  Verbose docstrings are great for the implementer (Step 6) but wasteful for adjacent module consumers (Steps 3, 5, 7) who only need to know how
  to call the interface, not its full behavioral contract.

  Layered Documentation Pattern

  I propose three documentation layers, each serving a different reader:

  Layer 1: Signature + type annotations (in the code itself, ~10 tokens per method)
  def parse(self, source: str, config: ParseConfig) -> AST: ...

  Layer 2: Contract summary (in CLAUDE.md or __init__.py comment, ~30 tokens)
  Parser.parse(source, config) -> AST: Tokenizes and parses source. Raises ParseError on invalid syntax.

  Layer 3: Full behavioral contract (in base.py docstring, ~100-200 tokens)
  def parse(self, source: str, config: ParseConfig) -> AST:
      """
      Pre: source is valid UTF-8, config.max_depth > 0
      Post: result is a well-formed AST matching source semantics
      Invariant: parse(s, c1) == parse(s, c2) when c1 == c2
      Raises: ParseError with location when source is syntactically invalid
      Perf: O(n) in source length for max_depth < 50
      """

  Who reads what:
  - Orchestrator (Step 3): Layer 2 (from CLAUDE.md, auto-loaded)
  - Test writer (Step 5): Layer 3 (reads base.py)
  - Implementer (Step 6): Layer 3 (reads base.py)
  - Adjacent module implementer: Layer 2 usually, Layer 3 if needed
  - Reconciler (Step 8): All layers (verifies consistency)

  .pyi Stub Files — An Underexplored Option

  Python has a native mechanism for type-only interface descriptions: .pyi files. They contain signatures and type annotations only — no
  implementation, no docstrings (optionally). They're what Pyright uses for type checking.

  # parser/base.pyi
  class Parser:
      def parse(self, source: str, config: ParseConfig) -> AST: ...
      def validate(self, ast: AST) -> ValidationResult: ...

  class ParseError(Exception):
      location: SourceLocation
      message: str

  Pros:
  - Standard Python mechanism, not framework-specific
  - Pyright/mypy enforces consistency with actual code
  - Extremely compact (~50 tokens per module)
  - Already understood by every Python tool

  Cons:
  - No behavioral contracts (just types)
  - Maintaining both .pyi and base.py is duplicative
  - Less useful for this pipeline where behavioral contracts matter

  Verdict: .pyi files are great for Tier 1 in general Python projects, but your pipeline specifically needs behavioral contracts (for Step 5 test
   formalization), so base.py with verbose docstrings remains the right Tier 1 vehicle. But .pyi could complement as a "Tier 0.75" — more than
  names, less than contracts.

  ---
  Proposal 3: AST/Inspect Tools vs Reading Source

  The Real Question

  Should agents use specialized code introspection tools, or should the code be organized so existing tools (Read, Grep) are sufficient?

  Option Analysis

  Option A: Python ast script in the repo

  # tools/inspect_interface.py
  import ast, sys

  def extract_interface(filepath):
      tree = ast.parse(open(filepath).read())
      for node in ast.walk(tree):
          if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
              # Extract name, args, returns, first-line docstring
              ...

  Agent usage: python tools/inspect_interface.py parser/base.py

  Output: ~200-350 tokens of structured signatures + docstrings (vs 500-800 for reading the file).

  Savings: ~50-60% over Read. But the tool call itself has overhead (Bash invocation, output parsing). Net savings are ~30-40% per file.

  Verdict: Moderate ROI. Useful for large files or when you need interface info for many files at once. But for a single base.py that's 100
  lines? Just Read it.

  Option B: MCP server (lsp-mcp, ast-grep, etc.)

  Native tool integration. Agent calls get_interface("parser") and gets structured JSON:
  {"classes": [{"name": "Parser", "methods": [{"name": "parse", "args": [...], "returns": "AST"}]}]}

  Savings: ~70-80% over Read. Native tool call, no Bash overhead, structured output.

  Verdict: High ROI for large projects. But introduces infrastructure dependency. Not portable across environments. Setup friction for
  contributors.

  Option C: Convention-only (better organized files + existing tools)

  No new tools. Instead:
  - base.py starts with structured header (readable via Read(limit=15))
  - CLAUDE.md files contain Tier 0/0.5 info (auto-loaded)
  - Templates teach Grep-before-Read patterns

  Savings: ~60-80% over naive Read. Zero infrastructure. Works everywhere.

  Verdict: Best ROI-to-complexity ratio. Especially for a scale-agnostic design.

  Option D: Hybrid — Convention + lightweight script

  Conventions for everyday use. Script available for batch operations (e.g., "give me all interfaces across 20 modules").

  My Recommendation

  Start with Convention (Option C), add script (Option D hybrid) when scale demands it.

  Reasons:
  1. Conventions work at any scale and have zero maintenance cost
  2. They degrade gracefully — if CLAUDE.md drifts, Read still works
  3. They're portable — no environment-specific tooling
  4. They teach agents good habits (Grep-first) that transfer to any project
  5. The ast script is ~50 lines and can be added when a project grows past 30 modules

  Reserve MCP servers for truly large projects (100+ modules) where the infrastructure cost is amortized across many agent sessions.

  ---
  Proposal 4: Grep Patterns for Agents

  The Untaught Skill

  Your templates say "read .current_session/" but never teach agents how to read efficiently. This is like telling someone to use a library
  without teaching them the card catalog.

  Proposed Grep Pattern Library

  Add this to the pipeline's meta-documentation or to CLAUDE.md:

  ## Efficient Code Discovery Patterns

  ### Tier 0: What exists
  Glob("**/__init__.py")  # ~10 tokens per module, all paths

  ### Tier 0.5: What interfaces exist
  Grep("^class ", glob="**/base.py")  # ~20 tokens per class name

  ### Tier 1: Signatures without bodies
  Grep("def |class |@abstract", path="module/base.py", output_mode="content")
  # ~50-100 tokens for full signature inventory

  ### Tier 1 targeted: Specific method signature
  Grep("def parse", path="parser/base.py", -A=5)  # signature + docstring start

  ### Tier 1: Error types
  Grep("class.*Error|class.*Exception", glob="**/base.py")

  ### Tier 1: Dependencies
  Grep("^from |^import ", path="module/base.py")  # what this module depends on

  ### Tier 2: Only when implementing
  Read("module/implementation_v1/impl.py")  # full source, own module only

  Where This Goes

  Two options:

  1. In each pipeline template — Step 6 template says "Before reading any file, use these Grep patterns to determine what you actually need..."
  2. In project CLAUDE.md — available to any agent session, not just pipeline steps

  I lean toward both: CLAUDE.md contains the pattern library, pipeline templates reference it and add step-specific guidance.

  ---
  Proposal 5: Tool-Use Instructions in Pipeline Templates

  Current Gap

  Templates describe what to read but not how to read efficiently. Step 6 says:
  "Tier 0 manifests — __init__.py files of all modules in the relevant subgraph"

  But doesn't say: "Use Glob to find them, then Read only the ones relevant to your module's dependencies."

  Proposed Addition to Each Template

  ## Context Loading Protocol

  **Phase 1 — Map (Tier 0, ~30 seconds)**
  1. CLAUDE.md module map is already in your context (auto-loaded)
  2. Identify which modules are relevant to your task from the map
  3. Skip modules not in your dependency subgraph

  **Phase 2 — Discover (Tier 0.5, ~1 minute)**
  4. For each relevant module: Read(module/CLAUDE.md) if it exists
  5. Or: Grep("^class |^def ", path="module/base.py") for signature inventory
  6. Determine which modules you need full Tier 1 for

  **Phase 3 — Contract (Tier 1, ~2 minutes)**
  7. For modules you directly call: Read(module/base.py)
  8. For modules you indirectly depend on: Tier 0.5 is sufficient

  **Phase 4 — Implement (Tier 2, your module only)**
  9. Read full source only for the module you own
  10. Never read Tier 2 of any other module

  **Anti-patterns:**
  - DON'T read all `__init__.py` files "just in case"
  - DON'T read `base.py` for modules you don't directly depend on
  - DON'T read implementation source for adjacent modules
  - DON'T re-read files you've already read (check your context first)

  Which Templates Need This?

  - Step 3 (Structural Analysis): Needs Tier 0 + selective Tier 1. Should use Grep heavily.
  - Step 4 (Interface Design): Needs Tier 0 + Tier 1 of adjacent modules. Should read base.py but can skip implementations.
  - Step 6 (Implementation): Most critical — explicit Tier 0/1/2 loading protocol.
  - Step 8 (Reconciliation): Needs to verify all tiers. Should read manifests and interfaces, but can Grep implementations for specific checks.

  ---
  Proposal 6: MCP Server for the Framework

  The Question

  Should this framework ship its own MCP server providing get_tier0(), get_tier1(module), search_requirements(query) etc.?

  Analysis

  For:
  - Formalizes tiered access as first-class tools
  - Agent calls get_tier1("parser") instead of figuring out which files to read
  - Can return pre-compressed, structured output
  - Can cache and invalidate intelligently
  - Could integrate with AST for always-accurate metadata

  Against:
  - Infrastructure dependency (Node.js/Python server must be running)
  - Setup friction for every contributor
  - Another thing to maintain and version
  - Convention-based approaches get you 80% of the benefit at 10% of the cost
  - MCP server is a solution looking for a problem if conventions work

  My Verdict

  Not yet. The convention-based approach (CLAUDE.md hierarchy + base.py headers + Grep patterns + template instructions) covers 80-90% of the
  context efficiency gains with zero infrastructure. Save MCP for when you hit a concrete wall that conventions can't solve.

  The one exception: if you're already using MCP servers for other purposes (database access, API tools, etc.), adding a code intelligence tool
  is incremental cost. But building MCP infrastructure specifically for this is premature.

  ---
  Summary: The Recommended Stack (Scale-Agnostic)

  ┌───────────────────────┬───────────────────────────────────────────────┬─────────────────────────┬───────────────────────────────────────────┐
  │         Layer         │                    Vehicle                    │          Cost           │                How Loaded                 │
  ├───────────────────────┼───────────────────────────────────────────────┼─────────────────────────┼───────────────────────────────────────────┤
  │ Tier 0 (project map)  │ Root CLAUDE.md                                │ ~1-2K tokens            │ Auto-loaded, FREE                         │
  ├───────────────────────┼───────────────────────────────────────────────┼─────────────────────────┼───────────────────────────────────────────┤
  │ Tier 0.5 (module      │ Module-level CLAUDE.md or __init__.py inline  │ ~50-150 tokens/module   │ Auto-loaded on directory entry, or        │
  │ summary)              │ comments                                      │                         │ Read(limit=15)                            │
  ├───────────────────────┼───────────────────────────────────────────────┼─────────────────────────┼───────────────────────────────────────────┤
  │ Tier 1 (full          │ base.py with structured header                │ ~300-800 tokens/module  │ Read on demand                            │
  │ contracts)            │                                               │                         │                                           │
  ├───────────────────────┼───────────────────────────────────────────────┼─────────────────────────┼───────────────────────────────────────────┤
  │ Tier 2 (full source)  │ Implementation files                          │ ~1,500-3,000            │ Read only for owned module                │
  │                       │                                               │ tokens/module           │                                           │
  ├───────────────────────┼───────────────────────────────────────────────┼─────────────────────────┼───────────────────────────────────────────┤
  │ Tooling               │ Grep pattern library in CLAUDE.md + optional  │ N/A                     │ Available to all agents                   │
  │                       │ ast script                                    │                         │                                           │
  ├───────────────────────┼───────────────────────────────────────────────┼─────────────────────────┼───────────────────────────────────────────┤
  │ Guidance              │ Context Loading Protocol in each pipeline     │ ~200 tokens in prompt   │ Part of agent instructions                │
  │                       │ template                                      │                         │                                           │
  └───────────────────────┴───────────────────────────────────────────────┴─────────────────────────┴───────────────────────────────────────────┘

  ---