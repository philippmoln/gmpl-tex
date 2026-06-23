from lark import Lark
from lark.exceptions import UnexpectedInput, GrammarError
from pathlib import Path
from .Transformers.LatexTransformer import *
from .Transformers.LookupTableBuilder import *
from .Modules.LatexAssembler import *

import sys
import json
import argparse
import importlib.resources as resources

BANNER = """\
 ██████╗ ███╗   ███╗██████╗ ██╗      ████████╗███████╗██╗  ██╗
██╔════╝ ████╗ ████║██╔══██╗██║      ╚══██╔══╝██╔════╝╚██╗██╔╝
██║  ███╗██╔████╔██║██████╔╝██║         ██║   █████╗   ╚███╔╝
██║   ██║██║╚██╔╝██║██╔═══╝ ██║         ██║   ██╔══╝   ██╔██╗
╚██████╔╝██║ ╚═╝ ██║██║     ███████╗    ██║   ███████╗██╔╝ ██╗
 ╚═════╝ ╚═╝     ╚═╝╚═╝     ╚══════╝    ╚═╝   ╚══════╝╚═╝  ╚═╝

GMPL → LaTeX converter
"""

def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog = "gmpl-tex",
        description = BANNER,
        formatter_class = argparse.RawDescriptionHelpFormatter,
        usage = "\n"
                " %(prog)s model.mod [lookup.json] --json\n"
                " %(prog)s model.mod [lookup.json] [output.tex] --latex"
    )
    parser.add_argument("files", nargs="+", type=Path, metavar="file")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--json",  action="store_true", help="Parse the GMPL model into a .json lookup table")
    mode.add_argument("--latex", action="store_true", help="Render LaTeX from the .json lookup table")
    return parser


def parse_model(model_src: Path):
    """LALR parser for the model grammar.

    ``maybe_placeholders`` keeps optional slots (e.g. ``[alias]``, ``[domain]``)
    at stable item indices; ``propagate_positions`` exposes ``meta.line`` for the
    ``% Line N`` comments.
    """

    try:
        grammar = (resources.files(__package__) / "grammar.lark").read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError):
        print("Internal error: the bundled 'grammar.lark' is missing from the gmpl-tex package.",
              file=sys.stderr)
        raise SystemExit(1)

    try:
        model = model_src.read_text(encoding="utf-8")
        parser = Lark(grammar, start="model", parser="lalr",
                      maybe_placeholders=True, propagate_positions=True)
        return parser.parse(model)
    except FileNotFoundError:
        print(f"Model file '{model_src}' not found.", file=sys.stderr)
        raise SystemExit(1)
    except GrammarError as e:
        print(f"Invalid bundled grammar: {e}", file=sys.stderr)
        raise SystemExit(1)
    except UnexpectedInput as e:
        print(f"Parse error in model '{model_src}' at line {e.line}, column {e.column}:", 
              file=sys.stderr)
        print(e.get_context(model), file=sys.stderr) # type: ignore
        print(f"Please check your model near here and try again.", file=sys.stderr)
        raise SystemExit(1)


def run_json(files: list[Path]) -> None:
    model_src = files[0]
    default_json_name = Path(model_src).stem
    output_json = files[1] if len(files) == 2 else Path(f"{default_json_name}.json")

    syntax_tree = parse_model(model_src)
    nomenclature = NomenclatureBuilder().transform(syntax_tree)

    with output_json.open("w", encoding="utf-8") as f:
        json.dump(nomenclature, f, indent=4, ensure_ascii=False)


def run_latex(files: list[Path]) -> None:
    model_src = files[0]
    default_json_name = Path(model_src).stem
    input_json = Path(f"{default_json_name}.json")

    if len(files) >= 2:
        input_json = files[1]
    elif not input_json.exists():
        run_json(files)

    default_latex_name = Path(model_src).stem
    output = files[2] if len(files) == 3 else Path(f"{default_latex_name}.tex")
    syntax_tree = parse_model(model_src)

    try:
        with input_json.open(encoding="utf-8") as f:
            nomenclature = json.load(f)
    except FileNotFoundError as e:
        print(f"File '{e.filename}' not found.", file=sys.stderr)
        raise SystemExit(1)
    except json.JSONDecodeError as e:
        print(f"Could not parse json '{input_json}': {e}", file=sys.stderr)
        raise SystemExit(1)
    except ValueError as e:
        print(f"Invalid json lookup table '{input_json}':", file=sys.stderr)
        print(f"  {e}", file=sys.stderr)
        raise SystemExit(1)

    transformer = LatexTransformer(nomenclature)
    model = transformer.transform(syntax_tree)
    output.write_text(assemble_latex(model), encoding="utf-8")


def main() -> None:
    arg_parser = build_argument_parser()

    if len(sys.argv) == 1:
        arg_parser.print_help()
        sys.exit(0)

    args = arg_parser.parse_args()

    if args.json:
        if len(args.files) not in (1, 2):
            arg_parser.error("--json expects: model.mod [output.json]")
        run_json(args.files)
    elif args.latex:
        if len(args.files) not in (1, 2, 3):
            arg_parser.error("--latex expects: model.mod [lookup.json] [output.tex]")
        run_latex(args.files)


if __name__ == "__main__":
    main()