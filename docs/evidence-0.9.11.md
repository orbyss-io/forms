# Program Kit 0.9.11 release evidence

Source regressions exercise a current draft, stale projection, mismatched registered draft hashes,
invalid draft JSON and DSL, confirmed baseline review, temporary-only `workspace.json`, exact
repository immutability, and absence of confirmation or architecture-acceptance effects.

The packaged clean-consumer acceptance installs the generated 0.9.11 extension and workflow, creates
the canonical intake artifacts as a hash-bound draft, inspects the draft C4 projection, proves the
outer validator still rejects that draft, applies explicit confirmation, and then completes final
intake validation in that order.

Release packaging, clean installation, previous-stable candidate upgrade, and public catalog install
and upgrade verification must reproduce the same behavior from generated release archives before
the patch is available to consumers.
