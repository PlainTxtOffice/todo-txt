# AGENTS.md

- Follow MVC boundaries in `src/gui/`.
- Views own Qt widgets, input collection, rendering, and user prompts.
- Delegate task commands and preference persistence to
  `src/gui/controllers/`; keep controllers independent of Qt.
- Task rules belong in `src/domains/tasks/`; archive workflows belong in
  `src/application/`, with filesystem operations in adapters.
