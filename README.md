---
last_updated: 2026-10-06
---

# Todo Txt

## Short Description

Desktop todo.txt application with optional premium recurrence.

## Long Description

Todo Txt is a Windows desktop app for one-time tasks kept in a plain-text
`todo.txt` file, so other todo.txt apps and text editors can share the file.
Each task has a title, priority, due date, projects, contexts, optional notes,
and completion state. The file is the source of truth. Lines you do not change
stay as they were, saves stop if another app changed the file, and the app
warns about Dropbox conflicted copies. **Edit > Recurring Tasks...** opens an
opt-in recurring list kept apart from `todo.txt`. It is a local preview, and
subscription billing is not connected yet.

![Parts of a todo.txt line: completion mark, priority, completion and creation
dates, description, and project, context, and key:value
tags](assets/description.svg)

See the [User Manual](docs/USER_MANUAL.md) and
[Recurring Tasks](docs/RECURRING_TASKS.md) for details.

## Usage Examples

Requires Python 3.12 or later and [uv](https://docs.astral.sh/uv/). From the
repository folder, install the dependencies:

```powershell
uv sync
```

Start the app:

```powershell
.venv/Scripts/python.exe -m src.main
```

Choose your `todo.txt` file under **Edit > Settings...**, then restart the app
to use it.

Run the tests (install the dev tools first with `uv sync --group dev`):

```powershell
.venv/Scripts/python.exe -m pytest
```

## Glossary

- **todo.txt**: A plain-text task format with one task per line.
- **Due date**: The date a task should be done by, stored as `due:YYYY-MM-DD`.
- **Project**: A word starting with `+`, such as `+Home`, that groups tasks.
- **Context**: A word starting with `@`, such as `@phone`, for where or how a
  task gets done.
- **Archive**: The `done.txt` file that completed tasks move to.
