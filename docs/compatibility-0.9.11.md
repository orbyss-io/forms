# Program Kit 0.9.11 compatibility report

0.9.11 is a governance review-gate patch over 0.9.10. Program Kit components advance to `0.9.11`;
runtime packages and the host image remain `0.9.9-preview.1` because no runtime contract changed.

The C4 viewer now accepts `draft` and `confirmed` bootstrap intake states for different read-only
purposes. A draft must match every registered intake artifact hash and byte count exactly, and its
DSL must parse and equal a fresh export from canonical `architecture-map.json`. Confirmed review
retains the existing hash-pair and freshness behavior, including review of a map and projection that
evolved together after confirmation.

The outer `program-kit-bootstrap` workflow remains incompatible with a draft intake and continues to
require explicit human confirmation before its intake validator succeeds. Viewing does not change
the intake, import `workspace.json`, create approval evidence, or accept architecture.
