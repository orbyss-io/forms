# ProgramKit.Web.Discovery

Optional `IWebShellFeature`, identity `ProgramKit.Web.Discovery`. Add its NuGet package to the
consumer feature/bundle closure and enable that exact identity in the **public root shell only**.
Do not map root robots/sitemap resources in a tenant/path-prefixed shell: generate per-origin
projections instead. It registers no Host middleware and replaces no exception/authentication
features. Enabling it deliberately exposes the manifest's exact routes anonymously; keep private
application endpoints in their own authenticated features. Avoid duplicate route owners.

The default catalogue reads `web/generated/program-kit/publication.json` below the content root.
Override through shell setting `ProgramKit:Web:Discovery:OutputDirectory`. Generate with
`ui_profile.py build`; deploy the manifest and public files as a coherent read-only unit. Invalid
hashes, duplicate/templated routes, linked/traversing paths, nonpublic visibility, unsupported
types and excessive payloads fail before endpoints are mapped. A catalogue snapshot lasts one
shell generation. This is not a general static-file middleware or directory browser.

Register a consumer-owned `IPublicDocumentCatalog` to replace the file adapter. All catalogue
output is explicitly public. HEAD/GET are supported; content type and noindex headers are owned
by this feature. CSP, cache policy, security headers, authentication and exception formatting
remain the application's selected independent features. The complete public content exists in
the initial response; JavaScript is not required for metadata or content retrieval.
