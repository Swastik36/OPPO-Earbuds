<!-- BEGIN:dox-framework-root -->
# DOX framework

- DOX is highly performant AGENTS.md hierarchy installed here
- Agent must follow DOX instructions across any edits

## Core Contract

- AGENTS.md files are binding work contracts for their subtrees
- Work products, source materials, instructions, records, assets, and durable docs must stay understandable from the nearest applicable AGENTS.md plus every parent AGENTS.md above it

## Read Before Editing

1. Read the root AGENTS.md
2. Identify every file or folder you expect to touch
3. Walk from the repository root to each target path
4. Read every AGENTS.md found along each route
5. If a parent AGENTS.md lists a child AGENTS.md whose scope contains the path, read that child and continue from there
6. Use the nearest AGENTS.md as the local contract and parent docs for repo-wide rules
7. If docs conflict, the closer doc controls local work details, but no child doc may weaken DOX

Do not rely on memory. Re-read the applicable DOX chain in the current session before editing.

## Update After Editing

Every meaningful change requires a DOX pass before the task is done.

Update the closest owning AGENTS.md when a change affects:

- purpose, scope, ownership, or responsibilities
- durable structure, contracts, workflows, or operating rules
- required inputs, outputs, permissions, constraints, side effects, or artifacts
- user preferences about behavior, communication, process, organization, or quality
- AGENTS.md creation, deletion, move, rename, or index contents

Update parent docs when parent-level structure, ownership, workflow, or child index changes. Update child docs when parent changes alter local rules. Remove stale or contradictory text immediately. Small edits that do not change behavior or contracts may leave docs unchanged, but the DOX pass still must happen.

## Hierarchy

- Root AGENTS.md is the DOX rail: project-wide instructions, global preferences, durable workflow rules, and the top-level Child DOX Index
- Child AGENTS.md files own domain-specific instructions and their own Child DOX Index
- Each parent explains what its direct children cover and what stays owned by the parent
- The closer a doc is to the work, the more specific and practical it must be

## Child Doc Shape

- Create a child AGENTS.md when a folder becomes a durable boundary with its own purpose, rules, responsibilities, workflow, materials, or quality standards
- Work Guidance must reflect the current standards of the project or user instructions; if there are no specific standards or instructions yet, leave it empty
- Verification must reflect an existing check; if no verification framework exists yet, leave it empty and update it when one exists

Default section order:
- Purpose
- Ownership
- Local Contracts
- Work Guidance
- Verification
- Child DOX Index

## Style

- Keep docs concise, current, and operational
- Document stable contracts, not diary entries
- Put broad rules in parent docs and concrete details in child docs
- Prefer direct bullets with explicit names
- Do not duplicate rules across many files unless each scope needs a local version
- Delete stale notes instead of explaining history
- Trim obvious statements, repeated rules, misplaced detail, and warnings for risks that no longer exist

## Closeout

1. Re-check changed paths against the DOX chain
2. Update nearest owning docs and any affected parents or children
3. Refresh every affected Child DOX Index
4. Remove stale or contradictory text
5. Run existing verification when relevant
6. Report any docs intentionally left unchanged and why

## User Preferences

- Build the project in clear layers (BLE / RFCOMM discovery -> protocol analysis -> Python library -> UI / CLI wrapper).
- Do not execute raw Bluetooth scans or RFCOMM socket connections without explaining parameters to the user.
- Maintain permanent laboratory documentation in `docs/` and raw binary captures in `captures/`.

## Purpose

Develop a fully open-source Linux companion application, PySide6 Desktop GUI, and CLI driver (`oppoctl`) for the **OPPO Enco Buds3 Pro** (and OPO v1 protocol TWS earbuds) that replicates the core functionality of the Android HeyMelody app (battery levels, EQ profiles, game mode, gesture controls, and ANC/transparency).

## Ownership

- Owner: Swastik
- Scope: Entire OPPO Companion Python library, PySide6 GUI, OPO v1 RFCOMM protocol driver, test suite, and Linux desktop integration.

## Local Contracts

- Python scripts must use Python 3.10+ standard features (`asyncio`, `socket.AF_BLUETOOTH`, `argparse`, `dataclasses`).
- Do not hardcode target Bluetooth MAC addresses in core library code; accept them dynamically via CLI flags or configuration defaults.
- All OPO v1 RFCOMM protocol frame encoding/decoding must remain isolated in `src/oppo_control/protocol.py`.
- Desktop integration scripts (`install.sh`, `oppogui.desktop`) must install without requiring elevated root privileges outside user-space paths (`~/.local/bin`, `~/.local/share/applications`).

## Work Guidance

- Refer to [PROTOCOL.md](file:///home/swastik/new-project/oppo%20gui/docs/PROTOCOL.md) for OPO v1 packet headers, command IDs, and checksum layout.
- Use `oppoctl` command line interface for quick headless protocol debugging and hardware queries.

## Verification

- Run offline protocol unit tests via `pytest tests/` or `python3 -m pytest tests/`.
- Validate package build metadata with `pip install -e .[dev]`.

## Child DOX Index

- [src](file:///home/swastik/new-project/oppo%20gui/src/AGENTS.md): Main Python application package source containing `oppo_control` library, `gui` PySide6 application, and telemetry models.
- [docs](file:///home/swastik/new-project/oppo%20gui/docs/AGENTS.md): Reverse-engineering specifications, protocol frame layout, and GATT profiles.
- [tests](file:///home/swastik/new-project/oppo%20gui/tests/AGENTS.md): Automated pytest suite for RFCOMM frame parsing, checksums, decoders, and GUI instantiation.
- [scripts](file:///home/swastik/new-project/oppo%20gui/scripts/AGENTS.md): Developer packet logging, protocol validation, and device survey utility scripts.
<!-- END:dox-framework-root -->
