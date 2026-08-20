# ExcaliFlow Studio

Local-first code intelligence and presentation-ready diagrams.

## Current capabilities

- Graphify/Understand-aware codebase diagrams.
- Offline Mermaid + Panzoom viewer and editable `.excalidraw` export.
- Editorial SVG/HTML plus architecture, Sankey, Wardley, journey, KPI, funnel, timeline, quadrant, process, matrix, and risk visuals.

## Development layout

```text
src/excaliflow/       # stable package/CLI boundary
scripts/              # compatibility generator during migration
assets/vendor/         # pinned offline browser runtimes
tests/                 # deterministic generator and CLI tests
agents/                # skill metadata
```

## Run

```powershell
$env:PYTHONPATH = "$PWD/src"
py -3 -m excaliflow.cli --help
py -3 -m unittest discover -s tests -v
```

## Migration boundary

The package CLI deliberately calls the verified generator while the renderer and viewer are split into testable modules. This preserves existing installed-skill behavior; it is not yet a claim that the monolith has been fully removed.
