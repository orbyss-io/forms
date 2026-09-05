# ProgramKit.Authentication.Assurance

Provider-neutral authentication assurance packaged as a CShell feature. Named policies evaluate
standard OIDC `acr`, `amr`, and `auth_time` claims after the selected authentication profile has
validated the token or session. Applications authorize with `assurance:<name>` or use
`IAssuranceEvaluator` to decide whether an interactive step-up is required.

Accepted ACR values are exact sets rather than a provider-specific numeric hierarchy. Identity
adapters map those portable requirements to their own authentication flows; the runtime package
contains no realm, flow-execution, authenticator, or provider administration concepts.
