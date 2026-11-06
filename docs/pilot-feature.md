# Proposed pilot feature: complete a task by ID

## Outcome

Let a user mark one existing task complete using its stable ID:

```sh
python -B -m pocket_tasks --store .artifacts/tasks.json complete 1
```

This is a proposed bounded implementation assignment. The baseline supports only `add` and `list`; completion is not implemented yet. The delivery owner must approve the concrete baseline revision, assignment and acceptance contract before a managed pilot executes.

## Acceptance

1. Completing a known positive task ID exits 0 and persists that task's `completed` value as `true`.
2. Repeating completion for the same ID exits 0 and leaves its completed state intact. It creates no task and allocates no ID.
3. Listing after completion shows `[x]` for the completed task, including in a fresh process.
4. IDs, titles, task order, other tasks, `next_id` and store version retain their values. No unrelated project file changes.
5. An unknown, nonpositive, boolean-like or noninteger ID exits 2 without changing store bytes or creating a missing store.
6. Existing malformed-store refusal and atomic-write protections remain applicable. Add/list baseline tests continue to pass.
7. Add behavioral regression coverage for completion, repeat completion, unknown/invalid IDs, persistence and untouched data. Run the complete standard-library test suite.

## Scope and evidence

Permitted feature files are `pocket_tasks.py`, `tests/test_pocket_tasks.py` and the relevant usage text in `README.md`. Use synthetic stores and put all generated evidence in `.artifacts/`. Do not add dependencies, network access, API keys, remote services, migrations, task deletion, scheduling or another feature.

Record the exact baseline and result revision or sealed patch, changed paths, full test command/exit/output, independent review and exact combined-result checks. Commit, push, integration and live Agent/provider execution require their separately applicable authority. In particular, a prepared project does not lift Möbiræon's current operational hold or supply missing genuine qualification.
