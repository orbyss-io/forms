# ProgramKit.Web.Discovery.Abstractions

`IPublicDocumentCatalog` and `PublicDocument` are framework/provider-neutral contracts. Implement
a catalogue to adapt another CMS or renderer without changing the shell feature or Host. Every
returned document is deliberately anonymous/public. Never implement this interface over a private
content repository without an explicit public projection. The catalogue is sampled once per shell
generation; publish new content through a new generation/deployment, not mutable response bodies.
