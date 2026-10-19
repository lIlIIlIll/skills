# Repository instructions

- Keep each skill self-contained under `skills/<skill-name>/`.
- Use lowercase kebab-case names and keep the folder name equal to the `name` in `SKILL.md`.
- Keep `SKILL.md` focused; route substantial mode-specific detail to `references/`.
- Do not add placeholders, generated caches, or duplicated documentation.
- Preserve automatic invocation unless a skill explicitly requires opt-in invocation.
- When changing a skill, run `python scripts/validate_skills.py` and `python -m unittest discover -s tests -v`.
- Run the upstream Skill Creator `quick_validate.py` as an additional check when it is available.

## Code Review Rules

- 对 `unified-code-review` 检查各 mode（pr/style/metrics/deep/architecture/fix）的读写边界：只读模式不得产生修改或隐式执行修复；缺乏可验证证据时应将发现降级为线索，不把风格或启发式度量误报为确认的正确性缺陷。
- 对 `clean-large-codebase` 检查 audit/plan/execute/verify/guard 的输入、状态和权限分离；重构不应改变功能或破坏用户已有改动。尺寸/复杂度阈值为信号而非单独的质量判决。
- 修改自动选择与 `SKILL.md` frontmatter 时，核对目录名与 skill name、trigger 描述、资源路径和 references；不要通过增加通用指令造成无关任务误触发。
- 报告有可复现步骤、契约违例和明确影响的阻塞问题。同一根因的对称/边界情形优先一次审查并归并；避免把已在 Review Thread 处理的问题重新包装为新问题。
- 修复提交的复审关注改动和受影响边界，同时仍指出真实的新缺陷；与当前 PR 无关的优化可以单独列为建议。

## Review 反馈处理与收敛

- 将审查意见按同根因分组，批量修复并更新覆盖正反和边界的 fixture/test，而不是“一条评论一次推送”。
- 变更 skill 时运行 `python scripts/validate_skills.py`、`python -m unittest discover -s tests -v`，可用时补充上游 `quick_validate.py`。实测结果须对应提交，未运行则注明。
- 合并判断依赖真实阻塞缺陷、验收和最新 HEAD 的 CI/Review 证据，不能把 Codex Thread 数量清零或轮数上限作为唯一标准。`AGENTS.md` 不会替代仓库 Review Trigger 配置。
