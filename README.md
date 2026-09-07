# SCADGen

**Turn natural language into complete, parametric OpenSCAD assemblies.**

*Successor to [SCADgen](https://github.com/nirmai/SCADgen), an earlier prototype — rebuilt from scratch around an agentic pipeline and a self-expanding template library.*

SCADGen is an AI-powered CAD generator. Describe an object in plain English — *"make a desk lamp"*, *"build a 4-cylinder engine top end"* — and an agentic pipeline decomposes it into parts, generates any templates it's missing, plans how the parts connect, and emits a ready-to-render `.scad` file.

**The template library grows with use** — ask for something it doesn't have (a birdcage, a spoked wheel) and it gets generated, OpenSCAD-verified, and kept for next time.

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![Tests](https://img.shields.io/badge/tests-386%20passing-brightgreen.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![OpenSCAD](https://img.shields.io/badge/output-OpenSCAD-orange.svg)

> A desk lamp generated from the prompt *"make a desk lamp"* — base, gooseneck arm, and shade, each a separate parametric part, positioned by the assembly solver.

> <img width="350" height="419" alt="Screenshot 2026-09-05 210330" src="https://github.com/user-attachments/assets/8633fc03-0328-49ac-a0c4-2b952fd43ab4" />

> A simple 2 piston Engine from the prompt: *"make a simple 2 piston engine"* — engine block, flywheel, gasket, and pistons (inside block) all positioned by the assembly solver

> <img width="524" height="370" alt="Screenshot 2026-09-05 204534" src="https://github.com/user-attachments/assets/1958cc18-9ae4-4abd-b9bc-e543b65fde98" />

> A birdcage from the prompt *"a birdcage with a domed top and vertical bars"* — no birdcage template existed; the dome was written from scratch by the LLM, OpenSCAD-verified, and assembled with a base, radial bars, a ring, and a finial. See [`examples/birdcage.scad`](examples/birdcage.scad).

<img width="317" height="286" alt="Screenshot 2026-09-06 104425" src="https://github.com/user-attachments/assets/e171e84c-d8df-4783-9b08-78b9d37d1e7b" />

High-res birdcage dome:

<img width="334" height="209" alt="Screenshot 2026-09-06 115131" src="https://github.com/user-attachments/assets/f075941c-7ac8-4cfa-bd59-3e4047150396" />

---

## Why this exists

Parametric CAD is powerful but slow to author: you pick parts, set dimensions, name mounting points, and hand-position everything. SCADGen's goal is to do that end-to-end from a description — the way an engineer would sketch an assembly, but automated. The north star: *given a prompt, produce a complete multi-part assembly in OpenSCAD without human intervention.*

The architecture is general-purpose by design, not domain-specific: engines, lamps, and objects with no pre-built template at all (a birdcage) all flow through the same pipeline.

---

## How it works

A five-stage agentic pipeline turns a prompt into an assembly:

```mermaid
flowchart LR
    A["Prompt<br/>(+ optional image)"] --> B["1. Decompose<br/>LLM → parts + connections"]
    B --> C["2. Inventory<br/>match vs. template library"]
    C --> D["3. Generate<br/>LLM writes missing .scad<br/>validate → retry"]
    D --> E["4. Connect<br/>resolve connector refs"]
    E --> F["5. Execute<br/>solve positions → render"]
    F --> G[".scad assembly"]
```

1. **Decompose** — an LLM breaks the description into parts (with suggested templates, parameters, colors, connections), classifying each as a bare primitive, a *pattern* of repeated elements (e.g. cage bars arranged radially), or a genuinely novel shape that needs to be generated. Optionally guided by a reference image (vision).
2. **Inventory** — each part is matched against the template library by id, alias, or keyword. Parts flagged as novel are routed to generation rather than forced onto the nearest primitive.
3. **Generate** — for anything missing, the LLM writes a complete `.scad` template (with metadata and connectors), which is checked structurally *and* by actually rendering it in OpenSCAD — repairing and retrying up to 3 times until it's real, renderable geometry.
4. **Connect** — connector references are validated against real templates and auto-repaired.
5. **Execute** — a graph solver computes each part's world transform (including repeated/patterned parts) and renders the final `.scad`.

### Built to not fall over

Every stage degrades gracefully instead of crashing — the pipeline is designed to always produce a valid assembly:

- **Out-of-range parameters** are clamped to each template's limits
- **Constraint violations** trigger a retry with safe defaults
- **Bad connector names** are auto-snapped, LLM-refined, or dropped
- **Degenerate geometry** (parts overlapping or below the base) falls back to a deterministic vertical stack
- **Bogus template names / failed generations / orphaned parts** are dropped with warnings, and the rest of the assembly still builds
- **Generated templates that don't actually render** (undefined variables, no geometry, broken syntax) are caught by rendering them in real OpenSCAD — not just checking their text — and sent back for repair

---

## Engineering knowledge, not just geometry

SCADGen isn't a dumb shape printer — templates carry real engineering metadata:

- **Constraints** — geometric rules checked before rendering (e.g. *"bolt circle must clear the outer edge"*, *"outer diameter must exceed inner diameter"*)
- **Standards resolution** — natural-language specs resolve to real values: `"M8 bolt"` → ISO metric thread geometry; `"32-tooth module-2 gear"` → computed pitch/outer diameters
- **Parameter harmonization** — linked dimensions stay consistent (a cylinder head's bore matches its block's)
- **Connectors** — named, expression-driven attachment points (`origin: [0, 0, "height"]`) that let parts mate and stack correctly

## Template library — 28 curated parts, growing with use

| Category | Templates |
|---|---|
| **Primitives** | cube, cylinder, sphere, cone, torus |
| **Fasteners** | hex_bolt, hex_nut, washer, set_screw, socket_head_cap_screw, countersunk_screw |
| **Mechanical** | shaft, bushing, bearing_shell, gear_spur, pulley, spring_compression |
| **Engine** | cylinder_block, cylinder_head, piston, connecting_rod, valve, flywheel, oil_pan |
| **Lamp** | lamp_base, lamp_arm, lamp_shade |
| **Sealing** | gasket |

These 28 ship with the repo. Anything the library doesn't have gets written by the LLM and OpenSCAD-verified on the spot, then kept in a separate generated-templates cache for reuse — e.g. `cage_dome`, made entirely from the prompt *"a birdcage with a domed top and vertical bars"* (see [`examples/birdcage.scad`](examples/birdcage.scad)). `scadgen list` tags cache entries `[generated]` so provenance stays clear.

---

## Requirements

- **Python 3.10+**
- **An LLM provider** — at least one of:
  - [Ollama](https://ollama.com/) running locally (free, no API key, auto-detected), or
  - an Anthropic or OpenAI API key (install the SDK with `pip install -e ".[anthropic]"` or `".[openai]"`, then set `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`)
- **[OpenSCAD](https://openscad.org/downloads.html)** — only required when an assembly needs a brand-new template generated, i.e. you ask for something the library doesn't already have. Not needed to run `generate`/`assemble` against existing templates, but you'll want it installed anyway to actually render the `.scad` output. If it's not on your `PATH`, point `OPENSCAD_PATH` at the executable. A recent build with the **Manifold** backend enabled (Preferences → Features) renders generated geometry dramatically faster than the older default backend — worth it if you plan to generate novel parts often.

---

## Quickstart

```bash
# install
pip install -e .

# set up an LLM provider (any one):
#   • local:  run Ollama (auto-detected, no extra install)
#   • cloud:  pip install -e ".[anthropic]"   (or ".[openai]")
#             export ANTHROPIC_API_KEY=...    (or OPENAI_API_KEY=...)

# generate a single part
scadgen generate "M8 hex bolt 40mm long" -o bolt.scad

# generate a full assembly from a description
scadgen assemble "make a desk lamp" -o lamp.scad --verbose

# guide the assembly with a reference image (vision models)
scadgen assemble "a birdcage" --image cage.png -o cage.scad

# preview the plan without generating
scadgen assemble "a 4-cylinder engine top end" --dry-run
```

Open the resulting `.scad` in [OpenSCAD](https://openscad.org/) to render, tweak parameters live, or export to STL for printing.

### Providers

Auto-detection order is **Ollama → Anthropic → OpenAI**; when a reference image is supplied, a vision-capable provider is preferred. Force one with `--provider {ollama,anthropic,openai}`.

---

## Architecture

```
scadgen/
├── agentic/      # the 5-stage assembly pipeline (decompose → execute)
├── assembly/     # connector model, position solver, renderer, builder
├── knowledge/    # constraints, standards resolution, harmonization
├── nlp/          # LLM providers (Ollama / Anthropic / OpenAI), extraction
├── core/         # engine + template registry
└── templates/    # 28 parametric .scad templates with metadata
```

- **~6,500 lines of Python**, **386 tests**
- Templates are plain `.scad` files with a `SCADGEN_META` YAML header — add a new part by dropping in a file; no code changes
- LLM-agnostic: swap providers via config or `--provider`

---

## Current status & roadmap

SCADGen has a **robust, working pipeline** — it reliably produces valid, correctly-positioned assemblies and never crashes on bad model output, and its template library compounds over time rather than staying fixed (see "Template library" above). The generated-templates cache lives in `generated_templates/` (`SCADGEN_GENERATED_DIR`-overridable); `scadgen clear-generated` resets it.

**Measured, not just claimed:** [`scripts/benchmark.py`](scripts/benchmark.py) runs a fixed set of prompts — some using the existing library, some forcing brand-new geometry — against Claude. Across 3 independent runs (18 assemblies total), every one succeeded, including two categories that were failing outright earlier the same day until a token-budget fix landed. Generated templates (9 across those runs) mostly passed OpenSCAD verification within one or two attempts — though take that fidelity number with a grain of salt: the generation prompt includes worked examples for cage/dome/ring-style geometry (the project's original proving case), so results on that specific shape family are somewhat inflated versus a truly unseen object. A couple of unrelated novel shapes (a tripod mount, a wall hook) passed just as cleanly, which is better evidence of real generalization than the headline number alone.

Known limitations:

- **Generation fidelity varies with model capability** — a frontier model (Claude, GPT-4o) reliably produces real, structured geometry for novel parts; smaller local models tend to fall back to plain primitives instead of using the pattern/custom-generation machinery
- **No feedback loop** — the system verifies that generated geometry *renders*, but doesn't yet look at *what* it rendered to critique and improve it

Planned next steps:

- [ ] Render → vision-critique → regenerate loop (compare the actual render against the request/reference image)
- [ ] Push decomposition further toward generation on weaker/local models
- [ ] Final-assembly render-check, not just per-template

---

## Tech stack

Python 3.10+ · OpenSCAD · Ollama / Anthropic / OpenAI · PyYAML · pytest

## License

MIT — see [LICENSE](LICENSE).
