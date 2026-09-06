# Forms and localization physical acceptance

This runbook closes the evidence gap that browser emulation cannot cover: real touch hardware,
virtual keyboards and assistive technologies. It does not publish packages and the showcase does
not send form data anywhere.

## Start the showcase

From the repository root, on a trusted private network:

```powershell
.\scripts\Start-FormsPhysicalAcceptance.ps1
```

Add `-Install` only when the pinned frontend dependencies are not already installed. The launcher
builds the packages and showcase with the exact Node/npm versions declared by the workspace, binds
port `4173`, and prints a loopback URL plus each detected private-network URL. Keep the terminal
open. A phone or tablet must be on the same private network and use the printed LAN URL. Stop the
server with Ctrl+C.

The server exposes only the four static showcase files and build evidence. Every response uses a
strict Content Security Policy, `nosniff`, no-referrer and no-store headers. Do not expose this
development server to a public or untrusted network. If another process uses the port, pass a free
one with `-Port 4174`. A Windows firewall prompt should be permitted for private networks only.

## Required evidence

Copy [the report template](templates/forms-physical-acceptance-report.md) for each acceptance run.
Record the exact Git commit, device model, physical or virtual status, OS, browser and assistive
technology versions. Screenshots or recordings supplement the report but do not replace observable
results.

The preferred first-publication matrix records all of these:

- A physical touch phone in portrait and landscape, including virtual-keyboard behavior.
- A physical touch tablet in portrait and landscape, including virtual-keyboard behavior.
- A desktop keyboard-only journey at 100% and 200% browser zoom.
- A screen-reader journey on at least one supported desktop or mobile combination.
- Dark/light appearance, increased contrast where the platform supports it, and reduced motion.

When hardware is genuinely unavailable, the release owner may explicitly accept a narrower physical
matrix for a named run. Record unavailable combinations as `DEFERRED`, with the reason and approval;
never report them as passed. The current accepted run is Windows desktop plus a physical iPhone in
Safari. Tablet and other physical-device combinations are deferred until hardware is available.

## Journey checklist

Use realistic data without personal or secret information.

1. In the form journey, submit empty fields, confirm the error summary and field errors, complete
   each step, use searchable choices, move backward and forward, and submit successfully.
2. Change locale and direction. Confirm labels, errors, step navigation, values and alignment remain
   understandable in both LTR and RTL.
3. Confirm each invalid field renders an inline message, exposes `aria-invalid="true"`, and has a
   visible danger-state outline in normal and high-contrast modes. Correcting the value must remove
   the field error.
4. Confirm there is no unexpected page-level horizontal scrolling at a 320 CSS-pixel viewport or
   200% zoom, focus is never hidden, touch targets are usable, and content is not clipped by the
   virtual keyboard.
5. With keyboard only, traverse every interactive element and complete the form journey without a
   pointer.
6. With a screen reader, confirm landmarks, headings, labels, descriptions, validation errors,
   status changes and step changes are announced meaningfully.

The prototyped form-modeler, schema-modeler and localization-management UIs were rejected during
physical review and removed from the publishable frontend family. This run deliberately does not
request or claim acceptance evidence for those components. Backend form/localization management
contracts and APIs remain separately tested.

Any journey that fails on an available, in-scope device blocks publication. Repair the product or
document an explicitly approved, time-bounded exception; then rerun the affected journey and attach
the new evidence. Unavailable devices may only be deferred through the recorded matrix exception
above.
