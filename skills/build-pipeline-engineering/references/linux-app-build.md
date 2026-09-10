# Linux application builds

Use this reference for DEB, RPM, AppImage, or tar archive outputs from an exact source ref. Linux is a target matrix: record the supported distributions/versions, CPU architectures, and libc/runtime baseline rather than claiming one build works everywhere.

## Establish the Linux contract

- Inspect the existing stack, build entry point, packaging definitions, dependency locks, and source-owned name/version. Reuse configured packagers; avoid inventing a new path for each format.
- Record target distribution and version, architecture and tool-specific spelling (`amd64` versus `x86_64`, `arm64` versus `aarch64`), glibc versus musl, dynamic-library requirements, and GUI/session requirements when relevant.
- Choose the requested format and installation scope; define prefix/layout, executable modes, symlinks, desktop entry/icons, licenses, configuration, and user-data locations. Add services, users/groups, autostart, or privileged hooks only when part of the requested product contract.
- Decide which dependencies are bundled and which are declared for the package manager or documented for the user. Bundling a language runtime does not remove native ABI/library requirements; packaging must not depend on undeclared libraries from the build machine.
- Record package identity, upstream version and packaging revision from source or permitted build inputs, maintainer metadata, upgrade/uninstall semantics, and required signing/trust policy. Do not change source version files or publish to a package repository to make a local build succeed.

## Select output and environment

| Format | Appropriate use | Required checks |
| --- | --- | --- |
| DEB | Debian/Ubuntu-family targets and package-manager installation | Control metadata, architecture, dependencies, maintainer scripts, file ownership/modes, upgrade and removal/purge behavior |
| RPM | RPM-based target distributions | Spec/package metadata, architecture, Requires/Provides, scriptlets, configuration-file handling, upgrade and erase behavior |
| AppImage | Portable application distribution on declared Linux baselines | AppDir completeness, desktop integration metadata, executable bit, runtime/FUSE requirements and actual launch on supported targets |
| Tar archive | Explicit portable/manual deployment | Payload layout, executable modes/symlinks, external runtime requirements and documented install/update/remove procedure |

Use native Linux runners or pinned distribution containers for compatible targets. Build against an appropriate supported baseline/sysroot for native dependencies: building on a newer glibc system can introduce symbols unavailable on older targets. musl and glibc are separate compatibility targets. AppImage is not a promise of compatibility with every distribution.

Pin SDK/compiler, language runtime, packager, base image, and dependency locks where available. Cross-building requires documented toolchain/packager support; target execution still needs native hardware or explicitly recorded emulation. A container can check package metadata and many CLI/install cases, but is not a substitute for a VM/runner with systemd, desktop session, or kernel behavior when those are required.

## Build, sign, and inspect

1. Check out the resolved commit, install pinned dependencies, and run the repository-owned build and packaging entry points for each distribution/architecture/format tuple. Keep staging and caches target-specific.
2. Inspect final payloads and dependency metadata. Examples: `dpkg-deb --info "app.deb"` and `dpkg-deb --contents "app.deb"`; `rpm -qpi "app.rpm"`, `rpm -qpl "app.rpm"`, and `rpm -qpR "app.rpm"`; `tar -tvf "app.tar.gz"` for archive contents/modes. For native ELF payloads, inspect architecture, interpreter, required libraries, and versioned symbols with tools such as `file` and `readelf`.
3. Use the configured signing mechanism when required. RPM can carry a package signature (verify with `rpmkeys --checksig` using the intended trusted keys). APT repository trust normally comes from signed repository metadata and package hashes; a standalone DEB checksum or detached signature alone does not configure APT trust. AppImage/archive signatures follow the chosen distribution policy. Provision protected keys only for the authorized signing stage.
4. Record explicit unsigned status for permitted unsigned artifacts. Required signature/trust failures block publication; checksums detect byte changes but do not prove publisher identity. Generate SHA-256 checksums from the final signed package bytes.

## Test package lifecycle and delivery

Use disposable target containers/VMs rather than installing into the user's host. Match the declared architecture and OS baseline, and avoid development dependencies that could mask missing runtime requirements.

- For DEB/RPM, install the actual built package using the target package manager so declared dependencies are resolved; launch or smoke-test its functionality. Test services/desktop integration only in an environment that supports them.
- Upgrade from an available supported prior package; verify identity, configuration/user data, file ownership, and service behavior. Remove/uninstall and, for DEB when applicable, separately test purge behavior according to the declared contract. Report absent prior packages as an upgrade-test gap.
- For AppImage, test launch with the supported runtime/FUSE setup; use an extraction fallback only if the application documents and verifies it. For tar archives, extract into a fresh path and exercise the documented launch/update/remove procedure.
- Verify modes and symlink targets after extraction/download. GitHub Actions zipped artifact upload (including `upload-artifact@v4`) does not preserve filesystem permissions for loose files; wrap loose Linux payloads or AppImages in tar when executable modes matter. Upload native packages directly when their internal metadata preserves the installed payload; keep any outer delivery archive traceable with its own checksum.
- Required metadata, dependency, signature, or lifecycle failures block upload. When target execution is unavailable, report the package as built with explicit unverified checks; follow the agreed failure policy before any upload.

Upload the verified deliverables, symbols when required, manifest, and SHA-256 checksums with a unique distribution/architecture/format/source/run name and explicit retention. Record build environment, libc baseline, external dependencies, signing status, and lifecycle evidence. Building files for Actions Artifacts does not itself authorize publishing APT/YUM repository metadata or a public release.

## Authoritative references

Use the policy/tool versions for the selected target distribution:

- [Debian shared-library and dependency policy](https://www.debian.org/doc/debian-policy/ch-sharedlibs.html)
- [APT authentication model](https://manpages.debian.org/stable/apt/apt-secure.8.en.html)
- [RPM signature verification](https://rpm.org/docs/6.0.x/man/rpmkeys.8)
- [AppImage concepts and compatibility](https://docs.appimage.org/introduction/concepts.html)
- [GitHub Actions artifact v4 limitations](https://github.com/actions/upload-artifact/blob/v4/README.md#limitations); recheck behavior for the workflow's selected version.
