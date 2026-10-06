# Recurring tasks: first local premium feature

The existing shared app now has **Edit > Recurring Tasks...**. Ordinary
todo.txt editing remains available independently of recurrence. Recurrence is
disabled by default and needs both explicit opt-in and an entitlement decision.

## Local development preview

Use the existing project environment; do not use `uv run`:

```powershell
.venv/Scripts/python.exe -m src.main --premium-preview
```

Open **Edit > Recurring Tasks...**, choose a template folder, select
**Enable recurring tasks**, and click **Apply**. The window explicitly labels
this as a local development preview without a paid subscription. The preview
switch is ignored by compiled builds. No payment, account, key, or subscription
is created.

The dialog generates and refreshes current work on opening, on **Apply** or
**Refresh**, and every minute while open. Opening it after a period boundary
generates the new current work. Generation is lazy; there is no background job
when the dialog is closed. A checked occurrence stays visible as completed for
that entire period. Uncheck it only when intentionally reopening that
occurrence.

## Template contract

Configure any readable folder containing `weekly.md`, `monthly.md`, and/or
`quarterly.md`. Individual missing cadences are allowed. Only named Markdown
checkboxes are imported. Empty placeholders are ignored. Checked and unchecked
template boxes both define future work; neither establishes dated history.

For weekly work, a weekday heading such as `## Sunday` supplies optional
guidance. Every weekly task is available throughout the whole Monday–Sunday
week. Completing Sunday's task on Monday counts once for that week and does not
create another task on Sunday. There are no automatic due dates.

YAML front matter is ignored, including stale `month: April` and `Quarter: Q2`.
These filenames define cadence; old metadata never selects an occurrence date.
The parser does not implement a general Markdown/YAML document engine.

Implicit template identity uses cadence plus a hash of the title with normalized
case and whitespace. Moving a task to another suggested weekday keeps its
identity. Duplicate normalized titles in one cadence are rejected. To
distinguish duplicate titles or preserve identity across renames, author an
explicit ID:

```markdown
- [ ] Review plans <!-- recurring-id: quarterly-review -->
```

IDs must be unique within their cadence. Existing occurrences are snapshots:
title and weekday edits apply to the next period; newly named templates appear
on the next refresh. Removing a template does not erase already generated work.

## Initial calendar and retention decisions

- Dates use the Windows local calendar, independent of UTC and daylight-saving
  clock offsets. Weeks start Monday at local midnight; the next Monday is
  excluded.
- Months start on the first and end at the next month's first. Calendar quarters
  start January 1, April 1, July 1, and October 1. End dates are exclusive.
- Only the current period is generated. Missed periods are not backfilled. Old
  incomplete occurrences remain in storage but do not carry into the current
  list.
- Generation is unique by template identity and period start. Refresh, restart,
  concurrent generation, and a completion retry cannot create duplicates.
- Completion is a separate record per occurrence. Repeated completion preserves
  the first date. Commands using an expired occurrence ID are rejected.
- Disabling recurrence or losing entitlement stops generation and completion
  commands. Current retained records remain readable; disabling deletes nothing.

**Decisions that affect user records:** renaming an implicit-ID template or
changing cadence creates a new identity and can add work in the current period.
Use explicit IDs for stable renames. Switching template folders shares the
existing recurrence library: identical cadence/title or explicit IDs refer to
the same template; already generated work remains visible until its period ends.
Changing the system date can change which period is shown. Historical records
are retained without automatic cleanup; this version has no history browser.

## Persistence and compatibility

`recurringEnabled` and `recurringFolder` are saved in the existing settings
JSON; unknown settings and ordinary file preferences are preserved. No
entitlement is stored there. `data/recurring.json` under the app's writable root
stores versioned UTF-8 JSON with separate `occurrences` and `completions` maps.
In a portable compiled build the `data` folder is beside the executable, outside
the temporary extraction folder. State is independent of the chosen template
folder and does not automatically follow todo.txt to Dropbox.

Period uniqueness uses template identity and period start. Occurrence IDs are
stored positive integers that survive restarts and migration. A saved
`next_identifier` counter prevents reuse while history is retained. Source
templates, todo.txt, done.txt, and notes are never rewritten by recurrence. The
recurring list is separate from the one-time task editor and its export/archive
commands, so ordinary todo.txt consumers see no new tokens or records. Fixture
copies of the user's examples live under `tests/fixtures/recurring/`; tests
never write to the live Dropbox folder.

