# EAROS Source Workspace Inventory

## Provenance and Boundary

The primary EAROS source workspace is a Git clone of the approved `lone-wolf-J/EAROS` repository. The repository remote is retained as the source-provenance record. This inventory was performed through Git metadata and filesystem inspection only; imported application code was not executed as part of the repository intake.

## Sanitized Source Scope

| Included in the source workspace | Explicitly excluded from source control and transfer packages |
| --- | --- |
| `backend/` FastAPI, governed platform-core, and contract tests | Package dependencies such as `node_modules/` |
| `frontend/` React/Vite client source, tests, and build scripts | Build outputs, coverage, and test-report artifacts |
| `docs/` operational, release, governance, and architecture records | Virtual environments, bytecode, caches, and local logs |
| Root deployment and automation configuration | Environment files, credentials, certificates, tokens, and private keys |

The repository ignore policy excludes known secret-bearing files—including `.env` variants, credentials, token files, `.pem` files, and private-key extensions—alongside dependencies and generated artifacts. The tracked-file inventory contains no dependency directory, virtual environment, generated build directory, environment file, or private-key/certificate file.

## Handling Requirement

> Treat the Git-tracked source tree as the transferable EAROS artifact. Recreate dependencies from the lockfile and install instructions in the target environment. Do not copy local caches, build outputs, test reports, or environment configuration between environments.

Local operational configuration must be supplied through the deployment secret manager described in the production runbook; it must never be added to this repository.

For the complete classification of available source, data, configuration, documentation, and reference materials, see the [user-provided application materials inventory](./EMERGENT_MATERIALS_INVENTORY.md).
