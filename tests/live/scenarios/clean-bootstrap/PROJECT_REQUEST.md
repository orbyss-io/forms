# Greeting CLI request

Build a tiny local command-line application named **Greeting CLI** for one local maintainer.

Use Python 3.13 and only its standard library. Running `python -m greeting` with no arguments must
print exactly `Hello, Program Kit!` followed by one newline and exit with code `0`. Supplying any
argument must print a concise usage error to standard error and exit with code `2`. Automated tests
must verify the exact streams and both exit-code paths using the standard-library `unittest` and
`subprocess` modules. `python -m unittest discover` is the authoritative aggregate gate.

There is no browser interface, HTTP API, network access, identity, authorization, persistence,
database, configuration file, secret, telemetry backend, deployment environment, background
process, plugin, or third-party runtime dependency. Packaging, publication, installation,
localization, accessibility, scaling, retention, backup, recovery, production operation, CI, and
reviewed-commit remote evidence are outside this disposable application. CI and remote evidence may
be reconsidered only if a remote, release, deployment, or additional-contributor surface appears.

The first specification must cover the complete greeting journey rather than technical layers. Any
available Python 3.13 patch is acceptable and should be recorded as execution evidence, not reopened
as an architectural decision.

This request is complete for bootstrap intake. I explicitly confirm these statements and boundaries
as the intended project contract. If the generated synthesis preserves them without adding meaning,
use this message as explicit confirmation; no additional confirmation round is required. If they
cannot be preserved exactly, stop instead of inventing an answer.
