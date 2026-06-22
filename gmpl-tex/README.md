# gmpl-tex

Convert a subset of **GMPL** (GNU MathProg) optimization models into **LaTeX**, so
the constraints, sets, parameters, variables and objectives you wrote for a solver
can go straight into a paper with readable, renamed symbols.

The tool works in two phases so you stay in control of the notation:

1. **Lookup-table generation** - parse `model.mod` into a JSON table listing every
   set, parameter, variable, constraint and objective name. Each name maps to a
   label you can edit.
2. **LaTeX generation** - render the model to LaTeX, substituting your edited
   labels from the JSON table.

## Install

No Python project setup required for users - pick whichever you have:

```bash
# with uv (no install, runs in a throwaway environment)
uvx --from git+https://github.com/<you>/gmpl-tex gmpl-tex --help

# with pipx (installs the gmpl-tex command onto your PATH)
pipx install git+https://github.com/<you>/gmpl-tex

# with plain pip, into a virtual environment
pip install git+https://github.com/<you>/gmpl-tex
```

## Usage

```text
gmpl-tex model.mod [lookup.json] --json
gmpl-tex model.mod [lookup.json] [output.tex] --latex
```

A full run, start to finish:

```bash
# 1. generate the editable lookup table (writes model.json)
gmpl-tex model.mod --json

# 2. open model.json and edit the label on the right-hand side of each entry,
#    e.g. "finishTime": "fTime"

# 3. render LaTeX using your edited labels (writes model.tex)
gmpl-tex model.mod model.json --latex
```

If you skip step 1 and run `gmpl-tex model.mod --latex` directly, a default table
is created automatically (labels equal to the raw names) and used. If a
`model.json` already exists next to the model, it is reused as-is and never
overwritten.

An example model is included under [`examples/model.mod`](examples/model.mod).

## Requirements

- Python 3.10 or newer
- [`lark`](https://github.com/lark-parser/lark) (installed automatically)