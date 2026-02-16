# Skill: `/interface` — Interface Metadata Extraction

## Purpose

Provides agents with compressed interface information at configurable depth, avoiding the need to read full source files. Wraps `tools/inspect_interface.py`.

## Registration

Add to your Claude Code project configuration (`.claude/commands/interface.md`):

```markdown
Extract interface metadata from Python modules using the AST inspection tool.

Usage: /interface <path> [options]

Run the following command with the provided arguments:
python tools/inspect_interface.py $ARGUMENTS
```

Alternatively, register as a project-level slash command by creating `.claude/commands/interface.md` with the above content.

## Usage Examples

```bash
# Tier 0.5: What interfaces exist in a module (names + signatures)
/interface parser/

# Tier 0: Just class/function names
/interface parser/ --depth=0

# Tier 1 full: Signatures + docstrings
/interface parser/base.py --depth=2

# Module-level docstring only (structured header)
/interface parser/base.py --module-doc

# Entire project, only base.py files
/interface . --only-base

# Verify CLAUDE.md accuracy
/interface . --only-base --verify=CLAUDE.md
```

## When to Use

| Situation | Use This | Not This |
|---|---|---|
| Need to know what API a module exposes | `/interface module/` | Read entire `base.py` |
| Need full behavioral contracts | Read `base.py` directly | `/interface --depth=2` (still misses context) |
| Need to understand many modules quickly | `/interface . --only-base` | Reading each `__init__.py` |
| Need a specific method's types | LSP hover | `/interface` (overkill for one method) |
| Need implementation details | Read `impl.py` (Tier 2) | Neither — this is interface-only |

## Integration with Tiered Context Model

- **Tier 0 (CLAUDE.md):** Already in context — no tool needed
- **Tier 0.5:** `/interface <module> --depth=0` → ~20 tokens/module
- **Tier 1 compressed:** `/interface <module> --depth=1` → ~100 tokens/module
- **Tier 1 full:** `/interface <module> --depth=2` → ~300 tokens/module
- **Tier 2:** Read implementation files directly — `/interface` doesn't help here
