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

## Requirements
 
- **Python 3.10 or newer.** Check what you have:
  - Windows: `py --version`
  - macOS / Linux: `python3 --version`
  - If it's missing, install from [python.org](https://www.python.org/downloads/). On Windows,
    tick **"Add python.exe to PATH"** in the installer.
- [`lark`](https://github.com/lark-parser/lark) - installed automatically.
- **No `git` required** for any of the commands below.


## Install

After installing, the command is named `gmpl-tex` and works the same on every platform.

**Windows** (PowerShell or Command Prompt):
 
```bat
py -m pip install "https://github.com/philippmoln/gmpl-tex/archive/refs/heads/main.zip"
```
 
**macOS / Linux:**
 
```bash
python3 -m pip install "https://github.com/philippmoln/gmpl-tex/archive/refs/heads/main.zip"
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

## Troubleshooting
 
- **A symbol shows up in red in the output.** That symbol is missing from your `model.json`
  lookup table - regenerate the table with `--json` after changing the model, then re-render.
