---
last_updated: 2026-09-28
version: 3.0.1
product_version: "1.0.0"
generated_from: "dev-docs/specs/USER_MANUAL_SPEC.instructions.md"
---

# User Manual

## Overview

Todo Txt is a Windows desktop program for keeping a list of one-time tasks.
Your tasks live in a plain-text `todo.txt` file, one task per line, so you can
also open the same file in other todo.txt apps or a text editor. The file is
the source of truth: the window shows what is in the file, and every change
you make in the window is written back to it straight away.
<!-- Verified from: pyproject.toml [project.description] -->
<!-- Verified from: src/gui/controllers/tasks.py [TaskController._persist] -->

It is for people who keep their tasks in the todo.txt format, including those
who share the file between devices with Dropbox. The program has one
interface: a desktop window with menus, a task list, and a task editor.
<!-- Verified from: src/gui/views/root_window/window.py [TodoMainWindow] -->
<!-- Verified from: src/adapters/storage/todo_text.py [TodoTextStore.find_conflicted_copies] -->

Each task can have a title, priority, due date, notes, completion state,
projects (`+Home`), contexts (`@phone`), and extra `key:value` tags. Notes are
an addition of this program. They are kept in the program's own data folder,
not in `todo.txt`.
<!-- Verified from: src/domains/tasks/models.py [Todo] -->
<!-- Verified from: src/adapters/storage/notes.py [NotesStore] -->
<!-- Verified from: dev-docs/specs/todo_spec.md -->

This manual covers using the program once it is running. Installation and
setup are not covered.

## Starting the Program

### Open The Window

From the project folder, run:

```powershell
.venv/Scripts/python.exe -m src.main
```

There is no separate installed command.
<!-- Verified from: src/main.py [main] -->
<!-- Verified from: pyproject.toml [project.scripts] -->

When the program starts it:

1. Reads its settings, creating the settings file with default values if it
   does not exist yet.
1. Loads your `todo.txt` file. If the file does not exist, the list starts
   empty.
