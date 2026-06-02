# Skills

This folder is for **project-local skills** — reusable, task-specific instructions
scoped to the Santé project. It is empty for now; add a subfolder per skill when a
repeatable workflow emerges (e.g. `add-report-type/`, `db-migration/`).

A skill is a folder containing a `SKILL.md` with YAML frontmatter:

```markdown
---
name: my-skill
description: Use when <trigger> — <what it does>.
---

<instructions>
```

## Superpowers plugin

The **Superpowers** plugin is installed globally (not in this folder) and is active
across sessions. It provides general-purpose skills such as `brainstorming`,
`writing-plans`, `executing-plans`, `test-driven-development`, `systematic-debugging`,
and `verification-before-completion`. Invoke them with the `Skill` tool; you do not
need to copy them here.

- Plans produced by `writing-plans` live in [../plans/](../plans/).
- Project context/memory lives in [../CLAUDE.md](../CLAUDE.md).
