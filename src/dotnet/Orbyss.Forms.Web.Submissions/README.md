# Orbyss.Forms.Web.Submissions

An endpoint-only `CShells.IWebShellFeature` for authenticated owner-scoped drafts, submissions,
decisions, and streamed attachments. It does not install middleware, global exception formatting,
or Host behavior. Consumers register the application services, authentication, authorization,
scanner, storage, and their preferred exception handler.

Attachment bytes stream through the application policy and quarantine store; uploads use
`Idempotency-Key` and `X-Requested-At` headers. No endpoint accepts an actor or administrative flag
from the request body.
