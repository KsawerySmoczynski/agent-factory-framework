---
name: interface
description: >
  Extract compressed interface metadata from Python modules at configurable depth levels.
  Use when you need to understand module APIs, class signatures, or type contracts without
  reading full source files. Provides Tier 0.5 and Tier 1 context in the tiered context model.
argument-hint: <path> [--depth=0|1|2] [--only-base] [--module-doc] [--verify=CLAUDE.md]
allowed-tools: Bash(python *)
---

# Interface Metadata Extraction

Extract interface metadata from Python modules using AST inspection. Wraps a bundled Python script that parses source files and returns compressed interface descriptions at configurable depth.

Run from the project root:

```bash
python .claude/skills/interface/scripts/inspect_interface.py $ARGUMENTS
```

## Depth Levels

| Depth | Content | ~Tokens/Module | Context Tier |
|-------|---------|----------------|--------------|
| 0 | Class/function names only | ~20 | Tier 0.5 |
| 1 | Names + signatures + type annotations (default) | ~100 | Tier 1 compressed |
| 2 | Names + signatures + docstrings | ~300 | Tier 1 full |

## Options

- `--depth=N` — Detail level: 0=names, 1=signatures (default), 2=signatures+docstrings
- `--format=text|json` — Output format (default: text)
- `--only-base` — Only inspect `base.py` files (skip implementations)
- `--module-doc` — Extract only module-level docstrings
- `--verify=CLAUDE_MD_PATH` — Verify CLAUDE.md module map matches code

## Usage Examples

```bash
# Tier 0.5: What interfaces exist in a module (names + signatures)
/interface parser/

# Just class/function names (~20 tokens/module)
/interface parser/ --depth=0

# Tier 1 full: Signatures + docstrings (~300 tokens/module)
/interface parser/base.py --depth=2

# Module-level docstring only (structured header)
/interface parser/base.py --module-doc

# Entire project, only base.py files
/interface . --only-base

# JSON output for programmatic use
/interface parser/ --format=json

# Verify CLAUDE.md accuracy against actual code
/interface . --only-base --verify=CLAUDE.md
```

## When to Use

| Situation | Use `/interface` | Use Something Else |
|---|---|---|
| Need to know what API a module exposes | `/interface module/` | Not: read entire `base.py` |
| Need full behavioral contracts | Read `base.py` directly | Not: `/interface --depth=2` (misses context) |
| Need to understand many modules quickly | `/interface . --only-base` | Not: reading each `__init__.py` |
| Need a specific method's types | LSP hover | Not: `/interface` (overkill for one method) |
| Need implementation details | Read `impl.py` (Tier 2) | Neither — this tool is interface-only |

## Integration with Tiered Context Model

Load context progressively — cheapest first, drill deeper only when needed:

- **Tier 0 (CLAUDE.md):** Already in context — no tool needed
- **Tier 0.5:** `/interface <module> --depth=0` — ~20 tokens/module
- **Tier 1 compressed:** `/interface <module> --depth=1` — ~100 tokens/module
- **Tier 1 full:** `/interface <module> --depth=2` — ~300 tokens/module
- **Tier 2:** Read implementation files directly — `/interface` doesn't help here
