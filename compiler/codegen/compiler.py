from __future__ import annotations

from compiler.ast.nodes import (
    AssignmentStatement,
    BinaryExpression,
    BlockExpression,
    BlockStatement,
    BoolLiteral,
    BreakStatement,
    CallExpression,
    ContinueStatement,
    Expression,
    FloatLiteral,
    ForStatement,
    FunctionDeclaration,
    Identifier,
    IfExpression,
    IfStatement,
    IndexAssignmentStatement,
    IndexExpression,
    IntegerLiteral,
    LetStatement,
    ListLiteral,
    MapLiteral,
    PrintStatement,
    Program,
    ReturnStatement,
    ThrowStatement,
    TryCatchStatement,
    ExpressionStatement,
    Statement,
    StringLiteral,
    UnaryExpression,
    UnitLiteral,
    WhileStatement,
)
from compiler.bytecode.instructions import Instruction, Op
from compiler.bytecode.program import CompiledProgram, FunctionInfo
from compiler.csv_schema import CsvSchemaError, parse_csv_schema
from compiler.diagnostics import SourceSpan
from runtime.values import UNIT, annotation_has_float, annotation_is_float


class Compiler:
    def __init__(self, inferred_types: dict[int, TypeAnnotation] | None = None) -> None:
        self.inferred_types = inferred_types or {}
        self.instructions: list[Instruction] = []
        self.functions: dict[str, FunctionInfo] = {}
        self.loop_stack: list[tuple[list[int], int, int, int]] = []
        self.try_depth = 0
        self.catch_depth = 0
        self.annotations: dict[str, TypeAnnotation] = {}

    def compile(self, program: Program) -> CompiledProgram:
        self.instructions = []
        self.functions = {}
        self.loop_stack = []
        self.try_depth = 0
        self.catch_depth = 0
        self.annotations = {}
        for stmt in program.statements:
            if isinstance(stmt, FunctionDeclaration):
                self.compile_function(stmt)
        for stmt in program.statements:
            if isinstance(stmt, FunctionDeclaration):
                continue
            self.compile_statement(stmt)
        self.emit(Op.HALT, span=program.span)
        return CompiledProgram(tuple(self.instructions), dict(self.functions))

    def compile_function(self, stmt: FunctionDeclaration) -> None:
        name = stmt.name.name
        if name in self.functions:
            raise RuntimeError(f"Duplicate function '{name}'")
        saved_instructions = self.instructions
        saved_loops = self.loop_stack
        saved_try_depth = self.try_depth
        saved_catch_depth = self.catch_depth
        saved_annotations = self.annotations
        self.instructions = []
        self.loop_stack = []
        self.try_depth = 0
        self.catch_depth = 0
        self.annotations = {}
        try:
            self.compile_expression(stmt.body)
            self.emit(Op.RETURN, span=stmt.body.span if stmt.body.span is not None else stmt.span)
            instructions = tuple(self.instructions)
        finally:
            self.instructions = saved_instructions
            self.loop_stack = saved_loops
            self.try_depth = saved_try_depth
            self.catch_depth = saved_catch_depth
            self.annotations = saved_annotations
        self.functions[name] = FunctionInfo(
            name=name,
            parameters=tuple(parameter.name.name for parameter in stmt.parameters),
            instructions=instructions,
            span=stmt.name.span,
            parameter_annotations=tuple(parameter.type_name for parameter in stmt.parameters),
            return_annotation=stmt.return_type,
        )

    def emit(self, op: Op, arg=None, span: SourceSpan | None = None) -> int:
        self.instructions.append(Instruction(op, arg, span=span))
        return len(self.instructions) - 1

    def patch(self, index: int, target: int) -> None:
        ins = self.instructions[index]
        if ins.op not in (Op.JUMP, Op.JUMP_IF_FALSE, Op.ITER_NEXT, Op.SETUP_TRY):
            raise RuntimeError(f"Cannot patch non-jump instruction at {index}: {ins!r}")
        self.instructions[index] = Instruction(ins.op, target, span=ins.span)

    def _emit_loop_exit_pops(self, span: SourceSpan | None) -> None:
        """Pop try handlers entered inside the loop a jump is leaving.

        Handlers that were already active when the loop started must stay:
        a `break` exits the loop, not the surrounding `try`.
        """
        loop_try_depth = self.loop_stack[-1][2]
        loop_catch_depth = self.loop_stack[-1][3]
        for _ in range(self.try_depth - loop_try_depth):
            self.emit(Op.POP_TRY, span=span)
        for _ in range(self.catch_depth - loop_catch_depth):
            self.emit(Op.END_CATCH, span=span)

    def compile_statement(self, stmt: Statement) -> None:
        if isinstance(stmt, LetStatement):
            self.compile_expression(stmt.value)
            if stmt.type_name is not None:
                self.emit(Op.COERCE, stmt.type_name, stmt.span)
            self.emit(
                Op.STORE_CONST if stmt.constant else Op.DECLARE_NAME,
                stmt.name.name,
                stmt.name.span,
            )
            if stmt.type_name is not None:
                self.annotations[stmt.name.name] = stmt.type_name
            else:
                self.annotations.pop(stmt.name.name, None)
            return
        if isinstance(stmt, AssignmentStatement):
            self.compile_expression(stmt.value)
            annotation = self.annotations.get(stmt.name.name)
            if annotation is not None:
                self.emit(Op.COERCE, annotation, stmt.span)
            self.emit(Op.STORE_NAME, stmt.name.name, stmt.name.span)
            return
        if isinstance(stmt, IndexAssignmentStatement):
            self.compile_expression(stmt.target.collection)
            self.compile_expression(stmt.target.index)
            root_name = self._index_root(stmt.target).name
            root_annotation = self.annotations.get(root_name)
            map_annotation = (
                root_annotation
                if isinstance(stmt.target.collection, Identifier)
                and root_annotation is not None
                and root_annotation.name == "Map"
                and len(root_annotation.arguments) == 2
                else None
            )
            if map_annotation is not None:
                self.emit(Op.COERCE, map_annotation.arguments[0], stmt.span)
            self.compile_expression(stmt.value)
            if map_annotation is not None:
                self.emit(Op.COERCE, map_annotation.arguments[1], stmt.span)
            self.emit(Op.STORE_INDEX, root_name, stmt.span)
            return
        if isinstance(stmt, BreakStatement):
            if not self.loop_stack:
                raise RuntimeError("`break` outside a loop reached codegen")
            self._emit_loop_exit_pops(stmt.span)
            self.loop_stack[-1][0].append(self.emit(Op.JUMP, None, stmt.span))
            return
        if isinstance(stmt, ContinueStatement):
            if not self.loop_stack:
                raise RuntimeError("`continue` outside a loop reached codegen")
            self._emit_loop_exit_pops(stmt.span)
            self.emit(Op.JUMP, self.loop_stack[-1][1], stmt.span)
            return
        if isinstance(stmt, ReturnStatement):
            self.compile_expression(stmt.value)
            self.emit(Op.RETURN, span=stmt.span)
            return
        if isinstance(stmt, ThrowStatement):
            self.compile_expression(stmt.value)
            self.emit(Op.THROW, span=stmt.span)
            return
        if isinstance(stmt, TryCatchStatement):
            handler_index = self.emit(Op.SETUP_TRY, None, stmt.span)
            self.try_depth += 1
            try:
                self.compile_block(stmt.try_block)
            finally:
                self.try_depth -= 1
            self.emit(Op.POP_TRY, span=stmt.span)
            end_jump = self.emit(Op.JUMP, None, stmt.span)
            catch_start = len(self.instructions)
            self.catch_depth += 1
            try:
                self.emit(Op.DECLARE_NAME, stmt.catch_name.name, stmt.catch_name.span)
                self.compile_block(stmt.catch_block)
            finally:
                self.catch_depth -= 1
            catch_end = len(self.instructions)
            self.emit(Op.END_CATCH, span=stmt.span)
            after_catch = len(self.instructions)
            self.patch(end_jump, after_catch)
            self.patch(handler_index, (catch_start, catch_end))
            return
        if isinstance(stmt, ExpressionStatement):
            self.compile_expression(stmt.expression)
            self.emit(Op.POP, span=stmt.span)
            return
        if isinstance(stmt, PrintStatement):
            for value in stmt.values:
                self.compile_expression(value)
            if len(stmt.values) > 1:
                self.emit(Op.JOIN_PRINT, len(stmt.values), span=stmt.span)
            self.emit(Op.PRINT, span=stmt.span)
            return
        if isinstance(stmt, IfStatement):
            self.compile_expression(stmt.condition)
            jump_to_else = self.emit(Op.JUMP_IF_FALSE, None, stmt.condition.span)
            self.compile_block(stmt.then_branch)
            if stmt.else_branch is not None:
                jump_to_end = self.emit(Op.JUMP, None, stmt.span)
                self.patch(jump_to_else, len(self.instructions))
                self.compile_block(stmt.else_branch)
                self.patch(jump_to_end, len(self.instructions))
            else:
                self.patch(jump_to_else, len(self.instructions))
            return
        if isinstance(stmt, WhileStatement):
            loop_start = len(self.instructions)
            self.compile_expression(stmt.condition)
            jump_to_end = self.emit(Op.JUMP_IF_FALSE, None, stmt.condition.span)
            breaks: list[int] = []
            self.loop_stack.append((breaks, loop_start, self.try_depth, self.catch_depth))
            try:
                self.compile_block(stmt.body)
            finally:
                self.loop_stack.pop()
            self.emit(Op.JUMP, loop_start, stmt.span)
            loop_end = len(self.instructions)
            self.patch(jump_to_end, loop_end)
            for index in breaks:
                self.patch(index, loop_end)
            return
        if isinstance(stmt, ForStatement):
            self.compile_expression(stmt.iterable)
            self.emit(Op.ITER_START, stmt.name.name, stmt.iterable.span)
            loop_start = len(self.instructions)
            jump_to_end = self.emit(Op.ITER_NEXT, None, stmt.name.span)
            breaks = []
            self.loop_stack.append((breaks, loop_start, self.try_depth, self.catch_depth))
            try:
                self.compile_block(stmt.body)
            finally:
                self.loop_stack.pop()
            self.emit(Op.JUMP, loop_start, stmt.span)
            cleanup = len(self.instructions)
            self.emit(Op.ITER_END, span=stmt.span)
            after_loop = len(self.instructions)
            self.patch(jump_to_end, after_loop)
            for index in breaks:
                self.patch(index, cleanup)
            return
        if isinstance(stmt, BlockStatement):
            self.compile_block(stmt)
            return
        if isinstance(stmt, FunctionDeclaration):
            raise NotImplementedError("Function declarations are only allowed at the top level")
        raise NotImplementedError(f"Codegen not implemented for: {type(stmt).__name__}")

    @staticmethod
    def _index_root(target: IndexExpression) -> Identifier:
        node: Expression = target.collection
        while isinstance(node, IndexExpression):
            node = node.collection
        if isinstance(node, Identifier):
            return node
        return Identifier("<expression>", span=target.span)

    def compile_block(self, block: BlockStatement) -> None:
        for stmt in block.statements:
            self.compile_statement(stmt)

    def compile_expression(self, expr: Expression) -> None:
        self._compile_expression_impl(expr)
        annotation = self.inferred_types.get(id(expr))
        if annotation_has_float(annotation) and (
            annotation_is_float(annotation)
            or isinstance(expr, (IfExpression, ListLiteral, MapLiteral))
        ):
            self.emit(Op.COERCE, annotation, expr.span)

    def _compile_expression_impl(self, expr: Expression) -> None:
        if isinstance(expr, IntegerLiteral):
            self.emit(Op.CONST, expr.value, expr.span)
            return
        if isinstance(expr, FloatLiteral):
            self.emit(Op.CONST, expr.value, expr.span)
            return
        if isinstance(expr, StringLiteral):
            self.emit(Op.CONST, expr.value, expr.span)
            return
        if isinstance(expr, BoolLiteral):
            self.emit(Op.CONST, expr.value, expr.span)
            return
        if isinstance(expr, UnitLiteral):
            self.emit(Op.CONST, UNIT, expr.span)
            return
        if isinstance(expr, BlockExpression):
            for stmt in expr.statements:
                self.compile_statement(stmt)
            self.compile_expression(expr.value)
            return
        if isinstance(expr, IfExpression):
            self.compile_expression(expr.condition)
            jump_to_else = self.emit(Op.JUMP_IF_FALSE, None, expr.condition.span)
            self.compile_expression(expr.then_value)
            jump_to_end = self.emit(Op.JUMP, None, expr.span)
            self.patch(jump_to_else, len(self.instructions))
            self.compile_expression(expr.else_value)
            self.patch(jump_to_end, len(self.instructions))
            return
        if isinstance(expr, Identifier):
            self.emit(Op.LOAD_NAME, expr.name, expr.span)
            return
        if isinstance(expr, ListLiteral):
            for element in expr.elements:
                self.compile_expression(element)
            self.emit(Op.BUILD_LIST, len(expr.elements), expr.span)
            return
        if isinstance(expr, MapLiteral):
            for key, value in expr.entries:
                self.compile_expression(key)
                self.compile_expression(value)
            self.emit(Op.BUILD_MAP, len(expr.entries), expr.span)
            return
        if isinstance(expr, IndexExpression):
            self.compile_expression(expr.collection)
            if expr.is_slice:
                if expr.index is not None:
                    self.compile_expression(expr.index)
                else:
                    self.emit(Op.CONST, 0, expr.span)
                if expr.end is not None:
                    self.compile_expression(expr.end)
                else:
                    self.emit(Op.CONST, None, expr.span)
                self.emit(Op.SLICE, span=expr.span)
                return
            if expr.index is None:
                raise RuntimeError("Index expression has no index or slice end")
            self.compile_expression(expr.index)
            self.emit(Op.INDEX, span=expr.span)
            return
        if isinstance(expr, CallExpression):
            if expr.callee.name == "print":
                if not expr.arguments:
                    raise RuntimeError("`print` expects at least one argument")
                for argument in expr.arguments:
                    self.compile_expression(argument)
                if len(expr.arguments) > 1:
                    self.emit(Op.JOIN_PRINT, len(expr.arguments), expr.span)
                self.emit(Op.PRINT_EXPR, span=expr.span)
                return
            if expr.callee.name == "len":
                if len(expr.arguments) != 1:
                    raise RuntimeError("`len` expects exactly one argument")
                self.compile_expression(expr.arguments[0])
                self.emit(Op.LEN, span=expr.span)
                return
            if expr.callee.name == "get":
                if len(expr.arguments) != 3:
                    raise RuntimeError("`get` expects exactly three arguments")
                for argument in expr.arguments:
                    self.compile_expression(argument)
                self.emit(Op.MAP_GET, span=expr.span)
                return
            if expr.callee.name == "range":
                arg_count = len(expr.arguments)
                if arg_count < 1 or arg_count > 3:
                    raise RuntimeError("`range` expects 1 to 3 arguments")
                for argument in expr.arguments:
                    self.compile_expression(argument)
                self.emit(Op.RANGE, arg_count, span=expr.span)
                return
            if expr.callee.name == "input":
                if len(expr.arguments) != 0:
                    raise RuntimeError("`input` expects exactly zero arguments")
                self.emit(Op.INPUT, span=expr.span)
                return
            if expr.callee.name == "int":
                if len(expr.arguments) != 1:
                    raise RuntimeError("`int` expects exactly one argument")
                self.compile_expression(expr.arguments[0])
                self.emit(Op.TO_INT, span=expr.span)
                return
            if expr.callee.name == "float":
                if len(expr.arguments) != 1:
                    raise RuntimeError("`float` expects exactly one argument")
                self.compile_expression(expr.arguments[0])
                self.emit(Op.TO_FLOAT, span=expr.span)
                return
            if expr.callee.name == "str":
                if len(expr.arguments) != 1:
                    raise RuntimeError("`str` expects exactly one argument")
                self.compile_expression(expr.arguments[0])
                self.emit(Op.TO_STR, span=expr.span)
                return
            if expr.callee.name in ("upper", "lower"):
                if len(expr.arguments) != 1:
                    raise RuntimeError(f"`{expr.callee.name}` expects exactly one argument")
                self.compile_expression(expr.arguments[0])
                self.emit(Op.UPPER if expr.callee.name == "upper" else Op.LOWER, span=expr.span)
                return
            if expr.callee.name == "contains":
                if len(expr.arguments) != 2:
                    raise RuntimeError("`contains` expects exactly two arguments")
                for argument in expr.arguments:
                    self.compile_expression(argument)
                self.emit(Op.CONTAINS, span=expr.span)
                return
            if expr.callee.name == "read_file":
                if len(expr.arguments) != 1:
                    raise RuntimeError("`read_file` expects exactly one argument")
                self.compile_expression(expr.arguments[0])
                self.emit(Op.READ_FILE, span=expr.span)
                return
            if expr.callee.name == "read_csv":
                if len(expr.arguments) != 2:
                    raise RuntimeError("`read_csv` expects exactly two arguments")
                self.compile_expression(expr.arguments[0])
                try:
                    columns = parse_csv_schema(expr.arguments[1])
                except CsvSchemaError as error:
                    raise RuntimeError(error.message) from None
                schema = tuple((column.name, column.type_name) for column in columns)
                self.emit(Op.READ_CSV, schema, expr.span)
                return
            for argument in expr.arguments:
                self.compile_expression(argument)
            self.emit(Op.CALL, (expr.callee.name, len(expr.arguments)), expr.span)
            return
        if isinstance(expr, UnaryExpression):
            self.compile_expression(expr.operand)
            if expr.operator == "-":
                self.emit(Op.NEG, span=expr.span)
                return
            if expr.operator == "!":
                self.emit(Op.NOT, span=expr.span)
                return
            raise NotImplementedError(f"Unary operator not implemented: {expr.operator!r}")
        if isinstance(expr, BinaryExpression):
            if expr.operator == "&&":
                self.compile_and(expr)
                return
            if expr.operator == "||":
                self.compile_or(expr)
                return
            self.compile_expression(expr.left)
            self.compile_expression(expr.right)
            ops = {
                "+": Op.ADD,
                "-": Op.SUB,
                "*": Op.MUL,
                "/": Op.DIV,
                "//": Op.IDIV,
                "%": Op.MOD,
                "==": Op.EQ,
                "!=": Op.NEQ,
                "<": Op.LT,
                "<=": Op.LTE,
                ">": Op.GT,
                ">=": Op.GTE,
            }
            if expr.operator not in ops:
                raise NotImplementedError(f"Binary operator not implemented: {expr.operator!r}")
            self.emit(ops[expr.operator], span=expr.span)
            return
        raise NotImplementedError(f"Expression codegen not implemented: {type(expr).__name__}")

    def compile_and(self, expr: BinaryExpression) -> None:
        self.compile_expression(expr.left)
        self.emit(Op.DUP, span=expr.span)
        jump_to_false = self.emit(Op.JUMP_IF_FALSE, None, expr.span)
        self.emit(Op.POP, span=expr.span)
        self.compile_expression(expr.right)
        self.emit(Op.BOOL, span=expr.span)
        jump_to_end = self.emit(Op.JUMP, None, expr.span)
        self.patch(jump_to_false, len(self.instructions))
        self.emit(Op.POP, span=expr.span)
        self.emit(Op.CONST, False, expr.span)
        self.patch(jump_to_end, len(self.instructions))

    def compile_or(self, expr: BinaryExpression) -> None:
        self.compile_expression(expr.left)
        self.emit(Op.DUP, span=expr.span)
        jump_to_false = self.emit(Op.JUMP_IF_FALSE, None, expr.span)
        self.emit(Op.POP, span=expr.span)
        self.emit(Op.CONST, True, expr.span)
        jump_to_end = self.emit(Op.JUMP, None, expr.span)
        self.patch(jump_to_false, len(self.instructions))
        self.emit(Op.POP, span=expr.span)
        self.compile_expression(expr.right)
        self.emit(Op.BOOL, span=expr.span)
        self.patch(jump_to_end, len(self.instructions))
