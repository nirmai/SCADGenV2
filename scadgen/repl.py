"""Interactive REPL for SCADgen."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from scadgen.core.engine import SCADEngine
from scadgen.exceptions import ConstraintViolationError, SCADGenError
from scadgen.knowledge.constraints import harmonize_linked_params, validate_constraints


class InteractiveSession:
    def __init__(self, engine: SCADEngine, output_dir: str = "generated_scad"):
        self.engine = engine
        self.output_dir = output_dir
        self.overrides: dict[str, Any] = {}
        self._counters: dict[str, int] = {}
        self._last_result = None

    def run(self) -> None:
        self._print_banner()
        while True:
            try:
                text = input("\nSCADgen> ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\nBye.")
                break
            if not text:
                continue
            if text.lower() in ("quit", "exit", "/quit", "/exit"):
                print("Bye.")
                break
            self._handle(text)

    def _print_banner(self) -> None:
        print()
        print("  SCADgen v0.1.0 — AI parametric CAD generator")
        print("  Type a part description to generate, or /help for commands.")
        print(f"  Output: {self.output_dir}/")

    def _handle(self, text: str) -> None:
        if text.startswith("/"):
            parts = text[1:].split(None, 1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""
            handler = {
                "help": self._cmd_help,
                "list": self._cmd_list,
                "info": self._cmd_info,
                "set": self._cmd_set,
                "clear": self._cmd_clear,
                "output": self._cmd_output,
                "last": self._cmd_last,
                "provider": self._cmd_provider,
                "assemble": self._cmd_assemble,
            }.get(cmd)
            if handler:
                handler(arg)
            else:
                print(f"  Unknown command: /{cmd}  (type /help)")
            return

        self._generate(text)

    def _cmd_help(self, _arg: str) -> None:
        print()
        print("  Just type a part description to generate a .scad file.")
        print()
        print("  Commands:")
        print("    /list [category]     List available templates")
        print("    /info <template>     Show template parameter details")
        print("    /set key=value ...   Set parameter overrides")
        print("    /clear               Clear parameter overrides")
        print("    /output <directory>  Change output directory")
        print("    /last                Show last generated part info")
        print("    /provider <name>     Switch LLM provider (ollama/openai/anthropic)")
        print("    /assemble <desc>     Generate a multi-part assembly from description")
        print("    /help                Show this help")
        print("    quit                 Exit")
        print()
        print("  Examples:")
        print('    M8 bolt 40mm long')
        print('    32 tooth gear module 2.5 with 10mm face width')
        print('    sphere 50mm diameter')
        print('    /set bore_diam=10')
        print('    small gear for a clock mechanism')

    def _cmd_list(self, arg: str) -> None:
        templates = self.engine.registry.list_templates(category=arg)
        if not templates:
            print("  No templates found.")
            return
        print()
        max_id = max(len(t.template_id) for t in templates)
        for t in templates:
            print(f"    {t.template_id:<{max_id}}  {t.description}")

    def _cmd_info(self, arg: str) -> None:
        if not arg:
            print("  Usage: /info <template_id>")
            return
        try:
            tmpl = self.engine.registry.get(arg.strip())
        except SCADGenError as e:
            print(f"  Error: {e}")
            return

        print(f"\n  {tmpl.template_id} — {tmpl.description}")
        if tmpl.aliases:
            print(f"  Aliases: {', '.join(tmpl.aliases)}")
        print()
        for p in tmpl.parameters:
            range_str = ""
            if p.min is not None and p.max is not None:
                range_str = f"  [{p.min}..{p.max}]"
            unit = f" {p.unit}" if p.unit else ""
            print(f"    {p.name}: {p.type}, default={p.default}{unit}{range_str}")
            if p.description:
                print(f"      {p.description}")

        if tmpl.derived_expressions:
            print("\n  Derived:")
            for name, expr in tmpl.derived_expressions.items():
                print(f"    {name} = {expr}")

    def _cmd_set(self, arg: str) -> None:
        if not arg:
            if self.overrides:
                pairs = "  ".join(f"{k}={v}" for k, v in self.overrides.items())
                print(f"  Current overrides: {pairs}")
            else:
                print("  No overrides set. Usage: /set key=value ...")
            return

        for item in arg.split():
            if "=" not in item:
                print(f"  Invalid: {item} (use key=value)")
                continue
            key, val = item.split("=", 1)
            self.overrides[key] = _parse_value(val)

        pairs = "  ".join(f"{k}={v}" for k, v in self.overrides.items())
        print(f"  Overrides: {pairs}")

    def _cmd_clear(self, _arg: str) -> None:
        self.overrides.clear()
        print("  Overrides cleared.")

    def _cmd_output(self, arg: str) -> None:
        if not arg:
            print(f"  Output directory: {self.output_dir}")
            return
        self.output_dir = arg.strip()
        print(f"  Output directory: {self.output_dir}")

    def _cmd_last(self, _arg: str) -> None:
        if self._last_result is None:
            print("  No parts generated yet.")
            return
        r = self._last_result
        print(f"\n  Template:  {r.template.template_id}")
        params = "  ".join(f"{k}={v}" for k, v in r.parameters.items())
        print(f"  Params:    {params}")
        if r.derived_values:
            derived = "  ".join(f"{k}={v:.4g}" for k, v in r.derived_values.items())
            print(f"  Derived:   {derived}")
        print(f"  Output:    {r.output_path}")

    def _cmd_provider(self, arg: str) -> None:
        if not arg:
            print(f"  Provider: {self.engine.config.provider}")
            return
        name = arg.strip().lower()
        if name not in ("ollama", "openai", "anthropic", "auto"):
            print(f"  Unknown provider: {name}  (use ollama, openai, or auto)")
            return
        self.engine.config.provider = name
        self.engine._extractor = None
        print(f"  Provider: {name}")

    def _cmd_assemble(self, arg: str) -> None:
        if not arg:
            print("  Usage: /assemble <description>")
            print("  Example: /assemble make a desk lamp")
            return

        from scadgen.agentic import assemble
        from scadgen.exceptions import AgenticError

        print(f"\n  Assembling: \"{arg}\"")
        try:
            result = assemble(
                description=arg,
                engine=self.engine,
                output_dir=self.output_dir,
                verbose=True,
            )
        except AgenticError as e:
            print(f"\n  Assembly error: {e}")
            return
        except Exception as e:
            print(f"\n  Error: {e}")
            return

        print(f"\n  Assembly generated: {result.output_path}")
        print(f"  Parts: {len(result.plan.parts)}")
        if result.generated_templates:
            print(f"  New templates: {len(result.generated_templates)}")
        for w in result.warnings:
            print(f"  Warning: {w}")

    def _generate(self, description: str) -> None:
        # Step 1: Extract template + params (resolver + LLM)
        try:
            extraction = self.engine.extractor.extract(description)
        except SCADGenError as e:
            print(f"\n  Error: {e}")
            return
        except Exception as e:
            print(f"\n  Error: {e}")
            return

        template = extraction.template
        extracted_params = extraction.parameters
        resolved = extraction.resolved_standards

        # Step 2: Show what we understood
        print(f"\n  Template:  {template.template_id} — {template.description}")

        if resolved and resolved.standards_matched:
            print(f"  Standards: {', '.join(resolved.standards_matched)}")

        # Step 3: Categorize params — locked (from standards/user) vs editable
        skip_display = {"fn", "fn_bolt", "fn_thread", "fn_nut"}
        resolved_keys = set(resolved.resolved_params.keys()) if resolved else set()
        override_keys = set(self.overrides.keys())

        locked: dict[str, Any] = {}
        editable: list[tuple] = []  # (ParameterDef, current_value, source)

        for p in template.parameters:
            if p.name in skip_display:
                continue
            if p.name in override_keys:
                locked[p.name] = self.overrides[p.name]
            elif p.name in resolved_keys:
                locked[p.name] = extracted_params.get(p.name, resolved.resolved_params[p.name])
            else:
                val = extracted_params.get(p.name, p.default)
                source = "inferred" if (p.name in extracted_params and val != p.default) else "default"
                editable.append((p, val, source))

        # Show locked params
        if locked:
            locked_str = "  ".join(f"{k}={v}" for k, v in locked.items())
            print(f"  Resolved:  {locked_str}")

        # Step 4: Let user specify changes in natural language, then ask remaining
        final_merged = dict(extracted_params)
        final_merged.update(self.overrides)
        matched: dict[str, Any] = {}

        if editable:
            # Show what's still open
            print()
            for pdef, current_val, source in editable:
                unit = f" {pdef.unit}" if pdef.unit else ""
                tag = f"({source})" if source != "default" else "(default)"
                print(f"    {pdef.description}: {current_val}{unit}  {tag}")

            print()
            try:
                spec = input("  Change anything? (e.g. 'length 40, threads off') or Enter to accept: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n  Cancelled.")
                return

            if spec:
                # Match against ALL params (not just editable) so user can override locked values too
                all_params = [p for p in template.parameters if p.name not in skip_display]
                matched = _fuzzy_match_params(spec, all_params)
                for name, val in matched.items():
                    final_merged[name] = val

                # Show what was matched
                if matched:
                    pairs = "  ".join(f"{k}={v}" for k, v in matched.items())
                    print(f"  Updated:   {pairs}")

                # Ask about anything the fuzzy match didn't cover (editable only)
                unmatched = [
                    (p, v, s) for p, v, s in editable
                    if p.name not in matched
                ]
                for pdef, current_val, source in unmatched:
                    unit = f" {pdef.unit}" if pdef.unit else ""
                    prompt_str = f"    {pdef.description} [{current_val}{unit}]: "
                    try:
                        answer = input(prompt_str).strip()
                    except (KeyboardInterrupt, EOFError):
                        print("\n  Cancelled.")
                        return
                    if answer:
                        final_merged[pdef.name] = _parse_value(answer)

        # Step 5: Validate, harmonize, check constraints, generate
        user_explicit = set(self.overrides.keys())
        user_explicit.update(matched.keys())

        try:
            validated = template.validate_params(final_merged)
            final_params = template.apply_defaults(validated)

            final_params, link_messages = harmonize_linked_params(
                template, final_params, user_explicit,
            )

            errors, constraint_warnings = validate_constraints(template, final_params)
            if errors:
                raise ConstraintViolationError(errors)

            scad_code = self.engine.renderer.render(template, final_params)
            derived = template.compute_derived(final_params)
        except ConstraintViolationError as e:
            print("\n  Geometry error:")
            for v in e.violations:
                print(f"    - {v}")
            print("  Please adjust parameters.")
            return
        except (SCADGenError, ValueError) as e:
            print(f"\n  Error: {e}")
            return

        # Step 6: Write output
        tid = template.template_id
        count = self._counters.get(tid, 0) + 1
        self._counters[tid] = count
        filename = f"{tid}_{count:03d}.scad"
        out_path = Path(self.output_dir) / filename
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(scad_code, encoding="utf-8")

        all_warnings = list(link_messages) + constraint_warnings
        from scadgen.types import GenerationResult
        result = GenerationResult(
            scad_code=scad_code,
            output_path=str(out_path),
            template=template,
            parameters=final_params,
            derived_values=derived,
            warnings=all_warnings,
        )
        self._last_result = result

        # Step 7: Print result
        print()
        for msg in link_messages:
            print(f"  Info:      {msg}")
        for w in constraint_warnings:
            print(f"  Warning:   {w}")
        if derived:
            derived_str = "  ".join(f"{k}={v:.4g}" for k, v in derived.items())
            print(f"  Derived:   {derived_str}")

        print(f"  Output:    {out_path}")

        if self.overrides:
            self.overrides.clear()


def _parse_value(val: str) -> Any:
    if val.lower() in ("true", "false", "yes", "no", "on", "off"):
        return val.lower() in ("true", "yes", "on")
    try:
        return float(val) if "." in val else int(val)
    except ValueError:
        return val


def _fuzzy_match_params(
    text: str, params: list,
) -> dict[str, Any]:
    """Match natural language like 'shaft length 30, head flat 20, threads off'
    against parameter names and descriptions."""
    import re

    # Build keyword → param mapping from names and descriptions
    keyword_map: dict[str, str] = {}  # keyword -> param.name
    for p in params:
        # Map full param name (e.g. "head_height" as typed)
        keyword_map[p.name.lower()] = p.name
        # Map param name words: "shaft_len" → "shaft", "len"
        for word in p.name.replace("_", " ").split():
            keyword_map[word.lower()] = p.name
        # Map description words (skip short/common ones)
        for word in p.description.lower().split():
            cleaned = word.strip("().,")
            if len(cleaned) >= 3 and cleaned not in ("the", "and", "for", "with", "from"):
                if cleaned not in keyword_map:
                    keyword_map[cleaned] = p.name

    result: dict[str, Any] = {}
    text_lower = text.lower()

    # Strategy 1: Find "keyword number" or "keyword = number" patterns
    for match in re.finditer(r"(\w+)\s*=?\s*(\d+(?:\.\d+)?)", text_lower):
        word, num_str = match.group(1), match.group(2)
        if word in keyword_map:
            pname = keyword_map[word]
            if pname not in result:
                result[pname] = _parse_value(num_str)

    # Strategy 2: Find "keyword on/off/true/false/yes/no" or "keyword=false" patterns
    for match in re.finditer(r"(\w+)\s*=?\s*(on|off|true|false|yes|no)\b", text_lower):
        word, bool_str = match.group(1), match.group(2)
        if word in keyword_map:
            pname = keyword_map[word]
            if pname not in result:
                result[pname] = _parse_value(bool_str)

    # Strategy 3: "no <keyword>" or "<keyword> off" for booleans
    for match in re.finditer(r"\bno\s+(\w+)", text_lower):
        word = match.group(1)
        if word in keyword_map:
            pname = keyword_map[word]
            param = next((p for p in params if p.name == pname), None)
            if param and param.type == "bool" and pname not in result:
                result[pname] = False

    # Strategy 4: Multi-word matching — try pairs of consecutive words
    words = re.findall(r"\w+", text_lower)
    for i in range(len(words) - 1):
        bigram = f"{words[i]} {words[i + 1]}"
        # Check if bigram matches a param name (e.g. "head flat" → "head_flat")
        underscore_form = f"{words[i]}_{words[i + 1]}"
        matching_param = next((p for p in params if p.name == underscore_form), None)
        if matching_param and matching_param.name not in result:
            # Look for a number after the bigram
            rest = text_lower[text_lower.index(bigram) + len(bigram):]
            num_match = re.match(r"\s*=?\s*(\d+(?:\.\d+)?)", rest)
            if num_match:
                result[matching_param.name] = _parse_value(num_match.group(1))
            # Check for boolean
            bool_match = re.match(r"\s+(on|off|true|false|yes|no)\b", rest)
            if bool_match and matching_param.type == "bool":
                result[matching_param.name] = _parse_value(bool_match.group(1))

    return result
