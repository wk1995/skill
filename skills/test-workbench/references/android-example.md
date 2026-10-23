# Optional example: Android package testing

This is one platform adapter for the general workflow, not a restriction on the Skill.

For a webpage ADB scanner/registration flow and USB/wireless identity deduplication, read [project-integrations.md](project-integrations.md#adb-device-discovery-and-registration). The bundled starter has no ADB service; reuse or implement the actual project adapter before claiming automatic phone detection.

- Discover with `adb devices -l`, resolve offline/unauthorized devices, and select an explicit serial with `adb -s` for operations. Do not treat a wireless endpoint as permanent physical identity.
- Register model, manufacturer, Android version/API, ABI, fingerprint and page size when relevant. Add the profile to the current round before recording results.
- Compare the verified APK's package ID, version and certificate with the installed application. Use a supported replacement install such as `adb -s "$SERIAL" install -r "$APK"` to retain data. Do not uninstall, clear data or force downgrades without authorization.
- Verify the installed version and, where readable, package digest. Resolve on-device install prompts instead of calling a canceled install a product defect.
- FIR, Play or other channel names do not authorize upload. A static 16 KB compatibility check does not replace testing a compatible runtime/device.

[Official Android Debug Bridge documentation](https://developer.android.com/tools/adb), checked on 2026-10-22, supports the device-targeting and replacement-install commands. Other platforms use their own tooling and environment profiles.
