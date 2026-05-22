---
description: Regenerate `.github/skills/_registry.md` from real `SKILL.md` frontmatter and verify the registry matches disk.
---

# Sync Skills Registry

Regenerate `.github/skills/_registry.md` from the actual `SKILL.md` files under `.github/skills/`.

## Requirements

- Use `.github/tools/pool-sync/generate_registry.py` as the source of truth.
- The registry must be generated from `name` and `description` frontmatter in each public `SKILL.md`.
- Exclude private skills and denylist-exception paths through the manifest loader; do not hardcode a separate private list here.
- Preserve deterministic category ordering and path sorting.
- Do not hand-edit `_registry.md`.

## Workflow

1. Run:

```bash
python .github/tools/pool-sync/generate_registry.py
```

2. Verify:

```bash
python .github/tools/pool-sync/generate_registry.py --check
python validate_pool.py
```

3. If validation fails because a skill is missing `name` or `description`, fix the `SKILL.md` frontmatter and rerun the generator.

## Success Criteria

- `.github/skills/_registry.md` matches the generated output exactly.
- New public skills, including `workflow/golden-nuggets/`, appear automatically after regeneration.
- `validate_pool.py` passes.
