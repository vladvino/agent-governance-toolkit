# Publishing Python Packages to PyPI via ESRP Release

This document describes the approved process for publishing Python packages from the
Agent Governance Toolkit to PyPI, using Microsoft's ESRP (Engineering System Release Pipeline).

> **⚠️ Important:** GitHub Actions Trusted Publishers (`pypa/gh-action-pypi-publish`) are
> **not compliant** for publishing Microsoft packages to PyPI. ESRP Release is the only
> approved production publishing path.

## Overview

| Component | Details |
|-----------|---------|
| **Pipeline** | `pipelines/pypi-publish.yml` (Azure DevOps) |
| **Publishing method** | ESRP Release (`EsrpRelease@11` ADO task) |
| **PyPI account** | `microsoft` |
| **Packages** | agent-os-kernel, agentmesh-platform, agent-hypervisor, agent-sre, agent-governance-toolkit, agent-runtime, agent-lightning |
| **Build tool** | `python -m build` (sdist + wheel) |

## Prerequisites

Before publishing, complete the following:

### 1. Microsoft Open Source Requirements

- [ ] Register your release via the [Open Source Portal](https://aka.ms/opensource) and obtain CELA/management approval
- [ ] Complete the [Release Checklist](https://aka.ms/releasechecklist) (LICENSE, README, SECURITY.md, CONTRIBUTING.md)
- [ ] Follow [Publish Binaries](https://aka.ms/publishbinaries) guidance
- [ ] Follow [OSS signing guidelines](https://aka.ms/osssigning)

### 2. ESRP Release Onboarding

- [ ] Complete [ESRP Release onboarding](https://aka.ms/esrp-onboarding):
  - Set up Azure Identity (Managed Identity recommended, or App Registration)
  - Register in the ESRP Portal
  - Configure TSS signing certificate in Azure Key Vault
- [ ] Install the ESRP Release ADO Task extension from the Microsoft-internal repo
- [ ] Verify your client ID is configured for public PyPI publishing

### 3. PyPI Account Setup

- [ ] Ensure packages are owned by the `microsoft` PyPI account
- [ ] Join the [PyPI Package Owners group on IDWeb](https://idweb) for notifications
- [ ] Remove personal PyPI accounts after Microsoft ownership is established

### 4. ADO Pipeline Configuration

Update the placeholder values in `pipelines/pypi-publish.yml`:

| Variable | Description | Where to find |
|----------|-------------|---------------|
| `esrpServiceConnection` | Azure service connection name | ADO project settings → Service connections |
| `esrpKeyVaultName` | Key Vault with TSS signing cert | Azure Portal → Key Vaults |
| `esrpSignCertName` | Certificate name in Key Vault | Azure Portal → Key Vault → Certificates |
| `esrpClientId` | Managed Identity or App Registration client ID | Azure Portal → App registrations |
| `esrpOwners` | Package owners (Microsoft FTEs) | Your team's distribution list |
| `esrpApprovers` | Package approvers (Microsoft FTEs) | Your team's distribution list |

## Publishing Process

### Build & Publish (Standard)

1. **Trigger the ADO pipeline** manually or via release gate
2. The pipeline builds all 7 packages (sdist + wheel) using `python -m build`
3. Validates that at least one `.whl` file exists per package (required by Microsoft Python team policy)
4. Publishes artifacts to PyPI via ESRP Release
5. Verifies packages appear on PyPI

### Dry Run (Build Only)

Set `dryRun: true` in the pipeline parameters to build packages without publishing.
This is useful for validating the build process before an actual release.

### Testing the Pipeline Setup

To test your ESRP configuration without publishing to PyPI, temporarily change the
`contenttype` in the ESRP task to a different type (e.g., `Maven`). The pipeline will
run and fail at content validation, confirming your setup is correct.

## GitHub Actions Integration

The GitHub Actions workflow (`.github/workflows/publish.yml`) handles:
- **Building** Python packages (sdist + wheel)
- **Attesting** build provenance via `actions/attest-build-provenance`
- **Uploading** build artifacts for traceability

It does **not** publish to PyPI. Actual publishing is done exclusively through the
ADO pipeline described above.

## Required Artifacts

| File Type | Required | Description |
|-----------|----------|-------------|
| `*.whl` | ✅ Required | Binary wheel (at least one per package) |
| `*.tar.gz` | Recommended | Source distribution (sdist) |

Even if a package has no binary components, publish a "pure" wheel (`*-py3-none-any.whl`).

## Linux Packages: Use manylinux

For packages with native extensions targeting Linux, you **must** use a `manylinux` tag
(e.g., `manylinux2014_x86_64`), not `linux_x86_64`. Publishing with `linux_x86_64` will
result in a PyPI rejection error.

## Policy Notes

- **ESRP does not sign Python wheels** — signing is not required for PyPI today. Compliance
  comes from controlled credentials, malware scanning, and centralized ownership.
- **Package name is inferred from filenames** — ESRP determines the package name from
  artifact filenames, not from explicit configuration.
- **No `--skip-existing` equivalent** — PyPI does not allow filename reuse. You must bump
  the version if a publish fails after partial upload.
- **Publish early** once a package name is public — PyPI does not support name reservation
  and squatting is a real risk.

## Troubleshooting

### ESRP reports "Success" but package doesn't appear on PyPI
**Cause:** Client ID not configured for public PyPI publishing.
**Fix:** Contact ESRP Release PMs to verify backend configuration for your client ID.

### "BadRequest – Package name isn't allowed"
PyPI rejects names that conflict with existing packages. TestPyPI may accept names that
prod PyPI rejects. Check the ESRP error message for specifics.

### "File already exists"
PyPI doesn't allow filename reuse even after version deletion. Bump the version or
contact the Microsoft Python team (`python@microsoft.com`) for manual deletion.

### Unsupported wheel platform tags
Ensure wheel files use PyPI-valid platform tags (e.g., `manylinux2014_x86_64`, `win_amd64`).
Invalid tags like `win_arm32` or `linux_x86_64` will be rejected.

### Pipeline works in ESRP v6 but fails in v7+
Almost always a permissions or client-ID scope issue. Verify your client ID has been
re-authorized for the new ESRP version.

## Yanking / Deleting Packages

Any Microsoft package that needs to be deleted or yanked from PyPI **must** go through
the Microsoft Python team:

- **Contact:** python@microsoft.com
- This is a controlled process to ensure supply chain integrity.

## Support

| Channel | Contact |
|---------|---------|
| ESRP Release PMs | esrprelpm@microsoft.com |
| Python Team | python@microsoft.com |
| Office Hours | Thursdays 9am–9:30am PST |
| ICM | [Create Incident](https://aka.ms/esrp-icm) |
| Teams | [ESRP Release Team](https://aka.ms/esrp-teams) |
