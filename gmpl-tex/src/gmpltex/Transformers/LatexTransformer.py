"""Parse tree -> LaTeX

`LatexRenderer` walks the Lark parse tree and produces the `RenderModels`
dataclasses that `LatexAssembler` later turns into a document. It is the second
half of a two-phase design:

    phase 1  (NomenclatureBuilder)  parse tree -> JSON of {raw name: label}
    phase 2  (LatexRenderer)        parse tree + that JSON -> LaTeX

The JSON supplies *display labels* only. Everything structural -- index
domains, bounds, set/arithmetic operators -- is recovered here by re-walking
the tree, so the JSON stays the single source of truth for names and nothing
else.
"""

from lark import Transformer, Token, v_args
from ..DataModels.RenderModels import *


REQUIRED_JSON_SECTIONS = {"sets", "parameters", "variables", "constraints", "objectives"}
REQUIRED_STRUCTURE = \
"""{
    "sets": {},
    "parameters": {},
    "variables": {},
    "constraints": {},
    "objectives": {}
}
"""


# GMPL operator token -> LaTeX. Membership/subset variants are included because
# the same map serves both arithmetic comparisons (param_rho) and the wider set
# of relational operators allowed inside expressions (_rho).
LATEX_OPERATORS: dict[str, str] = {
    "<=": "\\le",
    ">=": "\\ge",
    "<>": "\\neq",
    "!=": "\\neq",
    "=":  "=",
    "==": "=",
    "<":  "<",
    ">":  ">",

    "in":         "\\in",
    "within":     "\\subseteq",
    "not in":     "\\notin",
    "not within": "\\not\\subseteq",
    "!in":        "\\notin",
    "!within":    "\\not\\subseteq",

    "union":   "\\cup",
    "diff":    "\\setminus",
    "symdiff": "\\triangle",
    "inter":   "\\cap",
    "cross":   "\\times",

    "..":   "\\ldots",
    "&":    "\\mathbin{\\Vert}",
    "*":    "\\cdot",
    "div":  "\\div",
    "mod":  "\\bmod",
    "**":   "^",
    "^":    "^",
    "=":    "=",
    "==":   "=",

    "and":  "\\land",
    "&&":   "\\land",
    "or":   "\\lor",
    "||":   "\\lor",

    "Infinity": "\\infty"
}


