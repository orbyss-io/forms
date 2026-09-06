# Forms physical acceptance boundary

Program Kit 0.9.9 publishes a forms engine and thin framework bindings. It does not publish form
controls, action bars, steppers, lookup widgets, editors, modelers or component CSS. Consequently,
the earlier Program Kit component showcase is not a release-acceptance gate for this package set.

The automated browser fixture supplies its own deliberately minimal renderer and verifies that the
engine passes validated data, translated state and delayed validation presentation through React
under Chromium, Firefox and WebKit. That fixture renderer is test code and is not packed.

Physical-device, virtual-keyboard, screen-reader, appearance and responsive-layout acceptance
belongs to the consuming application and the renderer/design-system packages it selects. If a
future Program Kit release introduces a Program Kit-owned visual component, copy the report
template and restore a physical-acceptance matrix for that component before publication.

The rejected form-modeler, schema-modeler, localization-management and custom form-component
prototypes remain absent. Backend form/localization management contracts, validation, storage
ports, APIs and MCP tools remain separately tested and publishable.
