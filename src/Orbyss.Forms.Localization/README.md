# Orbyss.Forms.Localization

Explicit integration bridge between the independent Forms and Localization bounded contexts. It
merges a compiled form's translation requirements into a localization catalog without making Forms
own translations or making either semantic core depend on the other.

The bridge never publishes values. New messages enter the catalog without translations; existing
human translations and review state are retained. Conflicting source text or scope metadata fails
the merge through stable diagnostics.

Select `OrbyssFormsLocalizationFeature` to register `DefaultFormLocalizationBridge`. The feature
does not select a Localization runtime, store, or management implementation.
