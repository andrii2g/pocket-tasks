# Working on Pocket Tasks

Keep the CLI small, offline and usable with Python 3.14 and its standard library.

- Preserve valid existing task data, stable IDs and the documented JSON schema.
- Reject malformed state before mutation; write through a sibling temporary file and atomic replacement.
- Add no network calls, credentials, external services or runtime dependencies.
- Keep generated stores, temporary files and verification output inside `.artifacts/`.
- Run `python -B -m unittest discover -s tests -v` and add meaningful behavioral regression coverage for the assigned feature.
- Keep changes within the approved feature and report exact checks, outcomes and remaining limitations.

The proposed completion feature is in `docs/pilot-feature.md`. Its specification does not grant remote publication, live execution, integration or release authority.
