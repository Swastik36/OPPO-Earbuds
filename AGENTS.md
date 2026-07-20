# OPPO Enco Buds3 Pro Linux Companion Agent Contract

## Purpose
Develop a fully open-source Linux companion application for the OPPO Enco Buds3 Pro that replicates the core functionality of the Android HeyMelody app (battery levels, Noise Control/ANC/Transparency, EQ presets, touch gesture configs, etc.).

## Ownership
- Owner: Swastik
- Agent Role: Pair Programmer / Developer / Reverse Engineer

## Local Contracts
- Build the project in layers (BLE exploration -> protocol analysis -> Python library -> UI wrapper).
- Do not run scans or bluetooth scripts without explaining parameters.
- Store all documentation in the `docs/` folder as a permanent lab notebook.
- Put raw scans and outputs into the `output/` folder.

## Work Guidance
- Python scripts should use `argparse` to handle target MAC addresses flexibly instead of hardcoding.
- Maintain error safety for BLE connection timeouts, read blocks, or encryption requirements.
- Automate report generation (e.g., outputting JSON and Markdown GATT profiles).

## Verification
- Run Python linting / tests when appropriate.
- Verify BLE connectivity using standard tools if a physical device is present.

## Child DOX Index
(None)
