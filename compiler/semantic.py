"""
compiler/semantic.py
Semantic analyser: walks the AST, checks types, scoping, and usage rules.
Produces Diagnostic objects; does NOT raise exceptions for semantic errors.
"""
from __future__ import annotations

from typing import List, Optional, Set

from compiler.ast_nodes import (
    ASTNode, ASTVisitor, Assign, BinaryExpr, Block, CharLiteral, ExprStmt,
    FloatLiteral, ForStmt, FuncCall, FuncDecl, Identifier, IfStmt, IntLiteral,
    Param, Program, PointerAssign, ReturnStmt, StringLiteral, UnaryExpr, VarDecl, WhileStmt, ArrayAccess, ArrayAssign,
)
from compiler.models import (
    Diagnostic, DiagnosticCategory, Severity, SourceSpan,
)
from compiler.symbol_table import Symbol, SymbolTable as ST


# ---------------------------------------------------------------------------
# Type system helpers
# ---------------------------------------------------------------------------

NUMERIC_TYPES: Set[str] = {"int", "float"}
PRIMITIVE_TYPES: Set[str] = {"int", "float", "char", "void"}

def _is_valid_variable_type(type_name: str) -> bool:
    if type_name in PRIMITIVE_TYPES - {"void"}:
        return True

    if type_name.endswith("*"):
        base_type = type_name[:-1]
        return base_type in {"int", "float", "char"}

    return False

# Which types are compatible for assignment: dest = src
_ASSIGN_COMPAT = {
    ("int",   "int"):   True,
    ("int",   "float"): False,    # narrowing – warn
    ("float", "int"):   True,     # widening implicit
    ("float", "float"): True,
    ("char",  "char"):  True,
    ("char",  "int"):   True,     # common in C
    ("int",   "char"):  True,
}


def _assign_compatible(dest: str, src: str) -> bool:
    if dest == src:
        return True

    if dest.endswith("*") or src.endswith("*"):
        return False

    return _ASSIGN_COMPAT.get((dest, src), False)


def _arithmetic_result(left: str, right: str) -> Optional[str]:
    if left == "float" or right == "float":
        return "float"
    if left == "int" and right == "int":
        return "int"
    if left in ("int", "float", "char") and right in ("int", "float", "char"):
        return "int"
    return None


def _relational_result(left: str, right: str) -> Optional[str]:
    if left in NUMERIC_TYPES | {"char"} and right in NUMERIC_TYPES | {"char"}:
        return "int"   # C boolean is int
    return None


# ---------------------------------------------------------------------------
# Semantic analyser (visitor)
# ---------------------------------------------------------------------------

