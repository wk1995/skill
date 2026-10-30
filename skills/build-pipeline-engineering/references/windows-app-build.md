# Windows application builds

Use this reference to turn an exact source ref into a Windows installer or portable application. A compiled `.exe` is not necessarily an installer; identify the requested deliverable before selecting packaging tools.

## Establish the Windows contract

Inspect the existing project first: technology stack, build/publish entry point, locked dependencies, packaging configuration, and source-owned application/version identity. Record:

- Minimum Windows version and each target architecture (`x64`, `x86`, `ARM64`); distinguish the build host from the target and native dependencies.
- Installer format or portable bundle; user-level versus machine-wide installation, expected elevation, destination, shortcuts, file associations, and any explicitly required services or autostart.
- Runtime policy: bundled/self-contained or an external prerequisite such as .NET, VC++ Runtime, Java, Python, or WebView2. Include native DLLs, plugins, resources/models, licenses, and required configuration. State whether installation must work offline.
- Existing application ID, publisher, version, icons, upgrade identifiers, and behavior for upgrade, uninstall, and user data. Do not silently generate new identities for each build.
- Signed release or explicitly unsigned test artifact, signer identity, signing provider, timestamp service, and protected credential references.

If the format is unspecified, use the repository's configured format when it meets the requested deployment needs; otherwise explain the choice and resolve the missing requirement before implementing the installer.

## Choose the package and build path

| Deliverable | Appropriate use | Contract to verify |
| --- | --- | --- |
| EXE installer | Custom setup flow, prerequisite bootstrapper, or an existing installer framework | Actual framework and supported silent switches; an EXE may wrap an MSI or may just launch the app |
| MSI | Windows Installer management and enterprise deployment | Package/product/upgrade identity, version rules, install scope, repair/rollback where authored, silent install and upgrade behavior |
| MSIX | Existing MSIX packaging or an explicit deployment requirement | Package identity, supported OS/capabilities, publisher-to-certificate match and target trust/deployment policy |
| Portable ZIP | Run after extraction without an installer | Complete runnable payload, runtime requirements, write locations and absence of assumed installation steps |

Prefer the repository's existing packaging tool: for example WiX, Inno Setup, NSIS, MSIX tooling, or framework-owned packaging. A .NET publish, CMake build/install, Python bundle, or Electron/Tauri/Qt/Flutter build may produce the application payload; confirm the additional installer step instead of treating compilation as finished packaging. Pin the actual framework/packager versions and consult their matching documentation rather than inventing universal commands.

Use a Windows runner for Windows-native packaging, signing, and lifecycle testing unless the selected tool documents a supported alternative. Cross-compiling a binary does not establish that the installer, native modules, or runtime work on Windows. Keep each architecture's payload, prerequisites, symbols, caches, and installer in separate staging paths.

## Signing

- For public distribution, use an organizational signing service or a certificate issued through a trusted code-signing provider after identity validation. Provisioning may use hardware-backed keys or cloud signing; do not assume a downloadable PFX or require one when the provider uses a different interface.
- A self-signed certificate is suitable only for a controlled trust setup; it does not establish public publisher trust. For MSIX sideloading, ensure the target trusts the signing chain and the certificate matches the package publisher. Do not substitute unsigned output when signing is required.
- An explicitly unsigned EXE/MSI/portable test build can be useful; label it unsigned in the manifest and report. If required signing credentials are absent, report the missing protected configuration and stop the signed-release path.
- Sign applicable executable payloads before packaging, then sign the final installer/package as the toolchain requires. Use the provider-supported SHA-256 digest and timestamp configuration; never log keys, passwords, tokens, or certificate exports.
- Verify the final signature with the selected tool, for example `signtool verify /pa /all /v "path/to/setup.exe"` (or the MSI/MSIX path). Check expected signer, trust chain, timestamp, and signature result; compute checksums after all signing and packaging operations. Signing does not guarantee that SmartScreen reputation warnings disappear.

## Verify on the target

Inspect payloads for expected product/version, architecture, resources, licenses, prerequisites, and signatures. In a disposable Windows VM/runner representing the declared OS and architecture, test the applicable contract:

1. Clean installation with the intended user/elevation scope and runtime policy; exercise offline installation when promised.
2. Launch the installed application and a representative function without developer tooling or dependencies supplied only by the build machine.
3. Silent install when required. MSI supports `msiexec /i "path/to/app.msi" /quiet /norestart /log "path/to/install.log"`; create the log directory first. EXE switches belong to its installer framework and must be discovered there. Capture logs and distinguish documented success, reboot-required outcomes (such as MSI exit code 3010), and failure.
4. Upgrade from a supported prior package, retaining user data and the intended application identity; test repair/rollback only where the installer contract supports it. If no prior package is available, report the upgrade check as untested.
5. Uninstall using the supported mechanism, verifying application/integration cleanup and the configured user-data retention policy. For portable bundles, test fresh extraction, launch, and the documented replacement/removal procedure instead.

Installation mutates the test system; use a disposable environment rather than the user's workstation. Missing required outputs, identity/architecture mismatches, required signature failure, and required lifecycle test failures block upload. Report unavailable checks and their impact explicitly.

Upload the verified installer/bundle, applicable symbols, SHA-256 checksums, and a manifest linking source SHA, toolchain, target, version, signing status, test evidence, and run identity. Keep signing material out of every output.

## Authoritative references

Consult the versions matching the repository's toolchain; these pages describe platform contracts, not a pinned installer implementation:

- [Windows Installer command-line options](https://learn.microsoft.com/en-us/windows/win32/msi/standard-installer-command-line-options)
- [SignTool options and verification policy](https://learn.microsoft.com/en-us/windows/win32/seccrypto/signtool)
- [MSIX package signing](https://learn.microsoft.com/en-us/windows/msix/package/signing-package-overview)
