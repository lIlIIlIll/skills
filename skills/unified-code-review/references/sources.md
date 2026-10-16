# Approach-to-source mapping (methodology only)

This Skill is an independently authored synthesis of *ideas* from public workflows rather than a verbatim collection. No upstream code is required at runtime, and external tools are optional. Review their own licensing/version if integrating their code directly.

| Approach | Upstream example | Adapted idea |
| --- | --- | --- |
| Defect-first read-only review | https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/review-agent/SKILL.md | Review a concrete diff and prioritize actionable defects |
| Evidence-driven review | https://github.com/akkie76/code-review-skills | Preconditions + impact; review scope, avoid unsupported claims |
| Independent reviewers/jury | https://github.com/khasky/awesome-agent-skills | Blind passes and final evidence-based adjudication when agents are available |
| Coding standards | https://github.com/khasky/awesome-agent-skills and https://github.com/affaan-m/ECC | Naming, readability, structure, consistent local conventions |
| Cleanup and over-abstraction | https://github.com/khasky/awesome-agent-skills | Detect stale comments, useless wrappers, duplicated concepts; no implicit modification |
| Maintainability review | https://github.com/mthines/agent-skills | Low cognitive burden, guard clauses, simple architecture, avoid overengineering |
| Quantitative metrics | https://skillmd.com/skills/saturate/code-metrics | LOC / complexity / token duplication as triage, not mandates |
| Structural hotspot workflow | https://github.com/eabs86/complexity-analyzer | Metric hotspot ranking followed by manual source verification |
| Architectural review | https://github.com/paulpas/agent-skill-router | Coupling/cohesion and boundary-level consequences with measured evidence |
| Skill packaging | https://agentskills.io/specification | YAML frontmatter and progressive disclosure |

**Why not bundle upstream executables?** The sources have different licenses, language support, versioning and installation risk. Their best review practices can be coordinated without copying third-party code or implying that unsupported metrics exist for Cangjie.