class SemanticAnalyzer(ASTVisitor):
    """
    Performs semantic analysis on the AST.
    Call analyze(program_node) to get (diagnostics, symbol_table_snapshot).
    """

    def __init__(self) -> None:
        self._st = ST()
        self._diagnostics: List[Diagnostic] = []
        self._current_function_return_type: Optional[str] = None
        self._function_definitions_seen: Set[str] = set()

    # ---------------------------------------------------------------- public

    def analyze(self, root: Program):
        """Run semantic analysis and return (diagnostics, st_snapshot)."""
        self._st = ST()
        self._diagnostics = []
        self._current_function_return_type = None
        self._function_definitions_seen = set()

        self._st.push_scope("global")
        root.accept(self)
        snapshot = self._st.full_snapshot()   # capture before popping
        self._st.pop_scope()

        return self._diagnostics, snapshot

    # ---------------------------------------------------------------- helpers

    def _error(self, code: str, msg: str, span: SourceSpan, explanation: str = "") -> None:
        self._diagnostics.append(Diagnostic(
            code=code,
            category=DiagnosticCategory.SEMANTIC,
            message=msg,
            severity=Severity.ERROR,
            span=span,
            source="semantic",
            explanation=explanation,
        ))

    def _warning(self, code: str, msg: str, span: SourceSpan, explanation: str = "") -> None:
        self._diagnostics.append(Diagnostic(
            code=code,
            category=DiagnosticCategory.SEMANTIC,
            message=msg,
            severity=Severity.WARNING,
            span=span,
            source="semantic",
            explanation=explanation,
        ))

    def _infer_type(self, node: Optional[ASTNode]) -> Optional[str]:
        """Return the inferred type of an expression node (best effort)."""
        if node is None:
            return None
        if isinstance(node, IntLiteral):
            return "int"
        if isinstance(node, FloatLiteral):
            return "float"
        if isinstance(node, CharLiteral):
            return "char"
        if isinstance(node, StringLiteral):
            return "char*"   # simplified
        if isinstance(node, Identifier):
            sym = self._st.lookup(node.name)
            return sym.type_name if sym else None
        if isinstance(node, ArrayAccess):
            sym = self._st.lookup(node.name)
            if sym is None:
                return None
            if sym.is_array:
                return sym.type_name
            if sym.type_name.endswith("*"):
                return sym.type_name[:-1]
            return sym.type_name
        if isinstance(node, BinaryExpr):
            return node.inferred_type
        if isinstance(node, UnaryExpr):
            if node.op == "&":
                if isinstance(node.operand, (Identifier, ArrayAccess)):
                    operand_type = self._infer_type(node.operand)
                    if operand_type and operand_type != "unknown":
                        return operand_type + "*"
                return None

            if node.op == "*" and node.operand is not None:
                operand_type = self._infer_type(node.operand)
                if operand_type and operand_type.endswith("*"):
                    return operand_type[:-1]
                return None

            return node.inferred_type
        if isinstance(node, FuncCall):
            sym = self._st.lookup(node.name)
            if sym and sym.kind == "function":
                return sym.return_type
            return None
        if isinstance(node, Assign):
            sym = self._st.lookup(node.name)
            return sym.type_name if sym else None
        return None

    # ---------------------------------------------------------------- visitors

    def visit_program(self, node: Program) -> None:
        # Pass 1: Register function signatures before analyzing any body.
        for decl in node.declarations:
            if isinstance(decl, FuncDecl):
                if self._st.lookup(decl.name) is None:
                    sym = Symbol(
                        name=decl.name,
                        type_name=decl.return_type,
                        kind="function",
                        span=decl.span,
                        return_type=decl.return_type,
                        param_types=[p.type_name for p in decl.params],
                    )
                    self._st.define(sym)

        # Pass 2: Analyze declarations and function bodies.
        for decl in node.declarations:
            decl.accept(self)

    def visit_func_decl(self, node: FuncDecl) -> None:
        if node.return_type not in PRIMITIVE_TYPES:
            self._error(
                "SEM005",
                f"Unknown return type '{node.return_type}' for function '{node.name}'",
                node.span,
            )

        # Function signatures were registered in visit_program().
        # Detect repeated function definitions during the second pass.
        if node.name in self._function_definitions_seen:
            self._error(
                "SEM002",
                f"Duplicate function declaration '{node.name}'",
                node.span,
                explanation="A function with this name is already defined in this scope.",
            )
        else:
            self._function_definitions_seen.add(node.name)

        previous_return_type = self._current_function_return_type
        self._current_function_return_type = node.return_type

        self._st.push_scope(f"function:{node.name}")

        for param in node.params:
            param.accept(self)

        # Analyze the function body's statements directly in the function scope.
        # Nested blocks inside these statements still create their own scopes.
        if node.body:
            for stmt in node.body.statements:
                stmt.accept(self)

        self._st.pop_scope()
        self._current_function_return_type = previous_return_type

    def visit_var_decl(self, node: VarDecl) -> None:
        if node.type_name != "void" and not _is_valid_variable_type(node.type_name):
            self._error(
                "SEM005",
                f"Unknown type '{node.type_name}'",
                node.span,
            )
        if node.type_name == "void":
            self._error(
                "SEM006",
                f"Variable '{node.name}' cannot be declared as void",
                node.span,
                explanation="void is only valid as a function return type or empty parameter list.",
            )

        sym = Symbol(
            name=node.name,
            type_name=node.type_name,
            kind="variable",
            span=node.span,
            is_array=node.array_size is not None,
            array_size=(
                node.array_size.value
                if isinstance(node.array_size, IntLiteral)
                else None
            ),
        )
        if not self._st.define(sym):
            self._error(
                "SEM002",
                f"Duplicate declaration of '{node.name}' in the same scope",
                node.span,
                explanation="A variable with this name is already declared in this block.",
            )

        if node.initializer:
            node.initializer.accept(self)
            init_type = self._infer_type(node.initializer)
            if init_type and init_type != "unknown":
                if not _assign_compatible(node.type_name, init_type):
                    self._error(
                        "SEM003",
                        (
                            f"Type mismatch: cannot initialize '{node.type_name} {node.name}'"
                            f" with value of type '{init_type}'"
                        ),
                        node.span,
                        explanation=(
                            f"The declared type '{node.type_name}' is not compatible "
                            f"with the initializer type '{init_type}'."
                        ),
                    )

    def visit_param(self, node: Param) -> None:
        if node.type_name == "void":
            self._error("SEM006", "Parameter cannot be of type void", node.span)
        if node.name:
            sym = Symbol(name=node.name, type_name=node.type_name, kind="parameter", span=node.span)
            if not self._st.define(sym):
                self._error("SEM002", f"Duplicate parameter name '{node.name}'", node.span)

    def _visit_scoped_branch(
        self,
        branch: Optional[ASTNode],
        scope_name: str,
    ) -> None:
        if branch is None:
            return

        if isinstance(branch, Block):
            self._st.push_scope(scope_name)
            for stmt in branch.statements:
                stmt.accept(self)
            self._st.pop_scope()
        else:
            branch.accept(self)

    def visit_block(self, node: Block) -> None:
        self._st.push_scope(f"block (line {node.span.start.line})")
        for stmt in node.statements:
            stmt.accept(self)
        self._st.pop_scope()

    def visit_expr_stmt(self, node: ExprStmt) -> None:
        if node.expr:
            node.expr.accept(self)

    def visit_if_stmt(self, node: IfStmt) -> None:
        if node.condition:
            node.condition.accept(self)

        if node.then_branch:
            self._visit_scoped_branch(
                node.then_branch,
                f"if-then block (line {node.then_branch.span.start.line})",
            )

        if node.else_branch:
            self._visit_scoped_branch(
                node.else_branch,
                f"if-else block (line {node.else_branch.span.start.line})",
            )

    def visit_while_stmt(self, node: WhileStmt) -> None:
        if node.condition:
            node.condition.accept(self)

        if node.body:
            self._visit_scoped_branch(
                node.body,
                f"while body block (line {node.body.span.start.line})",
            )

    def visit_for_stmt(self, node: ForStmt) -> None:
        self._st.push_scope(f"for loop (line {node.span.start.line})")

        if node.init:
            node.init.accept(self)

        if node.condition:
            node.condition.accept(self)

        if node.update:
            node.update.accept(self)

        if node.body:
            self._visit_scoped_branch(
                node.body,
                f"for body block (line {node.body.span.start.line})",
            )

        self._st.pop_scope()

    def visit_return_stmt(self, node: ReturnStmt) -> None:
        if node.value:
            node.value.accept(self)

        ret_type = self._current_function_return_type
        if ret_type is None:
            return

        if ret_type == "void":
            if node.value is not None:
                self._error(
                    "SEM007",
                    "void function must not return a value",
                    node.span,
                )
        else:
            if node.value is None:
                self._error(
                    "SEM008",
                    f"Function with return type '{ret_type}' returns nothing",
                    node.span,
                )
            else:
                val_type = self._infer_type(node.value)
                if val_type and not _assign_compatible(ret_type, val_type):
                    self._error(
                        "SEM007",
                        (
                            f"Return type mismatch: function returns '{ret_type}'"
                            f" but expression has type '{val_type}'"
                        ),
                        node.span,
                        explanation=(
                            f"The function is declared to return '{ret_type}' but the "
                            f"return expression has type '{val_type}'."
                        ),
                    )

    def visit_assign(self, node: Assign) -> None:
        sym = self._st.lookup(node.name)
        if sym is None:
            self._error(
                "SEM001",
                f"Use of undeclared identifier '{node.name}'",
                node.span,
                explanation=(
                    f"'{node.name}' has not been declared before this assignment. "
                    "Declare it with an appropriate type first."
                ),
            )
        if node.value:
            node.value.accept(self)
            val_type = self._infer_type(node.value)
            if sym and val_type:
                if not _assign_compatible(sym.type_name, val_type):
                    self._error(
                        "SEM003",
                        (
                            f"Type mismatch: cannot assign '{val_type}' to"
                            f" '{sym.type_name} {node.name}'"
                        ),
                        node.span,
                        explanation=(
                            f"The variable '{node.name}' has type '{sym.type_name}' "
                            f"but the right-hand side has type '{val_type}'."
                        ),
                    )

    
    def visit_pointer_assign(self, node: PointerAssign) -> None:
        if node.target is None or node.value is None:
            return

        node.target.accept(self)
        node.value.accept(self)

        if not isinstance(node.target, UnaryExpr) or node.target.op != "*":
            self._error(
                "SEM011",
                "Pointer assignment requires a dereference target",
                node.span,
            )
            return

        pointer_type = self._infer_type(node.target.operand)

        if pointer_type is None:
            return

        if not pointer_type.endswith("*"):
            return


        target_type = pointer_type[:-1]
        value_type = self._infer_type(node.value)

        if value_type is not None and not _assign_compatible(target_type, value_type):
            self._error(
                "SEM003",
                f"Type mismatch: cannot assign '{value_type}' through pointer to '{target_type}'",
                node.span,
            )


    def visit_binary_expr(self, node: BinaryExpr) -> None:
        if node.left:
            node.left.accept(self)
        if node.right:
            node.right.accept(self)

        left_t = self._infer_type(node.left)
        right_t = self._infer_type(node.right)

        if node.op in ("/", "%") and isinstance(node.right, IntLiteral):
            if node.right.value == 0:
                self._error(
                    "SEM012",
                    f"Division or modulo by zero using operator '{node.op}'",
                    node.span,
                )

        if node.op in ("+", "-", "*", "/", "%"):
            result_type = _arithmetic_result(left_t or "", right_t or "")
            if node.op == "%" and (
                left_t == "float" or right_t == "float"
            ):
                self._error(
                    "SEM011",
                    "Modulo operator '%' requires integer operands",
                    node.span,
                )
                node.inferred_type = "unknown"
                return

            if (
                left_t is not None
                and right_t is not None
                and left_t != "unknown"
                and right_t != "unknown"
                and result_type is None
            ):
                self._error(
                    "SEM011",
                    f"Incompatible operands for arithmetic operator '{node.op}': "
                    f"'{left_t}' and '{right_t}'",
                    node.span,
                )

            node.inferred_type = result_type or "unknown"
        elif node.op in ("<", "<=", ">", ">=", "==", "!="):
            result_type = _relational_result(left_t or "", right_t or "")

            if (
                node.op in ("==", "!=")
                and left_t == right_t
                and left_t is not None
                and left_t.endswith("*")
            ):
                result_type = "int"

            if (
                left_t is not None
                and right_t is not None
                and left_t != "unknown"
                and right_t != "unknown"
                and result_type is None
            ):
                self._error(
                    "SEM011",
                    f"Incompatible operands for relational operator '{node.op}': "
                    f"'{left_t}' and '{right_t}'",
                    node.span,
                )

            node.inferred_type = result_type or "unknown"
        elif node.op in ("&&", "||"):
            if left_t == "void" or right_t == "void":
                self._error(
                    "SEM011",
                    f"Logical operator '{node.op}' requires scalar operands, "
                    f"got '{left_t}' and '{right_t}'",
                    node.span,
                )
                node.inferred_type = "unknown"
            else:
                node.inferred_type = "int"
        else:
            node.inferred_type = "unknown"

    def visit_unary_expr(self, node: UnaryExpr) -> None:
        if node.operand:
            node.operand.accept(self)

        op_t = self._infer_type(node.operand)

        if node.op == "-":
            if op_t is not None and op_t not in NUMERIC_TYPES:
                self._error(
                    "SEM011",
                    f"Unary operator '-' requires a numeric operand, got '{op_t}'",
                    node.span,
                )
                node.inferred_type = "unknown"
            else:
                node.inferred_type = op_t or "unknown"

        elif node.op == "!":
            if op_t == "void":
                self._error(
                    "SEM011",
                    "Logical NOT operator '!' requires a scalar operand, got 'void'",
                    node.span,
                )
                node.inferred_type = "unknown"
            else:
                node.inferred_type = "int"

        elif node.op == "*":
            if op_t is not None and not op_t.endswith("*"):
                self._error(
                    "SEM011",
                    f"Cannot dereference non-pointer expression of type '{op_t}'",
                    node.span,
                )
                node.inferred_type = "unknown"
            elif op_t is not None:
                node.inferred_type = op_t[:-1]
            else:
                node.inferred_type = "unknown"

        elif node.op == "&":
            if isinstance(node.operand, Identifier):
                sym = self._st.lookup(node.operand.name)
                node.inferred_type = sym.type_name + "*" if sym else "unknown"
            else:
                node.inferred_type = "unknown"

        else:
            node.inferred_type = op_t



    def visit_identifier(self, node: Identifier) -> None:
        sym = self._st.lookup(node.name)
        if sym is None:
            self._error(
                "SEM001",
                f"Use of undeclared identifier '{node.name}'",
                node.span,
                explanation=(
                    f"'{node.name}' is used but has not been declared in the current scope."
                ),
            )
        else:
            node.inferred_type = sym.type_name

    def visit_array_access(self, node: ArrayAccess) -> None:
        sym = self._st.lookup(node.name)

        if node.index is not None:
            node.index.accept(self)
            index_type = self._infer_type(node.index)

            if index_type is not None and index_type != "int":
                self._error(
                    "SEM011",
                    f"Array index must have type 'int', got '{index_type}'",
                    node.index.span,
                )

        if sym is None:
            self._error(
                "SEM001",
                f"Use of undeclared array or pointer '{node.name}'",
                node.span,
            )
            return

        if sym.is_array:
            if (
                node.index is not None
                and isinstance(node.index, IntLiteral)
                and sym.array_size is not None
                and not (0 <= node.index.value < sym.array_size)
            ):
                self._error(
                    "SEM011",
                    f"Array index {node.index.value} is out of bounds for "
                    f"'{node.name}' of size {sym.array_size}",
                    node.index.span,
                )

            node.inferred_type = sym.type_name
            return

        if sym.type_name.endswith("*"):
            node.inferred_type = sym.type_name[:-1]
            return

        self._error(
            "SEM011",
            f"'{node.name}' is not an array or pointer and cannot be indexed",
            node.span,
        )

    def visit_array_assign(self, node: ArrayAssign) -> None:
        sym = self._st.lookup(node.name)

        if node.index is not None:
            node.index.accept(self)
            index_type = self._infer_type(node.index)

            if index_type is not None and index_type != "int":
                self._error(
                    "SEM011",
                    f"Array index must have type 'int', got '{index_type}'",
                    node.index.span,
                )

        if node.value is not None:
            node.value.accept(self)

        if sym is None:
            self._error(
                "SEM001",
                f"Use of undeclared array '{node.name}'",
                node.span,
            )
            return

        is_pointer = sym.type_name.endswith("*")

        if not sym.is_array and not is_pointer:
            self._error(
                "SEM011",
                f"'{node.name}' is not an array or pointer and cannot be indexed",
                node.span,
            )
            return

        if (
            node.index is not None
            and isinstance(node.index, IntLiteral)
            and sym.array_size is not None
            and not (0 <= node.index.value < sym.array_size)
        ):
            self._error(
                "SEM011",
                f"Array index {node.index.value} is out of bounds for "
                f"'{node.name}' of size {sym.array_size}",
                node.index.span,
            )

        value_type = self._infer_type(node.value) if node.value else None
        element_type = sym.type_name[:-1] if is_pointer else sym.type_name

        if value_type and value_type != "unknown":
            if not _assign_compatible(element_type, value_type):
                self._error(
                    "SEM003",
                    f"Cannot assign type '{value_type}' to array element "
                    f"of type '{element_type}'",
                    node.span,
                )

    def visit_func_call(self, node: FuncCall) -> None:
        sym = self._st.lookup(node.name)

        for arg in node.arguments:
            arg.accept(self)

        if sym is None:
            self._error(
                "SEM001",
                f"Call to undeclared function '{node.name}'",
                node.span,
            )
        elif sym.kind != "function":
            self._error(
                "SEM009",
                f"'{node.name}' is not a function",
                node.span,
            )
        else:
            node.inferred_type = sym.return_type

            expected = len(sym.param_types)
            got = len(node.arguments)

            if expected != got:
                self._error(
                    "SEM010",
                    (
                        f"Function '{node.name}' expects {expected} argument(s)"
                        f" but {got} were provided"
                    ),
                    node.span,
                )

            for index, (arg, param_type) in enumerate(
                zip(node.arguments, sym.param_types), start=1
            ):
                arg_type = self._infer_type(arg)

                if arg_type and not _assign_compatible(param_type, arg_type):
                    self._error(
                        "SEM003",
                        (
                            f"Type mismatch in argument {index} of function "
                            f"'{node.name}': expected '{param_type}'"
                            f" but got '{arg_type}'"
                        ),
                        arg.span,
                    )


    def visit_int_literal(self, node: IntLiteral) -> None:
        pass  # type is implicit: int

    def visit_float_literal(self, node: FloatLiteral) -> None:
        pass

    def visit_char_literal(self, node: CharLiteral) -> None:
        pass

    def visit_string_literal(self, node: StringLiteral) -> None:
        pass
