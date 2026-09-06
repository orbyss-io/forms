# Greeting CLI

Build a tiny local command-line application for a single user.

## Required behavior

- Use Python 3.13 and only its standard library.
- Running `python -m greeting` prints exactly `Hello, Program Kit!` followed by one newline.
- A successful invocation exits with code `0`.
- The application accepts no arguments. Supplying an argument prints a concise usage error to
  standard error and exits with code `2`.
- Automated tests verify the exact output and both exit-code paths.
- The accepted verification tools are Python's standard-library `unittest` and `subprocess`; they
  add no dependency or separate architecture choice.
- For this disposable, local, single-maintainer application, `python -m unittest discover` is the
  authoritative aggregate gate. CI and reviewed-commit remote evidence are deferred until a remote,
  release, deployment, or additional-contributor surface actually exists.
- Any available Python 3.13 patch satisfies the accepted runtime line. Record the resolved patch as
  execution evidence; do not create a new ADR merely to choose a patch release.

## Explicit boundaries

- There is one local maintainer and no other actor or role.
- There is no browser interface, HTTP API, network access, identity, authorization, persistence,
  database, configuration file, secret, telemetry backend, deployment environment, background
  process, plugin, or third-party runtime dependency.
- Packaging, publication, installation, localization, accessibility, scaling, retention, backup,
  recovery, and production operation are outside this application.
- The first specification should cover the complete greeting journey rather than technical layers.
