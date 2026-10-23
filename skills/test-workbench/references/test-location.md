# Test location and direct-device handoff

Use optional `case.testLocation` to help a person or device controller locate the test's page and controls. Derive it from the actual application, source, screenshots or interface tree; do not invent selectors or credentials. It describes planned navigation, not proof of a current screen or a successful test.

## Optional case field

This illustrative fragment belongs on a normal case definition. Replace the example values with project-specific information:

```json
{
  "testLocation": {
    "app": "example.app",
    "screen": "Login page",
    "entryPath": ["Open the test application", "Open the account tab", "Choose login"],
    "targets": [
      {"name": "Login button", "by": "resource-id", "value": "example.app:id/login", "action": "Tap after confirming the page and entered test account"}
    ],
    "verify": "Confirm the page title, account context and selected device before acting"
  }
}
```

Only `screen` is required when the optional object is present. `app` and `verify` are nonempty strings; `entryPath` is an ordered string array; `targets` is an array of objects requiring `name`, `by`, `value` and `action`. Allowed `by` keys are `resource-id`, `accessibility-id`, `text`, `test-id`, `css` and `xpath`; use only strategies the actual controller supports. Empty path/target arrays are valid for manual navigation or when already on the page. Unknown fields, malformed objects and unsupported strategies reject before persistence. No static coordinate or `verified` flag is accepted.

Edit this JSON in the current case definition. Rounds and annotation snapshots freeze it with the other case fields; later edits do not rewrite historical hints. Archives retain it, while older cases without it remain valid and show missing guidance explicitly.

## Webpage and AI

Case details show application/page, entry path, target locator/action and verification note. **Copy phone test hints** includes exact version/source/build, plan/round/environment IDs, device configuration, phase and known failure/staleness, prerequisites, steps and expected result. Copying is read-only; it does not run a command or send a message. The graph's next-test panel also identifies the target page when configured.

`CONTRACT.testLocation`, AI execution `testLocation` projections and graph nodes mark hints as `unverified-live-screen`. The original definition remains in the archive and frozen `nextTest.target`. The template renders metadata as text, never as HTML, shell commands or live selector evaluation. It does not connect to devices, capture screenshots or look up live controls.

## When directly operating a phone

1. Match the actual device/environment and installed package to the round's source/build. Check required cases and live session/data preconditions; recorded passes do not transfer sessions.
2. Inspect the current screenshot or interface tree through the project's available controller. Confirm the page and navigate the entry path if necessary. Match a supported locator and confirm the intended control. Refresh the view after navigation/layout changes; derive any controller-required coordinates from that current view, never a guessed or stale position.
3. Follow the case steps and expected result. Retain screenshots/logs and actual outcomes as execution evidence, separately from the declared hint. Start/result guards still apply.
4. If location fails, refresh and check app/page/device context before classifying the outcome. Missing tooling/access or an unavailable prerequisite may block execution; a confirmed product control/behavior violating the expected result is a failure. Explain the observation instead of treating every locator miss as the same outcome.

Hints support the requested testing scope; they do not authorize unrelated device operations or repeated automatic retries.
