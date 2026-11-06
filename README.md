# Pocket Tasks

A tiny offline task-list CLI. Add tasks, list them, and keep their stable IDs in a local JSON file. It uses Python 3.14 and the standard library; no dependency installation, account or network connection is needed.

## Use

Run these commands from the repository root:

```sh
python -B -m pocket_tasks add "Write the pilot contract"
python -B -m pocket_tasks add "Review the result"
python -B -m pocket_tasks list
```

The list displays:

```text
1 [ ] Write the pilot contract
2 [ ] Review the result
```

The default store is `.artifacts/tasks.json`. Choose another store explicitly with a global option before the command:

```sh
python -B -m pocket_tasks --store .artifacts/demo/tasks.json add "Try the CLI"
python -B -m pocket_tasks --store .artifacts/demo/tasks.json list
```

Adding trims surrounding whitespace, rejects blank titles, allocates the next ID and creates a task with `completed: false`. Listing preserves stored order and shows `[x]` for a valid existing completed task. Listing a missing store reports `No tasks.` without creating a file.

The UTF-8 store has an exact versioned shape:

```json
{
  "version": 1,
  "next_id": 2,
  "tasks": [
    {"id": 1, "title": "Write the pilot contract", "completed": false}
  ]
}
```

IDs are unique positive integers; `next_id` is greater than all existing IDs. ID gaps are allowed. Boolean and floating-point values cannot stand in for IDs. Unexpected fields, duplicate JSON keys, non-finite numbers and malformed stores are rejected with exit code 2, without replacing existing bytes. Successful commands exit 0. Writes replace the destination from a closed temporary file in the same directory. Use one writer at a time.

## Check the baseline

```sh
python -B -m unittest discover -s tests -v
```

Tests use only synthetic files beneath `.artifacts/`, including subprocess entry-point checks and atomic-write failure checks. Local stores, temporary files and test output are ignored by Git.

## Delivery pilot

This baseline implements **add** and **list**. The proposed next feature is **complete a task by ID**, described in [the pilot feature brief](docs/pilot-feature.md). That command is intentionally left for the bounded implementation/review pilot. Preparing this repository does not authorize live Agent execution or establish provider qualification.