Each operation reloads state under a local OS file lock. The lock covers the
complete read-modify-write operation, preventing lost updates between
cooperating instances of this app on the same computer. `recurring.json.lock` is
a persistent sidecar; the OS releases its lock if the app exits or crashes. A
competing operation waits at most two seconds before reporting an error that can
be retried. The sidecar is not a stale-lock flag and should not be removed while
apps run.

Saves use a unique temporary file in the same folder, flush to disk, then
replace JSON atomically. Unchanged refreshes do not rewrite it. Invalid JSON,
duplicate keys/periods, unsupported schema, invalid dates, or orphaned
completions cause a visible error rather than a reset. Failed writes retain the
previous complete file. Observed outside edits before replacement are rejected,
but manual editors do not participate in the app lock. Edit state only with the
app closed.

The state file is local to this app installation. JSON readability does not
provide Dropbox multi-device merging or conflict resolution. If the app itself
is in a synced folder, its state is there too; concurrent edits from different
computers can conflict and require manual review. No new backups or caching were
introduced. Resetting or deleting state loses completion and permits
regeneration.

## Migration from the first SQLite preview

On the first recurrence access, if JSON is absent and `data/recurring.sqlite3`
exists, the app reads SQLite in read-only mode, validates the entire schema and
history, and atomically writes JSON. This preserves occurrence IDs, period
snapshots, and all completion records, including past periods. The SQLite file
is never overwritten or deleted. Python's built-in SQLite module remains only
for this importer; ordinary recurrence reads and writes use JSON.

Close the previous app version before migrating. Once JSON exists, it is the
source of truth: SQLite is neither merged nor reimported. Switching back to an
older app does not update JSON, and changes in that old database will not follow
you back. Removing JSON while retaining SQLite makes the next access import that
old snapshot again; do not remove JSON expecting a fresh reset. Corrupt JSON
never falls back to stale SQLite. Invalid legacy state or a failed save leaves
the original database intact and does not create a partial replacement. A later
access can retry migration if no JSON was successfully saved.

## Subscription integration still required

`src/domains/premium/access.py` defines `RecurringEntitlement`. The default
`UnavailableEntitlement` denies access. `build_recurring_controller()` in
`src/bootstrap.py` accepts an injected implementation and rechecks access on
every generation and completion command. This is an integration seam, not secure
billing or a complete subscription product. Client code can be modified by its
owner.

Before a premium release, choose an account/authentication approach, a
subscription and payment provider, backend verification and revocation,
offline/grace policy, plan/price/currency, entitlement refresh/error behavior,
packaging, and distribution terms. Connect verified subscription access at
bootstrap and test expiration, renewal, cancellation, and network failure. No
provider, price, or credentials have been invented and production billing is not
configured.

## Existing licensing

The app declares GPL-3.0-or-later in `pyproject.toml`; `LICENSE` is unchanged.
Selling GPL software is allowed, but distribution retains applicable source and
recipient-freedom obligations. A paid edition built from this code does not
become proprietary merely through an entitlement gate. See the
[GNU GPL FAQ](https://www.gnu.org/licenses/gpl-faq.html#DoesTheGPLAllowMoney)
and
[GPLv3 distribution terms](https://www.gnu.org/licenses/gpl-3.0.html).

The only runtime dependency remains PySide6. The installed PySide6 6.11.2
metadata declares `LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only`. Qt for Python
has community and commercial licensing options; confirm distribution/packaging
obligations for the selected option before releasing a subscription edition. See
[Qt for Python licensing](https://doc.qt.io/qtforpython-6/licenses.html).

## Verification

```powershell
.venv/Scripts/python.exe -m pytest -p no:cacheprovider
ruff check src tests
.venv/Scripts/python.exe -m mypy src
```

Tests cover calendar boundaries, example parsing, early completion through
Sunday, restart, rollover, missing periods, malformed templates/state,
concurrent app processes, lock timeout/crash release, interrupted writes,
corruption, read-only SQLite migration, opt-in, entitlement denial, settings
retention, and the native Qt dialog controls. A real subscription lifecycle and
compiled premium distribution remain untested until those components exist.
