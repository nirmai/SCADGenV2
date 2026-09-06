# Examples

Sample output from the agentic pipeline. Open any `.scad` file in
[OpenSCAD](https://openscad.org/) to render it.

- **`desk_lamp.scad`** — generated from the prompt `"make a desk lamp"`.
  Three parametric parts (base, gooseneck arm, shade) decomposed, connected,
  and positioned automatically by the assembly solver.

- **`birdcage.scad`** — generated from `"a birdcage with a domed top and
  vertical bars"`. No birdcage template existed beforehand: the decomposer
  identified 5 parts (base, radial cage bars, a top ring, a domed lattice
  top, a finial), routed the dome to the LLM as a brand-new template since
  no primitive could represent it, generated and OpenSCAD-render-verified
  that template (`generated_cage_dome.scad`, included alongside), and
  assembled everything into the final file.

Regenerate or make your own:

```bash
scadgen assemble "make a desk lamp" -o my_lamp.scad --verbose
scadgen assemble "a birdcage with a domed top" -o my_cage.scad --verbose
```
