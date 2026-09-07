# Orbyss.Localization.Formats

Bounded, mutation-free adapters for CSV, Orbyss Forms JSON, XLSX, XLIFF 2.1, and GNU PO imports and exports.

Each adapter converts untrusted bytes into the provider-neutral `LocalizationImportDocument`.
Catalog mutation remains the responsibility of the preview/apply coordinator, so parsing a file
can never bypass hash binding, optimistic concurrency, validation, review, or authorization.

Exports use deterministic ordering and content digests. CSV and XLSX carry structured scope columns;
JSON carries the complete provider-neutral entry contract. PO and XLIFF exports require one explicit
scope and one target locale so repeated keys cannot become ambiguous. XLSX emits text-only cells and
never formulas or active content.

CSV is a lossless machine-interchange representation; spreadsheet software can interpret leading
characters as formulas when opening CSV directly. Use the XLSX exporter for human spreadsheet
workflows because it writes every cell explicitly as text.

XLSX support uses the platform ZIP/XML readers and does not execute formulas, macros, external
relationships, links, or embedded objects. Consumers register only the adapter instances they want.
