# Reproduction Prompt — {feature/module}

> contract author（evidence-first-repro）が生成し、implementation agent にそのまま渡す 1 本のプロンプト。
> このプロンプトは mini-spec。`memory/contracts/{feature-module}.md` に保存する。
> **contract author は新しい事実を足さない。以下の Facts は facts-sheet の source 付き行のみから転記する。**

---

You are {Codex|Claude Code}, an implementation agent. Reproduce the **{feature/module}** feature of the studied product as a localhost prototype.

## Role

- Recreate only the structure and behavior described in the facts below.
- The appearance is fixed by the house design system — you do not design look-and-feel.

## Use only the facts below

Use **only** the following facts. Do not add features, screens, data, or behavior that are not listed here.

- {fact 1（source 付き事実からの転記）}
- {fact 2}
- {fact 3}
- ...

## Implementation rules

- **Limit strictly to the facts above.** If a detail is not in the facts, do not implement it.
- **Do NOT invent a generic SaaS dashboard, analytics overview, or CRM-like UI.** No charts, KPI tiles, activity feeds, or filler sections unless they appear in the facts.
- **Import UI ONLY from the house design system at `{design system path}`** (UI kit + prototype shell). **Author no new styles / no bespoke CSS.** If a needed element is missing from the kit, use the closest existing component — do not create a new visual style.
- **Make the route reachable under `{target route}`.** Wire it into the app so it can be opened directly.
- **Keep the UI specific to this module ({feature/module}).** Do not add navigation, settings, or surfaces belonging to other modules.

## Verification

- Update the code so that `{target route}` renders locally.
- Run the build; the page must compile with no errors.
- The rendered result must **match the facts, not an invented appearance** — every visible element must trace back to a fact above.
- Remove any UI you added that is not backed by a fact.

**Return the changed code directly.**

---

## Optional extra constraints（必要に応じて有効化）

- Use only official sources (no third-party or speculative descriptions).
- Use only facts present in the facts-sheet (nothing from memory or assumption).
- Produce no explanatory essay / prose write-up.
- Produce no product strategy or positioning commentary.
- Do not infer or add a user story.
- Do not produce a speculative "missing feature" list.
