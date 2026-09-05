from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="scadgen",
        description="AI-powered parametric OpenSCAD generator",
    )
    parser.add_argument("--version", action="version", version="scadgen 0.1.0")
    parser.add_argument("--provider", default="auto", choices=["auto", "ollama", "openai"],
                        help="LLM provider (for interactive mode)")
    parser.add_argument("--output-dir", default="generated_scad",
                        help="Output directory (for interactive mode)")

    subparsers = parser.add_subparsers(dest="command")

    # generate
    gen = subparsers.add_parser("generate", help="Generate a .scad file")
    gen.add_argument("description", nargs="?", default="", help="NL description of the part")
    gen.add_argument("--template", "-t", default="", help="Template ID (bypasses NLP)")
    gen.add_argument("--set", "-s", nargs="*", default=[], help="Parameter overrides: key=value")
    gen.add_argument("--output", "-o", default="", help="Output file path")
    gen.add_argument("--output-dir", default="", help="Output directory")
    gen.add_argument("--provider", default="auto", choices=["auto", "ollama", "openai"])
    gen.add_argument("--model", default="", help="LLM model name override")
    gen.add_argument("--dry-run", action="store_true", help="Show params without generating")
    gen.add_argument("--stdout", action="store_true", help="Print SCAD to stdout")
    gen.add_argument("-v", "--verbose", action="store_true")

    # list
    lst = subparsers.add_parser("list", help="List available templates")
    lst.add_argument("--category", "-c", default="", help="Filter by category")

    # info
    inf = subparsers.add_parser("info", help="Show template details")
    inf.add_argument("template_id", help="Template ID")

    args = parser.parse_args(argv)

    if args.command is None:
        _cmd_interactive(args)
        return

    if args.command == "generate":
        _cmd_generate(args)
    elif args.command == "list":
        _cmd_list(args)
    elif args.command == "info":
        _cmd_info(args)


def _cmd_interactive(args: argparse.Namespace) -> None:
    from scadgen.core.engine import SCADEngine
    from scadgen.repl import InteractiveSession

    engine = SCADEngine(provider=args.provider)
    session = InteractiveSession(engine, output_dir=args.output_dir)
    session.run()


def _cmd_generate(args: argparse.Namespace) -> None:
    from scadgen.core.engine import SCADEngine

    engine = SCADEngine(provider=args.provider)

    if args.model:
        if engine.config.provider in ("ollama", "auto"):
            engine.config.ollama_model = args.model
        else:
            engine.config.openai_model = args.model

    params = {}
    for item in args.set:
        if "=" not in item:
            print(f"Error: --set value must be key=value, got: {item}", file=sys.stderr)
            sys.exit(1)
        key, val = item.split("=", 1)
        try:
            params[key] = float(val) if "." in val else int(val)
        except ValueError:
            if val.lower() in ("true", "false"):
                params[key] = val.lower() == "true"
            else:
                params[key] = val

    if not args.description and not args.template:
        print("Error: provide a description or --template", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        if args.description:
            extraction = engine.extractor.extract(args.description)
            tmpl = extraction.template
            merged = {**extraction.parameters, **params}
        else:
            tmpl = engine.registry.get(args.template)
            merged = params

        validated = tmpl.validate_params(merged)
        final = tmpl.apply_defaults(validated)

        print(f"Template: {tmpl.template_id}")
        print(f"Module:   {tmpl.module_name}")
        print("Parameters:")
        for p in tmpl.parameters:
            val = final.get(p.name, p.default)
            src = "set" if p.name in params else ("nlp" if p.name in merged else "default")
            print(f"  {p.name} = {val}  ({src})")

        derived = tmpl.compute_derived(final)
        if derived:
            print("Derived:")
            for k, v in derived.items():
                print(f"  {k} = {v:.4g}")
        return

    output_path = args.output
    if not output_path and args.output_dir:
        name = args.template or "output"
        output_path = str(Path(args.output_dir) / f"{name}.scad")
    if not output_path and not args.stdout:
        output_path = str(Path("generated_scad") / f"generated_{args.template or 'part'}.scad")

    from scadgen.exceptions import ConstraintViolationError
    try:
        result = engine.generate(
            description=args.description,
            template_id=args.template,
            params=params,
            output_path="" if args.stdout else output_path,
        )
    except ConstraintViolationError as e:
        print("Geometry error:", file=sys.stderr)
        for v in e.violations:
            print(f"  - {v}", file=sys.stderr)
        sys.exit(1)

    if args.stdout:
        print(result.scad_code)
    else:
        print(f"Generated: {result.output_path}")
        if args.verbose:
            print(f"Template:  {result.template.template_id}")
            for k, v in result.parameters.items():
                print(f"  {k} = {v}")
            for k, v in result.derived_values.items():
                print(f"  {k} = {v:.4g} (derived)")

    for w in result.warnings:
        print(f"Warning: {w}", file=sys.stderr)


def _cmd_list(args: argparse.Namespace) -> None:
    from scadgen.core.engine import SCADEngine

    engine = SCADEngine()
    templates = engine.registry.list_templates(category=args.category)

    if not templates:
        print("No templates found.")
        return

    max_id = max(len(t.template_id) for t in templates)
    for t in templates:
        cat = f"[{t.category}]" if t.category else ""
        print(f"  {t.template_id:<{max_id}}  {t.description:<45} {cat}")


def _cmd_info(args: argparse.Namespace) -> None:
    from scadgen.core.engine import SCADEngine

    engine = SCADEngine()
    try:
        tmpl = engine.registry.get(args.template_id)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Template: {tmpl.template_id}")
    print(f"Module:   {tmpl.module_name}")
    print(f"Category: {tmpl.category}")
    print(f"Description: {tmpl.description}")
    if tmpl.tags:
        print(f"Tags: {', '.join(tmpl.tags)}")
    if tmpl.aliases:
        print(f"Aliases: {', '.join(tmpl.aliases)}")
    print()
    print("Parameters:")
    for p in tmpl.parameters:
        range_str = ""
        if p.min is not None and p.max is not None:
            range_str = f" [{p.min} .. {p.max}]"
        unit_str = f" {p.unit}" if p.unit else ""
        print(f"  {p.name}: {p.type}, default={p.default}{unit_str}{range_str}")
        if p.description:
            print(f"    {p.description}")

    if tmpl.connectors:
        print()
        print("Connectors:")
        for c in tmpl.connectors:
            print(f"  {c.name}: {c.type} at {c.origin} -> {c.direction}")

    if tmpl.derived_expressions:
        print()
        print("Derived values:")
        for name, expr in tmpl.derived_expressions.items():
            print(f"  {name} = {expr}")
