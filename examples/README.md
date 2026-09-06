# Examples

Sample output from the agentic pipeline. Open any `.scad` file in
[OpenSCAD](https://openscad.org/) to render it.

- **`desk_lamp.scad`** — generated from the prompt `"make a desk lamp"`.
  Three parametric parts (base, gooseneck arm, shade) decomposed, connected,
  and positioned automatically by the assembly solver.

Regenerate or make your own:

```bash
scadgen assemble "make a desk lamp" -o my_lamp.scad --verbose
```
