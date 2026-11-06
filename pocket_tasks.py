"""A small offline task list, backed by a strictly validated JSON file."""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


class StoreError(ValueError):
    """The existing task store cannot be used safely."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise StoreError("duplicate JSON keys are not allowed")
        result[key] = value
    return result


def _reject_constant(_value):
    raise StoreError("non-finite JSON numbers are not allowed")


def validate_store(state):
    if type(state) is not dict or set(state) != {"version", "next_id", "tasks"}:
        raise StoreError("expected version, next_id and tasks")
    if type(state["version"]) is not int or state["version"] != 1:
        raise StoreError("unsupported store version")
    if type(state["next_id"]) is not int or state["next_id"] < 1:
        raise StoreError("next_id must be a positive integer")
    if type(state["tasks"]) is not list:
        raise StoreError("tasks must be a list")
    identifiers = set()
    for task in state["tasks"]:
        if type(task) is not dict or set(task) != {"id", "title", "completed"}:
            raise StoreError("each task must have id, title and completed")
        identifier = task["id"]
        if type(identifier) is not int or identifier < 1 or identifier in identifiers:
            raise StoreError("task IDs must be unique positive integers")
        if type(task["title"]) is not str or not task["title"].strip():
            raise StoreError("task titles must be nonempty text")
        if type(task["completed"]) is not bool:
            raise StoreError("completed must be a boolean")
        identifiers.add(identifier)
    if identifiers and state["next_id"] <= max(identifiers):
        raise StoreError("next_id must be greater than every existing task ID")
    return state


def load_store(path):
    if path.is_symlink():
        raise StoreError("the task store must not be a symbolic link")
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {"version": 1, "next_id": 1, "tasks": []}
    except UnicodeError as error:
        raise StoreError("the task store must be UTF-8 text") from error
    try:
        state = json.loads(
            content, object_pairs_hook=_unique_object, parse_constant=_reject_constant
        )
    except (ValueError, RecursionError) as error:
        raise StoreError("the task store contains invalid JSON") from error
    return validate_store(state)


def save_store(path, state):
    validate_store(state)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(state, stream, ensure_ascii=False, allow_nan=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Keep a small offline task list.")
    parser.add_argument(
        "--store", type=Path, default=Path(".artifacts/tasks.json"), help="JSON task store"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("add", help="add a task").add_argument("title")
    commands.add_parser("list", help="list tasks in their stored order")
    arguments = parser.parse_args(argv)
    try:
        if arguments.command == "add" and not arguments.title.strip():
            raise StoreError("the task title must not be blank")
        state = load_store(arguments.store)
        if arguments.command == "add":
            identifier = state["next_id"]
            state["tasks"].append(
                {"id": identifier, "title": arguments.title.strip(), "completed": False}
            )
            state["next_id"] += 1
            save_store(arguments.store, state)
            print(f"Added task {identifier}.")
        elif not state["tasks"]:
            print("No tasks.")
        else:
            for task in state["tasks"]:
                marker = "x" if task["completed"] else " "
                print(f"{task['id']} [{marker}] {task['title']}")
    except (StoreError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
