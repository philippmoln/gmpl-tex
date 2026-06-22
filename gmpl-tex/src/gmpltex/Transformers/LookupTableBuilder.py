from lark import Transformer

class NomenclatureBuilder(Transformer):
    """Phase 1: walk the parse tree and collect the *names* the user may want to
    relabel, as a JSON-ready dict of one section per declaration kind::
 
        {"sets": {raw: label}, "parameters": {...}, "variables": {...},
         "constraints": {...}, "objectives": {...}}
 
    Each label starts equal to its raw name; the user edits the labels before
    phase 2 renders the LaTeX. Only the declaration name matters here, so every
    other rule is pruned to None by ``__default__``.
    """


    def __default__(self, data, children, meta) -> None: # type: ignore
        return None

    def statement(self, items: list) -> list | None:
        return items[0]

    def set_statement(self, items: list) -> tuple:
        return "set", str(items[0])
    
    def parameter_statement(self, items: list) -> tuple:
        return "parameter", str(items[0])

    def variable_statement(self, items: list) -> tuple:
        return "variable", str(items[0])
    
    def constraint_statement(self, items: list) -> tuple:
        return "constraint", str(items[1])
    
    def objective_statement(self, items: list) -> tuple:
        return "objective", str(items[1])

    def model(self, items) -> dict:
        return {
            "sets": {
                i[1]: i[1]
                for i in items if i[0] == "set"
            },
            "parameters": {
                i[1]: i[1]
                for i in items if i[0] == "parameter"
            },
            "variables": {
                i[1]: i[1]
                for i in items if i[0] == "variable"
            },
            "constraints": {
                i[1]: i[1]
                for i in items if i[0] == "constraint"
            },
            "objectives": {
                i[1]: i[1]
                for i in items if i[0] == "objective"
            }
        }