from ..DataModels.RenderModels import *

_PREAMBLE = """\
\\documentclass{article}
\\usepackage[utf8]{inputenc}
\\usepackage{amsmath}
\\usepackage{amssymb}
\\usepackage{xcolor}

\\begin{document}
"""

def _wrap_into_latex_skeleton(body: str) -> str:
    """Wrap math blocks in a compilable LaTeX document skeleton."""
    return _PREAMBLE + body + "\n\\end{document}"


def assemble_latex(model: Model, standalone: bool = True) -> str:
    """Render a whole model to LaTeX.

    With ``standalone`` (the default) the output is a compilable document --
    documentclass, packages and ``document`` environment included. Pass
    ``standalone=False`` to emit only the math blocks, e.g. for \\input-ing into
    an existing paper.
    """
    sections: list[str] = []

    sections.append(f"\\section{{Input data}}\n")
    sections.append(f"\\subsection{{Sets}}\n")
    sections.append(set_param_block(model.sets)) # type: ignore

    sections.append(f"\\subsection{{Parameters}}\n")
    sections.append(set_param_block(model.parameters)) # type: ignore

    sections.append(f"\\section{{Model}}\n")
    sections.append(f"\\subsection{{Variables}}\n")
    sections.append(variables_block(model.variables))

    sections.append(f"\\subsection{{Constraints}}\n")
    sections.append(constraints_block(model.constraints))

    sections.append(f"\\subsection{{Objectives}}\n")
    sections.append(objectives_block(model.objectives))

    body = "\n".join(sections)

    return _wrap_into_latex_skeleton(body) if standalone else body


def itemize_block(items: list[AttributedStatement]) -> str:
    if not items:
        return ""
    
    list_items = "\n".join(
        f"% Line {item.line}\n"
        "\\item $" + item.name
        + ", \\quad ".join(
            [f"{attr}" for attr in item.attributes]
            + ([item.domain] if item.domain else [])
        ) + "$"
        for item in items
    )

    return f"""\
\\begin{{itemize}}
{list_items}
\\end{{itemize}}
"""


def math_block(items: list[AttributedStatement]) -> str:
    """Render set or parameter declarations, one display-math block each.

    Both share the same shape (name, optional attributes, optional domain),
    so sets and parameters go through here.
    """
    blocks = []
    for item in items:
        attrs = [a for a in item.attributes if a]
        content = ", \n\\quad ".join(f"{item.name} {attr}" for attr in attrs) if attrs else item.name
        if item.domain:
            content += f",\n\\quad {item.domain}"
        blocks.append(f"""\
% Line {item.line}
\\[
{content}
\\]
""")
    return "\n".join(blocks)


def set_param_block(items: list[AttributedStatement]) -> str:
    
    if not items:
        return ""

    blocks = []
    declarations = [i for i in items if not any(":=" in a for a in (i.attributes or []))]
    definitions  = [i for i in items if any(":=" in a for a in (i.attributes or []))]

    if declarations:
        blocks.append(itemize_block(declarations))
        
    if definitions:
        blocks.append(math_block(definitions))

    return "\n".join(blocks)


def variables_block(variables: list[Variable]) -> str:
    """Render all variable declarations as a single itemize list."""
    return itemize_block(variables) # type: ignore


def constraints_block(constraints: list[Constraint]) -> str:
    """Render each constraint as a labelled equation."""
    blocks = []
    for c in constraints:
        blocks.append(f"""\
% Line {c.line}
\\begin{{equation}}
\\label{{Eq:{c.name}}}
{c.lhs}
{c.op_left} 
{c.middle + "\n" if c.middle else ""} {c.op_right if c.op_right else ""} {c.rhs}
{c.domain + "\n" if c.domain else ""}\\end{{equation}}
""")
    return "\n".join(blocks)


def objectives_block(objectives: list[Objective]) -> str:
    """Render each objective as a labelled equation (formula → sense)."""
    blocks = []
    for obj in objectives:
        blocks.append(f"""\
% Line {obj.line}
\\begin{{equation}}
\\label{{Eq:{obj.name}}}
{obj.formula}
\\to
{obj.verb}
\\end{{equation}}
""")
    return "\n".join(blocks)