# TODO: aliases ('string' after a declared name) are parsed but not yet used.
# Decide whether an alias should take precedence over the JSON display label.
class LatexTransformer(Transformer):

    def _validate_nomenclature(self, nom) -> dict:
        if not isinstance(nom, dict):
            raise ValueError("Lookup table must be a valid dictionary.")
        for s in REQUIRED_JSON_SECTIONS:
            if s not in  nom:
                raise ValueError(
                    f"Lookup table is missing section '{s}'."
                    f"Table must maintain this structure: \n{REQUIRED_STRUCTURE}"
                )
            section = nom[s]
            if not isinstance(section, dict):
                raise ValueError("Section must be a valid dictionary.")
            for key, value in section.items():
                if not isinstance(value, str):
                    raise ValueError(
                        f"Label value '{value}' in section '{s}', key '{key}' must be a string."
                    )
                if '_' in value:
                    print(f"""\
Warning : Label values must not contain '_' (subscripts).
        | section : {s}
        | key     : {key}
        | value   : {value}
Subscripted labels may affect LaTeX rendering
""")
        return nom

    def __init__(self, nomenclature) -> None:
        super().__init__()
        try:
            self.nom = self._validate_nomenclature(nomenclature)
        except Exception as e:
            print(e)
            raise SystemExit(1)

        self._labels: dict[str, str] = {
            key: value
            for section in self.nom.values()
                for key, value in section.items()
        }

    # ----------------------------------------------------------------- helpers

    def _label(self, section: str, key, fallback: str) -> str:
        """Display label the user chose in the JSON for `key`, or `fallback`
        when the name is absent (should not happen for JSON from phase 1)."""
        return self.nom[section].get(str(key), fallback)

    def _display_name(self, name) -> str:
        """Resolve a referenced symbol to its display label (any section)."""
        return self._labels.get(name, name) # type: ignore

    def _latex_operator(self, op) -> str:
        return LATEX_OPERATORS.get(str(op), str(op))
    
    def _binary_expression(self, items: list) -> str:
        return f"{items[0]} {self._latex_operator(items[1])} {items[2]}"

    #_brace_indices yields indices *and* any filter condition
    # ("i, j : cond") for the surrounding \forall / aggregate clause.
    def _brace_indices(self, entries: list) -> str:
        return ", ".join(str(e[0]) for e in entries if e)

    def _brace_subscript(self, entries: list) -> str:
        index_parts = [str(e[1]) for e in entries if e and e[0]]
        conditions  = [str(e[1]) for e in entries if e and not e[0]]
        base = ", ".join(index_parts)
        return f"{base} : {', '.join(conditions)}" if conditions else base

    def _name_subscript(self, entries: list) -> str:
        """`_{i, j}` to append to a symbol name (empty when un-indexed)."""
        if not entries:
            return ""
        indices = ",".join(str(e[0]) for e in entries if e[0])
        return f"_{{{indices}}}"

    def _forall_domain(self, entries: list) -> str | None:
        """`\\forall i \\in I : cond` clause for a declaration's index set, or
        None when there is none. """
        if not entries:
            return None
        return f"\\forall\\ {self._brace_subscript(entries)}"
    
    def _display_missing_name_in_red(self, name: str) -> str:
        return f"\\color{{red}}{name}"

    # ---------------------------------------------------------------- terminals

    def STRING_LIT(self, token: Token) -> str:
        """Strip the surrounding quotes and collapse a doubled quote (the GMPL
        escape for a literal quote) back to a single one."""
        return token[1:-1].replace(token[0] * 2, token[0])

    def str_lit(self, items: list) -> str:
        return items[0]

    # -------------------------------------------------------------------- model

    def model(self, items: list) -> Model:
        return Model(
            sets        = [item for item in items if isinstance(item, Set)],
            parameters  = [item for item in items if isinstance(item, Parameter)],
            variables   = [item for item in items if isinstance(item, Variable)],
            constraints = [item for item in items if isinstance(item, Constraint)],
            objectives  = [item for item in items if isinstance(item, Objective)],
        )

    def statement(self, items: list) -> object:
        return items[0]

    # ---------------------------------------------------------------------- set

    @v_args(meta=True)
    def set_statement(self, meta, items: list) -> Set:
        domain_entries = items[2]
        name = self._label("sets", items[0], self._display_missing_name_in_red(items[0]))
        return Set(
            line       = meta.line,
            name       = name + self._name_subscript(domain_entries),
            domain     = self._forall_domain(domain_entries),
            attributes = [a for a in items[3:] if a],
        )

    def set_dimen(self, items: list) -> None:
        return None

    def set_within(self, items: list) -> str:
        return f"\\subseteq {items[1]}"

    def set_assign(self, items: list) -> str:
        return f":= {items[1]}"

    def set_default(self, items: list) -> None:
        return None

    # ---------------------------------------------------------------- parameter

    @v_args(meta=True)
    def parameter_statement(self, meta, items: list) -> Parameter:
        domain_entries = items[2]
        name = self._label("parameters", items[0], self._display_missing_name_in_red(items[0]))
        return Parameter(
            line       = meta.line,
            name       = name + self._name_subscript(domain_entries),
            domain     = self._forall_domain(domain_entries),
            attributes = [a for a in items[3:] if a],
        )

    def param_rho(self, items: list) -> str:
        return self._latex_operator(str(items[0]))

    def param_symbolic(self, items: list) -> None:
        return None

    def param_condition(self, items: list) -> str:
        op, expr = items[0], items[1]
        return f"{op} {expr}"

    def param_in(self, items: list) -> str:
        return f"\\in {items[1]}"

    def param_assign(self, items: list) -> str:
        return f":= {items[1]}"

    def param_default(self, items: list) -> None:
        return None

    # ----------------------------------------------------------------- variable

    @v_args(meta=True)
    def variable_statement(self, meta, items: list) -> Variable:
        name = self._label("variables", items[0], self._display_missing_name_in_red(items[0]))
        return Variable(
            line       = meta.line,
            name       = name + self._name_subscript(items[2]),
            domain     = self._forall_domain(items[2]),
            attributes = [a for a in items[3:] if a],
        )

    def var_less_than(self, items: list) -> str:
        return f"{self._latex_operator(items[0])} {items[1]}"

    def var_greater_than(self, items: list) -> str:
        return f"{self._latex_operator(items[0])} {items[1]}"

    def var_eq(self, items: list) -> str:
        return f"{self._latex_operator(items[0])} {items[1]}"

    # --------------------------------------------------------------- constraint

    @v_args(meta=True)
    def constraint_statement(self, meta, items: list) -> Constraint:
        constraint = items[4]
        constraint.line = meta.line
        constraint.name = self._label("constraints", items[1], self._display_missing_name_in_red(items[1]))
        # constraint() always leaves domain=None, so an unconditional assign
        # (None when there is no index set) preserves the previous behaviour.
        constraint.domain = self._forall_domain(items[3])
        return constraint

    def constraint(self, items: list) -> Constraint:
        match items:
            case [lhs, op, rhs]:
                return Constraint(
                    line     = None, 
                    name     = "", 
                    domain   = None,
                    lhs      = lhs, 
                    op_left  = self._latex_operator(op),
                    middle   = "", 
                    op_right = "", 
                    rhs      = rhs
                )
            case [lhs, op1, mid, op2, rhs]:
                # Normalise the mixed-operator double bounds to lb <= e <= ub.
                if op1 == ">=" and op2 == "<=":
                    lhs, mid = mid, lhs
                    op1 = "<="
                elif op1 == "<=" and op2 == ">=":
                    lhs, mid, rhs = rhs, lhs, mid
                    op2 = "<="
                return Constraint(
                    line     = None, 
                    name     = "", 
                    domain   = None,
                    lhs      = lhs, 
                    op_left  = self._latex_operator(op1),
                    middle   = mid, 
                    op_right = self._latex_operator(op2),
                    rhs      = rhs,
                )
            case _:
                # Unreachable: the grammar only yields 3- or 5-item constraints.
                return Constraint()  # type: ignore

    # ---------------------------------------------------------------- objective

    @v_args(meta=True)
    def objective_statement(self, meta, items: list) -> Objective:
        return Objective(
            line    = meta.line,
            verb    = items[0],
            name    = self._label("objectives", items[1], self._display_missing_name_in_red(items[1])),
            domain  = self._forall_domain(items[3]),
            formula = items[4],
        )

    def verb(self, items: list) -> str:
        return items[0]

    def minimize(self, items: list) -> str:
        return "\\min"

    def maximize(self, items: list) -> str:
        return "\\max"

    # =========================================================================
    #  Expression ladder (mirrors the expression_N levels in grammar.lark).
    #  Binary handlers receive [lhs, OP_token, rhs]; the operator token sits at
    #  items[1] and is skipped.
    # =========================================================================

    # -- level 13-11: logical or, and, not --
    or_expr = and_expr = _binary_expression

    def not_expr(self, items: list) -> str:
        return f"\\lnot {items[1]}"

    # -- level 10: relational (non-associative) --
    relational_expr = _binary_expression

    # -- level 9: union / difference / symmetric difference --
    union_expr = diff_expr = symdiff_expr = _binary_expression

    # -- level 8 - 7: intersection, cross product --
    inter_expr = cross_expr = _binary_expression

    # -- level 6: ranges --
    range_expr = _binary_expression

    def range_by_expr(self, items: list) -> str:
        lower, dots, upper, step = items[0], self._latex_operator(items[1]), items[2], items[4]
        return f"\\{{{lower}, {lower}+{step}, {dots}, {upper}\\}}"

    # -- level 5: string concatenation --
    concat_expr = _binary_expression

    # -- level 4: + - less --
    expression_4 = _binary_expression

    def op_less(self, items: list) -> str:
        lhs, rhs = items[0], items[2]
        return f"\\max({lhs} - {rhs},\\ 0)"

    # -- level 3: * / div mod --
    mul = int_div = mod = _binary_expression

    def div(self, items: list) -> str:
        # If the numerator already carries \left( ... \right), fold the fraction
        # inside those delimiters rather than nesting a second pair.
        if items[0].startswith("\\left(") and items[0].endswith("\\right)"):
            items[0] = items[0][len("\\left(\n"):-len("\n\\right)")]
            return f"\\left(\n\\frac{{{items[0]}}}{{{items[2]}}}\n\\right)"
        return f"\\frac{{{items[0]}}}{{{items[2]}}}"

    # -- level 2: unary +/- --
    def expression_2(self, items: list) -> str:
        op, expr = items[0], items[1]
        return f"{op}{expr}"

    # -- level 1: power --
    expression_1 = _binary_expression

    # ------------------------------------------------------- primary expressions

    def primary_expression(self, items: list) -> str:
        return items[0]

    def number(self, items: list) -> str:
        return str(items[0])

    def infinity_lit(self, items: list) -> str:
        return self._latex_operator(items[0])

    def name(self, items: list) -> str:
        # A bare name in an expression is resolved against the json labels.
        return self._display_name(str(items[0]))

    def subscript_ref(self, items: list) -> str:
        return f"{self._display_name(items[0])}_{{{items[1]}}}"

    def func_call(self, items: list) -> str:
        name = str(items[0])
        args = items[1]
        if name == "card":
            return f"\\left| {args[0]} \\right|"
        if name in ("min", "max"):
            return f"\\{name}\\left( {', '.join(str(a) for a in args)} \\right)"
        return f"\\mathrm{{{name}}}\\left( {', '.join(str(a) for a in args)} \\right)"

    def func_call_noargs(self, items: list) -> str:
        return f"\\mathrm{{{str(items[0])}}}\\left( \\right)"

    def set_value(self, items: list) -> str:
        """Render a brace expression used as a value (set literal or set
        comprehension), as opposed to an index domain."""
        entries = items[0]
        if not entries:
            return "\\{\\}"

        index_entries = [(d, dom) for d, dom in entries if d]
        conditions    = [dom for d, dom in entries if not d]

        if conditions:
            # comprehension: \{ index_exprs \mid condition \}
            index_parts = [str(dom) for _, dom in index_entries]
            cond_str    = ", ".join(str(c) for c in conditions)
            return f"\\{{{', '.join(index_parts)} \\mid {cond_str}\\}}"

        # plain literal: recover each value from its "dummy \in value" entry
        parts = []
        for dummy, domain in index_entries:
            marker = f"{str(dummy)} \\in "
            if str(domain).startswith(marker):
                parts.append(str(domain)[len(marker):])
            else:
                parts.append(str(dummy))
        if len(parts) == 1 and parts[0].startswith("\\{"):
            return parts[0]
        return f"\\{{{', '.join(parts)}\\}}"

    def paren_expr(self, items: list) -> str:
        elems = items[0]
        if len(elems) == 1:
            return f"({elems[0]})"
        return "(" + ", ".join(str(e) for e in elems) + ")"

    # ------------------------------------------------- iterated (aggregate) ops

    def sum_expr(self, items: list) -> str:
        return f"\\sum_{{{self._brace_subscript(items[1])}}} {items[2]}"

    def prod_expr(self, items: list) -> str:
        return f"\\prod_{{{self._brace_subscript(items[1])}}} {items[2]}"

    def min_expr(self, items: list) -> str:
        return f"\\min_{{{self._brace_subscript(items[1])}}} {items[2]}"

    def max_expr(self, items: list) -> str:
        return f"\\max_{{{self._brace_subscript(items[1])}}} {items[2]}"

    def forall_expr(self, items: list) -> str:
        return f"\\forall\\, {self._brace_subscript(items[1])} : {items[2]}"

    def exists_expr(self, items: list) -> str:
        return f"\\exists\\, {self._brace_subscript(items[1])} : {items[2]}"

    def setof_expr(self, items: list) -> str:
        entries, element = items[1], items[2]
        conditions = ", ".join(entry[1] for entry in entries)
        return f"\\{{{element} \\mid {conditions}\\}}"

    # ---------------------------------------------- conditional (branched) exprs

    def if_then_expr(self, items: list) -> str:
        condition = items[1]
        then_expr = items[3]
        return f"""\
    \\begin{{cases}}
    {then_expr} & \\text{{if }} {condition}
    \\end{{cases}}"""

    def if_then_else_expr(self, items: list) -> str:
        condition = items[1]
        then_expr = items[3]
        else_expr = items[5]
        return f"""
    \\begin{{cases}}
        {then_expr} & \\text{{if }}{condition} \\\\
        {else_expr} & \\text{{otherwise}}
    \\end{{cases}}"""

    # ------------------------------------------- brace / index domain plumbing
    # A brace expression is transformed into a list of (index_name, latex)
    # entries; entries whose index_name is "" are filter conditions.

    def domain(self, items: list) -> list:
        return items[0]

    def brace_list(self, items: list) -> list:
        return items

    def brace_set(self, items: list) -> list:
        return items[0]

    def empty_set(self, items: list) -> list:
        return []

    def filtered_brace_set(self, items: list) -> list:
        entries, condition = items[0], items[1]
        return entries + [("", condition)]

    def idx_in(self, items: list) -> tuple:
        name, expr = items[0], items[2]
        return (name, f"{name} \\in {expr}")

    def idx_bare(self, items: list) -> tuple:
        """Bare set with no explicit dummy: invent one from the set's first
        letter (or "i" for a range, which has no usable letter)."""
        idx = items[0]
        if "\\ldots" in idx:
            return ("i", f"i \\in {idx}")
        dummy = idx[0].lower()
        return (dummy, f"{dummy} \\in {idx}")

    def idx_tuple_in(self, items: list) -> tuple:
        index_names = [str(n) for n in items[0]]   # ["i", "j"] from (i,j)
        set_expr = items[2]                         # e.g. "LINKS"
        combined = ",".join(index_names)            # "i,j"
        return (combined, f"({combined}) \\in {set_expr}")

    # ------------------------------------------------------------ list plumbing

    def subscript_list(self, items: list) -> str:
        return ", ".join(str(i) for i in items)

    def arg_list(self, items: list) -> list:
        return items

    def expression_list(self, items: list) -> list:
        return items

    def alias(self, items: list) -> str:
        return items[0]
    
    # -------------------------------------------------------------- shared attr

    def num_attr(self, items: list) -> str:
        return items[0]

    def int_attr(self, items: list) -> str:
        return "\\in \\mathbb{Z}"

    def binary_attr(self, items: list) -> str:
        return "\\in \\{0,1\\}" 