1. Opens the **Todo Txt** window.
1. Warns you about any Dropbox conflicted copies of your file, and offers to
   locate the file if it is missing. See
   [Prompts When The Window Opens](#prompts-when-the-window-opens).
<!-- Verified from: src/config/settings.py [load_settings] -->
<!-- Verified from: src/adapters/storage/todo_text.py [TodoTextStore.load_todos] -->
<!-- Verified from: src/gui/views/root_window/window.py [TodoMainWindow.__init__] -->

### Close The Program

Choose **File > Exit**, press `Ctrl+Q`, or close the window. Saved tasks are
already in `todo.txt`. If the editor has changes you have not saved, you are
asked what to do with them first. See
[Save Or Discard Unsaved Changes](#save-or-discard-unsaved-changes).
<!-- Verified from: src/gui/views/menu_bar/main_menu.py [build_menu_bar] -->
<!-- Verified from: src/gui/views/root_window/window.py [TodoMainWindow.closeEvent] -->

## Getting Around

The window has a menu bar across the top, the task list on the left, and the
task editor on the right. Click a task in the list to show it in the editor.
Most commands are also on the menus, and many have keyboard shortcuts. See
[Commands and Shortcuts](#commands-and-shortcuts).
<!-- Verified from: src/gui/views/root_window/panes/task_view.py [TaskView.__init__] -->
<!-- Verified from: src/gui/views/menu_bar/main_menu.py [build_menu_bar] -->

**Help > About** shows the program name and a short description. There is no
other built-in help.
<!-- Verified from: src/gui/views/menu_bar/main_menu.py [_show_about] -->

### Read The Task List

Each row in the task list has a checkbox that is ticked when the task is
complete, followed by the task's line exactly as it is written in `todo.txt`.
For example: `(A) 2026-09-20 Pay rent due:2026-10-01`. In that line,
`2026-09-20` is the creation date and `due:2026-10-01` is the due date. See
[Understand todo.txt Lines](#understand-todotxt-lines).
<!-- Verified from: src/gui/views/root_window/panes/task_view.py [TaskView._build_task_entry] -->
<!-- Verified from: src/adapters/export.py [format_todo_line] -->

A row too long for the list wraps onto more lines and rewraps when you resize
the window. Wrapping only changes the display. Each task is still one line in
`todo.txt`.
<!-- Verified from: src/gui/views/root_window/panes/task_view.py [TaskView.__init__] -->

To show shorter labels instead, untick **View > Show todo.txt Lines**. Each
row then shows:

- the priority in brackets, such as `(A)`, when the task has one
- the due date, or `No due date`
- a dash and the task title

For example: `(A) 2026-10-01 - Pay rent`. Your choice is remembered the next
time you start the program.
<!-- Verified from: src/gui/views/root_window/task_labels.py [format_task_label] -->
<!-- Verified from: src/gui/views/menu_bar/view_menu.py [build_view_menu] -->

When a grouping is selected in the **View** menu, a bold header row such as
`Overdue` or `+Home` appears above each group. Header rows cannot be selected.
See [Group The Task List](#group-the-task-list).
<!-- Verified from: src/gui/views/root_window/panes/task_view.py [_build_group_header] -->

### Use The Task Editor

The editor on the right has these parts, from top to bottom:

| Part | What it does |
| --- | --- |
| **File Path** | Shows the `todo.txt` file in use, for reference only. A long path is shortened in the middle. Point at it to see the full path. To change the file, see [Switch To Another todo.txt File](#switch-to-another-todotxt-file). |
| Task title | The task's title. |
| Priority list | **No priority** or a letter such as **(A)**. |
| **Due date** | Tick the box to give the task a due date, then pick the date. Click the arrow for a calendar. In the calendar, today's date is outlined, and **Today** jumps to the current month without changing the date. The day of the week, such as `Wednesday`, is shown below the date unless **Date display** already includes it. |
| Notes | Optional notes. |
| **New** | Clears the editor to start a new task. |
| **Save** | Saves the task shown in the editor. |
| **Complete** | Saves the selected task and marks it complete. Reads **Reopen** when the selected task is already complete. |
| **Delete** | Deletes the selected task. |
| **Export** | Writes a copy of your tasks to another file. |
<!-- Verified from: src/gui/views/root_window/panes/task_editor.py [TaskEditorPane.__init__] -->
<!-- Verified from: src/gui/views/root_window/panes/task_editor.py [_FilePathLabel] -->
<!-- Verified from: src/gui/views/root_window/panes/task_editor.py [_build_due_calendar] -->
<!-- Verified from: src/gui/views/root_window/panes/task_editor.py [_DueCalendar.paintCell] -->
<!-- Verified from: src/gui/views/root_window/panes/task_editor.py [TaskEditorPane.set_date_display_format] -->

**Complete** and **Delete** are unavailable until you click a task in the list.
<!-- Verified from: src/gui/views/root_window/panes/task_editor.py [TaskEditorPane.set_completion_state] -->

### Prompts When The Window Opens

| Window title | When it appears | What to do |
| --- | --- | --- |
| **Dropbox Conflicted Copies** | Files beside `todo.txt` have `conflicted copy` in their names. | Compare them with `todo.txt` and merge anything you need before deleting them. |
| **Todo File Missing** | The configured `todo.txt` cannot be found. | Choose **Yes** to open Settings and pick the file. |
<!-- Verified from: src/gui/views/root_window/window.py [TodoMainWindow._show_conflicted_copy_alert] -->
<!-- Verified from: src/gui/views/root_window/window.py [TodoMainWindow._locate_missing_file] -->
<!-- Verified from: src/adapters/storage/todo_text.py [TodoTextStore.find_conflicted_copies] -->

If you choose a different file in Settings from the **Todo File Missing**
prompt, the program closes. Start it again to use that file.
<!-- Verified from: src/gui/views/root_window/window.py [TodoMainWindow._locate_missing_file] -->

### When Another App Changes The File

The program watches `todo.txt` while it is open. If another program or
Dropbox changes the file, a **Todo File Changed** prompt asks whether to
reload it. Choose **Yes** to load the new version. Anything unsaved in the
window is discarded.
<!-- Verified from: src/gui/views/root_window/window.py [TodoMainWindow._shared_file_changed] -->

## Everyday Tasks

### Add A Task

1. Choose **Edit > New Task**, press `Ctrl+N`, or click **New**.
1. Type a title.
1. Type any projects, such as `+Home +Work`, or pick them from **Add project**.
1. Pick **No priority** or a priority letter.
1. To give the task a due date, tick **Due date** and pick the date.
1. Type any notes.
1. Click **Save**.

The task is written to `todo.txt` straight away, and the editor clears so you
can add another.
<!-- Verified from: src/gui/views/root_window/panes/task_view.py [TaskView.save_task] -->

### Fill In The Editor Fields

| Field | What to enter |
| --- | --- |
| Task title | Required. Leaving it blank shows a **Validation** message: `title is required`. |
| Projects | Optional. Separate project names with spaces. The `+` in front of each name is optional, so `Home Work` and `+Home +Work` both work. Pick a project from the **Add project** dropdown to add one already in `todo.txt`. |
| Priority | **No priority**, or a letter from the range set in Settings. The default range is **(A)** to **(E)**. |
| **Due date** | Optional. Leave the box unticked for no due date. When ticked, the date starts at today. |
| Notes | Optional free text, on as many lines as you like. |
<!-- Verified from: src/gui/views/root_window/panes/task_editor.py [TaskEditorPane] -->
<!-- Verified from: src/domains/tasks/models.py [TaskBoard.create_todo] -->
<!-- Verified from: src/config/settings.py [BUILT_IN_SETTINGS] -->

### What The Program Records For You

- **Creation date**: today's date is added to each new task.
- **Position**: new tasks are added at the end of `todo.txt`.
<!-- Verified from: src/domains/tasks/models.py [TaskBoard.create_todo] -->
<!-- Verified from: src/adapters/storage/todo_text.py [TodoTextStore._in_file_order] -->

### Add Projects And Contexts

Type projects in the **Projects** box, for example `+Home +Work`. They are
saved to `todo.txt` with the task and can be used for sorting and grouping.
<!-- Verified from: src/gui/views/root_window/panes/task_editor.py [TaskEditorPane.task_values] -->

To reuse a project, pick it from the **Add project** dropdown beside the box.
The dropdown lists every project in `todo.txt`, A to Z. Picking one adds it to
the end of the box, unless the task already has it. The dropdown is greyed out
until at least one task has a project.
<!-- Verified from: src/gui/views/root_window/panes/task_editor.py [TaskEditorPane.set_known_projects] -->
<!-- Verified from: src/domains/tasks/models.py [TaskBoard.list_projects] -->

Contexts do not have their own box. Type them in the title, for example
`Call plumber @phone`. The program recognizes words starting with `@` as
contexts, and words starting with `+` as projects, the next time it loads the
file. After that, projects typed in the title appear in the **Projects** box.
<!-- Verified from: src/adapters/export.py [_parse_body_tokens] -->

### How Notes Are Stored

Notes are saved in `notes.json` in the program's data folder, never in
`todo.txt`. See [Where Your Files Live](#where-your-files-live). Each note is
matched to its task by the task's creation date and title. So a note stays
with its task when another app completes it or changes its priority, due
date, projects, or contexts.
<!-- Verified from: src/adapters/storage/notes.py [NotesStore] -->
<!-- Verified from: src/adapters/export.py [format_todo_line] -->

A note moves with its task when you rename the task in this program. It is
removed when you delete or archive the task. If another app changes a task's
title, the note no longer matches and does not appear. It stays in
`notes.json`, and it comes back if the title is changed back.
<!-- Verified from: src/adapters/storage/notes.py [NotesStore.save_notes] -->

### Edit A Task

1. Click a task in the list. Its details appear in the editor.
1. Change the title, projects, priority, due date, or notes.
1. Click **Save**.
<!-- Verified from: src/gui/views/root_window/panes/task_view.py [TaskView._select_task] -->
<!-- Verified from: src/gui/views/root_window/panes/task_view.py [TaskView.save_task] -->

To remove a due date, untick **Due date** and click **Save**. A task with no
due date shows **Due date** unticked.
<!-- Verified from: src/gui/views/root_window/panes/task_editor.py [TaskEditorPane._show_due_date] -->
<!-- Verified from: src/gui/views/root_window/panes/task_editor.py [TaskEditorPane.task_values] -->

If a task was given a priority outside your Settings range, for example in
another app, that priority still appears in the list and is kept unless you
change it.
<!-- Verified from: src/gui/views/root_window/panes/task_editor.py [TaskEditorPane.set_priority_range] -->

### Save Or Discard Unsaved Changes

If you change a task in the editor and then click another task, click
**New**, press `Ctrl+N`, or close the window without saving, an
**Unsaved Changes** prompt asks `Save changes to "<task title>"?`. For a new
task that has not been saved yet, it asks `Save changes to the new task?`.

| Button | What happens |
| --- | --- |
| **Save** | Saves your changes, then carries on. If the title is blank, a **Validation** message appears and you stay on the task. |
| **Discard** | Drops your changes, then carries on. |
| **Cancel** | Stays on the task you were editing, with your changes kept. |
<!-- Verified from: src/gui/views/root_window/panes/task_view.py [TaskView.resolve_unsaved_changes] -->
<!-- Verified from: src/gui/views/root_window/panes/task_view.py [TaskView._select_task] -->

Only real changes count. If you change a field and then change it back, or
only add spaces around the title or notes, there is nothing to save and no
prompt appears. **Save**, **Complete**, and ticking a checkbox in the list do
not ask. A **Todo File Changed** reload still discards unsaved changes, as
its prompt says.
<!-- Verified from: src/gui/views/root_window/panes/task_editor.py [TaskEditorPane.has_unsaved_changes] -->
<!-- Verified from: src/gui/views/root_window/panes/task_view.py [TaskView.reload_tasks] -->

### Complete A Task

Tick the task's checkbox in the list. The change is saved at once and today's
date is recorded as the completion date. The due date is not changed.
Untick the box to mark the task open again. This removes the completion date.
<!-- Verified from: src/gui/views/root_window/panes/task_view.py [TaskView._toggle_task] -->
<!-- Verified from: src/domains/tasks/models.py [Todo.set_completed] -->

You can also complete the task shown in the editor:

1. Click the task in the list.
1. Click **Complete**, choose **Edit > Toggle Complete**, or press
   `Ctrl+Enter`.

Any changes you made in the editor are saved first. The editor then clears
for a new task. For a completed task the button reads **Reopen**, and using it
marks the task open again.
<!-- Verified from: src/gui/views/root_window/panes/task_view.py [TaskView.complete_selected] -->
<!-- Verified from: src/gui/views/menu_bar/main_menu.py [build_menu_bar] -->

### Delete A Task

1. Click the task in the list.
1. Click **Delete**, choose **Edit > Delete Task**, or press `Delete`.

The task is removed from `todo.txt` at once, with no confirmation. The
**Delete** button is unavailable until a task is selected. If you use the menu
or press `Delete` with no task selected, a message says `Select a task first.`
<!-- Verified from: src/gui/views/root_window/panes/task_view.py [TaskView.delete_selected] -->

### Archive Completed Tasks

1. Choose **File > Archive Completed** or press `Ctrl+Shift+A`.
1. When asked `Move N completed task(s) to done.txt?`, click **Yes**.
<!-- Verified from: src/gui/views/root_window/panes/task_view.py [TaskView.archive_completed] -->

Completed tasks are added to the end of `done.txt` and then removed from
`todo.txt`. Existing lines in `done.txt` are kept. If there is nothing to
archive, a message says `There are no completed tasks to archive.` If
`todo.txt` changed in another app, nothing is archived and you are offered a
reload.
<!-- Verified from: src/application/archive.py [archive_completed_todos] -->
<!-- Verified from: src/adapters/storage/done_text.py [DoneTextStore.append_lines] -->

### Sort The Task List

Choose **View > Sort By** and pick an order. A checkmark shows the current
choice. Your choice is remembered the next time you start the program. It
only changes the window and never reorders `todo.txt`.
<!-- Verified from: src/gui/views/menu_bar/view_menu.py [build_view_menu] -->
<!-- Verified from: src/gui/views/root_window/panes/task_view.py [TaskView._write_view_settings] -->

| Sort By | Order |
| --- | --- |
| **Completion** | Open tasks first, then by due date, then by title. This is the default. |
| **Due Date** | Earliest due date first. |
| **Priority** | `(A)` first through `(Z)`. |
| **Created Date** | Oldest creation date first. |
| **Alphabetical** | By title, ignoring capital letters. |
| **Project** | By the first project on each task, A to Z. |
| **Context** | By the first context on each task, A to Z. |
<!-- Verified from: src/domains/tasks/arrangement.py [_SORT_KEYS] -->

For every order except **Completion** and **Alphabetical**, tasks without the
sorted detail come last. Ties are settled by open before completed, then
priority, then due date, then title.
<!-- Verified from: src/domains/tasks/arrangement.py [_calc_tiebreak] -->

### Group The Task List

Choose **View > Group By** and pick a grouping. Tasks inside each group follow
the current sort order. Groups with no tasks are not shown. Like the sort
order, your choice is remembered and never changes `todo.txt`.
<!-- Verified from: src/gui/views/root_window/panes/task_view.py [TaskView.set_group_by] -->

| Group By | Groups, in order |
| --- | --- |
| **None** | No groups. This is the default. |
| **Completion** | `Active`, `Completed` |
| **Due Date** | `Overdue`, `Today`, `Next 7 Days`, `Later`, `No Due Date` |
| **Priority** | `Priority A` through `Priority Z`, then `No Priority` |
| **Project** | One group per project, such as `+Home`, A to Z, then `No Project` |
| **Context** | One group per context, such as `@phone`, A to Z, then `No Context` |
<!-- Verified from: src/domains/tasks/arrangement.py [group_todos] -->

**Due Date** groups use your computer's current date. `Next 7 Days` covers
tomorrow through seven days from today. A completed task is placed by its due
date like any other task.
<!-- Verified from: src/domains/tasks/arrangement.py [_calc_due_label] -->
<!-- Verified from: src/gui/views/root_window/panes/task_view.py [TaskView.refresh_list] -->

A task with more than one project or context appears under each of them.
<!-- Verified from: src/domains/tasks/arrangement.py [_calc_group_labels] -->

### How Changes Reach todo.txt

Each save rewrites only the lines you changed. Lines you did not touch are
kept exactly as they were, including any formatting from other apps, and
tasks keep their place in the file. Sorting and grouping in the window never
change the order of lines in the file.
<!-- Verified from: src/adapters/storage/todo_text.py [TodoTextStore.render_line] -->
<!-- Verified from: src/adapters/storage/todo_text.py [TodoTextStore._in_file_order] -->

Before each save, the program checks that `todo.txt` has not changed since it
was loaded. If it has, nothing is written. A **Todo File Changed** prompt
offers to reload the file and discard your unsaved change.
<!-- Verified from: src/adapters/storage/todo_text.py [TodoTextStore.ensure_current] -->
<!-- Verified from: src/gui/views/root_window/panes/task_view.py [TaskView._offer_reload] -->

## Settings and Preferences

Settings are saved in `settings.json` and kept between runs. Changes in the
settings window are saved when you click **Save**. **View** menu choices are
saved as soon as you pick them. See
[Where Your Files Live](#where-your-files-live).
<!-- Verified from: src/config/settings.py [save_settings] -->
<!-- Verified from: src/gui/views/root_window/panes/task_view.py [TaskView._write_view_settings] -->

### Change Settings In The Window

1. Choose **Edit > Settings...** or press `Ctrl+,`.
1. Change the fields below.
1. Click **Save**, or **Cancel** to discard your changes.

| Field | What to enter |
| --- | --- |
| **Minimum priority** | The first priority letter offered in the editor. |
| **Maximum priority** | The last priority letter offered in the editor. It cannot come before **Minimum priority**. |
| **Date display** | `2026-01-14` or `Wed, Jan 14, 2026`. |
| **Todo file** | The `todo.txt` file to use. Click **Browse...** to pick one. |
<!-- Verified from: src/gui/views/settings/settings_dialog.py [SettingsDialog] -->

Priority and date display changes apply to the open window straight away.
**Date display** only changes how dates look in the editor and in the
shorter list labels. Dates in `todo.txt`, and in list rows that show
`todo.txt` lines, are always written as `YYYY-MM-DD`.
<!-- Verified from: src/gui/views/menu_bar/main_menu.py [_edit_settings] -->
<!-- Verified from: src/adapters/export.py [format_todo_line] -->

The priority range only limits the choices in the editor. Any valid priority
from `A` to `Z` already in `todo.txt` is still shown and kept.
<!-- Verified from: src/domains/tasks/models.py [_clean_priority] -->

### Switch To Another todo.txt File

1. Open **Edit > Settings...**.
1. Click **Browse...** next to **Todo file** and pick an existing file.
1. Click **Save**.
1. Answer the archive prompt, if one appears. See the table below.
1. When the message says `Todo Txt will close. Restart it to use the selected
   file.`, click **OK**. Then start the program again.
<!-- Verified from: src/gui/views/settings/settings_dialog.py [SettingsDialog._save] -->

If your completed-task archive (`done.txt`) sits beside the old file, the
program asks what to do with it:

| Prompt | Choices |
| --- | --- |
| **Move Completed-Task Archive** | **Yes** moves `done.txt` to the new folder. **No** leaves it in place and starts a new `done.txt` in the new folder. **Cancel** stops the change. |
| **Archive Already Exists** | **Merge** adds the old archive's lines to the end of the new folder's `done.txt` and keeps duplicate lines. **Overwrite...** replaces the new folder's `done.txt` after a second confirmation. **Use Existing** leaves both files as they are. **Cancel** stops the change. |
<!-- Verified from: src/gui/views/settings/archive_prompt.py [ask_archive_move] -->
<!-- Verified from: src/application/file_change.py [save_file_settings] -->

### Settings Error Messages

| Message | Fix |
| --- | --- |
| `Minimum priority must come before maximum priority.` | Pick a minimum that comes before or equals the maximum. |
| `Select a todo.txt file.` | Enter or browse to a file. |
| `Select an existing todo.txt file.` | Pick a file that already exists. |
| `Could not save settings: ...` | Check that the settings file can be written, then try again. |
<!-- Verified from: src/gui/views/settings/settings_dialog.py [SettingsDialog._save] -->

### Edit The Settings File

Settings are stored as JSON in `settings.json`. Close the program before
editing the file by hand. Your edits take effect the next time the program
starts. The program keeps any keys it does not use.
<!-- Verified from: src/config/settings.py [load_settings] -->

| Setting | Default | Accepted values | How to change it |
| --- | --- | --- | --- |
| `priority.minimum` | `A` | One capital letter `A` to `Z` | **Minimum priority** in **Edit > Settings...** |
| `priority.maximum` | `E` | One capital letter `A` to `Z` | **Maximum priority** in **Edit > Settings...** |
| `dateDisplayFormat` | `iso` | `iso` or `weekday_short` | **Date display** in **Edit > Settings...** |
| `todoFile` | `data/todo.txt` | Path to `todo.txt` | **Todo file** in **Edit > Settings...** |
| `doneFile` | `done.txt` beside `todoFile` | Path to the archive file | `settings.json` only |
| `sortOrder` | `completion` | `completion`, `due_date`, `priority`, `created`, `alphabetical`, `project`, `context` | **View > Sort By** |
| `groupBy` | `none` | `none`, `completion`, `due_date`, `priority`, `project`, `context` | **View > Group By** |
| `showFileLines` | `true` | `true` or `false` | **View > Show todo.txt Lines** |
<!-- Verified from: src/config/settings.py [load_settings] -->
<!-- Verified from: src/config/settings.py [save_settings] -->
<!-- Verified from: src/config/settings.py [BUILT_IN_SETTINGS] -->
<!-- Verified from: src/gui/views/menu_bar/view_menu.py [build_view_menu] -->

Example:

```json
{
  "priority": {
    "minimum": "A",
    "maximum": "E"
  },
  "todoFile": "C:/Users/you/Dropbox/todo/todo.txt",
  "dateDisplayFormat": "iso",
  "sortOrder": "due_date",
  "groupBy": "project",
  "showFileLines": true
}
```

If a value is not accepted, the program will not start until it is fixed.
If you set `doneFile`, the archive stays at that path when you switch
`todo.txt` files.
<!-- Verified from: src/config/settings.py [_parse_priority_bound] -->
<!-- Verified from: src/gui/views/settings/archive_prompt.py [ask_archive_move] -->

## Importing and Exporting

The program exports your tasks as a todo.txt file. There is no import command.
To work with tasks from another todo.txt file, point the program at that file.
See [Switch To Another todo.txt File](#switch-to-another-todotxt-file).
<!-- Verified from: src/gui/views/menu_bar/main_menu.py [build_menu_bar] -->

### Export A Copy Of Your Tasks

1. Choose **File > Export...**, press `Ctrl+E`, or click **Export**.
1. Pick a folder and file name. The suggested name is `todo.txt`.
1. Click **Save**.
<!-- Verified from: src/gui/views/root_window/panes/task_view.py [TaskView.export_tasks] -->

The export writes every task, including completed ones, in todo.txt format.
Tasks are ordered open first, then by due date, then by title, whatever the
**View** settings are. Notes are not included. Your own `todo.txt` is not
changed.
<!-- Verified from: src/adapters/export.py [export_todo_text] -->
<!-- Verified from: src/domains/tasks/models.py [TaskBoard.list_todos] -->

If you pick a file that already exists, Windows asks you to confirm before it
is replaced.
<!-- Verified from: src/gui/views/root_window/panes/task_view.py [TaskView.export_tasks] -->

## Commands and Shortcuts

The program has no terminal commands or options beyond the launch command in
[Open The Window](#open-the-window). Shortcuts are shown as they appear on
Windows.
<!-- Verified from: src/main.py [main] -->

| Menu | Command | Shortcut | What it does |
| --- | --- | --- | --- |
| File | **Export...** | `Ctrl+E` | Writes a copy of your tasks to a file you choose. |
| File | **Archive Completed** | `Ctrl+Shift+A` | Moves completed tasks to `done.txt`. |
| File | **Exit** | `Ctrl+Q` | Closes the program. |
| Edit | **New Task** | `Ctrl+N` | Clears the editor for a new task, first asking about any unsaved changes. |
| Edit | **Toggle Complete** | `Ctrl+Enter` | Saves the selected task and marks it complete, or open again if it is already complete. |
| Edit | **Delete Task** | `Delete` | Deletes the selected task. |
| Edit | **Settings...** | `Ctrl+,` | Opens the settings window. |
| View | **Sort By** > **Completion**, **Due Date**, **Priority**, **Created Date**, **Alphabetical**, **Project**, **Context** | None | Sets the task list order. |
| View | **Group By** > **None**, **Completion**, **Due Date**, **Priority**, **Project**, **Context** | None | Sets the task list groups. |
| View | **Show todo.txt Lines** | None | Switches the task list between `todo.txt` lines and shorter labels. |
| Help | **About** | None | Shows the program name and a short description. |
<!-- Verified from: src/gui/views/menu_bar/main_menu.py [build_menu_bar] -->
<!-- Verified from: src/gui/views/menu_bar/view_menu.py [build_view_menu] -->

The editor's **Save** button has no keyboard shortcut.
<!-- Verified from: src/gui/views/root_window/panes/task_editor.py [TaskEditorPane.__init__] -->

## Your Data Files

### Where Your Files Live

When you run the program from the project folder, the base folder is the
project folder. When you run a built copy of the program, the base folder is
the folder that holds the program file.
<!-- Verified from: src/config/path_handler.py [calc_root_dir] -->

| File | Location | Written by the program |
| --- | --- | --- |
| `todo.txt` | The **Todo file** setting. Default: `data/todo.txt` in the base folder. | On every change |
| `done.txt` | Beside `todo.txt`, unless `doneFile` is set. | When archiving |
| `notes.json` | `data/` in the base folder. | When a task is saved |
| `settings.json` | The base folder. | When settings or **View** choices change |
| `todo_txt.log` | `logs/` in the base folder. | While running |
| Exported file | Wherever you choose. | When exporting |
<!-- Verified from: src/config/path_handler.py [NOTES_PATH] -->
<!-- Verified from: src/config/settings.py [SETTINGS_PATH] -->
<!-- Verified from: src/config/settings.py [AppSettings] -->
<!-- Verified from: src/config/logging/log_config.py [configure_logging] -->

### Understand todo.txt Lines

Each non-blank line is one task. The program reads and writes these parts, in
this order:

| Part | Example | Meaning |
| --- | --- | --- |
| `x` and a date | `x 2026-09-25` | Completed, with the completion date. |
| Priority | `(A)` | Priority of an open task. |
| Date | `2026-09-20` | Creation date. |
| Text | `Pay rent` | Title. |
| `+word` | `+Home` | A project. |
| `@word` | `@phone` | A context. |
| `due:` | `due:2026-10-01` | Due date, written `YYYY-MM-DD`. |
| `key:value` | `rec:1m` | Any other tag. It is kept as it is. |
| `pri:` | `pri:A` | Priority of a completed task. |
<!-- Verified from: src/adapters/export.py [format_todo_line] -->
<!-- Verified from: src/adapters/export.py [_parse_todo_line] -->

Example lines:

```text
(A) 2026-09-20 Pay rent +Home @online due:2026-10-01
x 2026-09-25 2026-09-20 Buy milk @errands pri:B
```

A word with exactly one colon and text on both sides, such as `10:30`, is read
as a `key:value` tag and moved to the end of the line when that task is next
saved.
<!-- Verified from: src/adapters/export.py [_is_metadata] -->

The program does not reject lines it cannot fully read. A `due:` or `pri:`
value that is not valid, such as `due:2026-13-45`, stays in the task's title
so you can see and fix it. A line with no title words, such as `x 2026-01-01`,
is shown as its whole text. These lines are saved back unchanged unless you
edit them.
<!-- Verified from: src/adapters/export.py [_parse_metadata_token] -->
<!-- Verified from: src/adapters/export.py [_parse_todo_line] -->

### Move Your Tasks To Another Folder

1. Close the program.
1. Move `todo.txt`, and `done.txt` if you like, to the new folder.
1. Start the program. When **Todo File Missing** appears, choose **Yes**.
1. Browse to the moved file and click **Save**.
1. Start the program again when it closes.
<!-- Verified from: src/gui/views/root_window/window.py [TodoMainWindow._locate_missing_file] -->

To start a new file in another folder instead, create an empty `todo.txt`
there first. **Todo file** only accepts a file that already exists.
<!-- Verified from: src/gui/views/settings/settings_dialog.py [SettingsDialog._save] -->

## Troubleshooting

| Symptom | Likely Cause | Resolution |
| --- | --- | --- |
| The program closes at once or will not start. | `settings.json` has a value the program does not accept. | Fix the value using the table in [Edit The Settings File](#edit-the-settings-file). |
| A task title shows text such as `due:2026-13-45` or `(a)`. | The line has a due date or priority the program cannot read. | Fix the value in the editor or a text editor. For example, use `due:2026-12-31` or `(A)`. |
| **Todo File Changed** keeps appearing. | Another app or device is changing `todo.txt`. | Choose **Yes** to reload. Let Dropbox finish syncing before editing on another device. |
| A change was not saved. | `todo.txt` changed outside the program before the save. | Choose **Yes** to reload, then make the change again. |
| **Dropbox Conflicted Copies** appears at startup. | Two devices changed the file before syncing. | Compare the listed files with `todo.txt`, merge what you need, then delete the copies. |
| **Todo File Missing** appears at startup. | The file was moved, renamed, or deleted. | Choose **Yes** and browse to the file. |
| A task's note is missing. | The task's title or creation date was changed in another app. | Change the title back, or copy the note from `notes.json`. See [How Notes Are Stored](#how-notes-are-stored). |
| A file named `notes.json.invalid` appeared. | `notes.json` could not be read, so the program set it aside and started a new one. | Open `notes.json.invalid` in a text editor to recover your notes. |
| `Select a task first.` appears. | **Delete Task** or **Toggle Complete** was used with no task selected. | Click a task, then try again. |
<!-- Verified from: src/config/settings.py [load_settings] -->
<!-- Verified from: src/adapters/export.py [_parse_metadata_token] -->
<!-- Verified from: src/adapters/storage/notes.py [NotesStore._read_entries] -->
<!-- Verified from: src/gui/views/root_window/window.py [TodoMainWindow] -->
<!-- Verified from: src/gui/views/root_window/panes/task_view.py [TaskView] -->

## FAQ

### Does Sorting Change My todo.txt File

No. **View** choices only change the window. Existing lines keep their place
in the file, and new tasks are added at the end.
<!-- Verified from: src/adapters/storage/todo_text.py [TodoTextStore._in_file_order] -->

### Which Date Does The Program Use For Today

Creation and completion dates use your computer's date and time zone, so a
task added late in the evening gets that day's date.
<!-- Verified from: src/domains/tasks/models.py [_local_today] -->

### Can I Use Other todo.txt Apps On The Same File

Yes. The program keeps lines it did not change exactly as they were. It warns
you instead of overwriting when another app has changed the file.
<!-- Verified from: src/adapters/storage/todo_text.py [TodoTextStore.render_line] -->
<!-- Verified from: src/adapters/storage/todo_text.py [TodoTextStore.ensure_current] -->

### Do Notes Sync To My Other Devices

No. Notes are stored in the program's data folder on this computer, not in
`todo.txt`, so Dropbox and other todo.txt apps do not see them.
<!-- Verified from: src/config/path_handler.py [NOTES_PATH] -->
<!-- Verified from: src/adapters/export.py [format_todo_line] -->

### Can I Undo A Delete

No. There is no undo, and deleting does not ask for confirmation.
<!-- Verified from: src/gui/views/menu_bar/main_menu.py [build_menu_bar] -->
<!-- Verified from: src/gui/views/root_window/panes/task_view.py [TaskView.delete_selected] -->

### Can I Give Tasks Priorities Outside My Settings Range

Not from the editor. A priority from `A` to `Z` added in another app or a text
editor is kept and shown.
<!-- Verified from: src/gui/views/root_window/panes/task_editor.py [TaskEditorPane.set_priority_range] -->

## Glossary

| Term | Meaning |
| --- | --- |
| Archive | The `done.txt` file that completed tasks move to. |
| Completion date | The date when a task was marked complete. |
| Conflicted copy | An extra file Dropbox creates when two devices change a file before syncing. |
| Context | A word starting with `@`, such as `@phone`, for where or how a task gets done. |
| Creation date | The date when a task was added. |
| Due date | The date a task should be done by, stored as `due:YYYY-MM-DD`. |
| Group | A labeled section of the task list chosen from **View > Group By**. |
| Priority | A capital letter from `A` to `Z`, shown as `(A)`. `A` is the highest. |
| Project | A word starting with `+`, such as `+Home`, that ties tasks together. |
| Tag | Any other `key:value` word on a task line, such as `rec:1m`. |
| todo.txt | The plain-text task file, with one task per line. |
