from dataclasses import dataclass
from abc import ABC


@dataclass
class Section(ABC):
    """Base for every renderable declaration. `line` is the 1-based source line,
    used for the `% Line N` comments in the generated LaTeX."""
    line: int | None


@dataclass
class AttributedStatement(Section):
    name: str
    domain: str | None
    attributes: list[str]


@dataclass
class Set(AttributedStatement):
    pass

@dataclass
class Parameter(AttributedStatement):
    pass


@dataclass
class Variable(AttributedStatement):
    pass


@dataclass
class Constraint(Section):
    """A relation rendered as a labelled equation.

        single bound:  lhs  op_left  rhs
        double bound:  lhs  op_left  middle  op_right  rhs   (e.g. lb <= e <= ub)

    `middle` / `op_right` stay None for a single-sided constraint.
    """
    name: str
    domain: str | None
    lhs: str
    op_left: str
    rhs: str
    middle: str | None = None
    op_right: str | None = None


@dataclass
class Objective(Section):
    verb: str
    name: str
    domain: str | None
    formula: str


@dataclass
class Model:
    sets:        list[Set]
    parameters:  list[Parameter]
    variables:   list[Variable]
    constraints: list[Constraint]
    objectives:  list[Objective]