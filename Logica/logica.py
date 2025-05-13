import copy

class predicate:
    # Represents a logical predicate or a set of constants.
    def __init__(self, first_arg, second_arg=None):
        if isinstance(first_arg, str) and isinstance(second_arg, list):
            self.predicate = first_arg
            self.args = [str(arg) for arg in second_arg]
            self.neg = False
            self._is_constant_set = False
        elif isinstance(first_arg, list) and second_arg is None:
            if not first_arg:
                raise ValueError("Constant list cannot be empty.")
            self.predicate = None
            self.args = sorted([str(arg) for arg in first_arg])
            self.neg = False
            self._is_constant_set = True
        else:
            raise TypeError("Initialize with (name: str, args: list) or (constants: list)")

    def __str__(self):
        if self._is_constant_set:
            if len(self.args) == 1:
                return self.args[0]
            else:
                args_str = ", ".join(sorted(self.args))
                return f"{{{args_str}}}"
        else:
            prefix = "~" if self.neg else ""
            args_str = ", ".join(self.args)
            return f"{prefix}{self.predicate}({args_str})"

    def negate(self):
        if self._is_constant_set:
            raise TypeError("Cannot negate a constant set.")
        new_pred = copy.deepcopy(self)
        new_pred.neg = not self.neg
        return new_pred

    def __eq__(self, other):
        if not isinstance(other, predicate):
            return NotImplemented
        if self._is_constant_set != other._is_constant_set:
            return False
        if self._is_constant_set:
            return self.args == other.args
        else:
            return self.predicate == other.predicate and \
                   self.args == other.args and \
                   self.neg == other.neg

    def __hash__(self):
        if self._is_constant_set:
            return hash((self._is_constant_set, tuple(self.args)))
        else:
            return hash((self._is_constant_set, self.predicate, tuple(self.args), self.neg))

FormulaType = object 
class expression: pass
class ForAll: pass
class Exists: pass

class expression:
    # Represents a logical expression. Returns None if initialized with None.
    def __new__(cls, expression_input, wrap=False):
        if expression_input is None:
            return None
        instance = super().__new__(cls)
        return instance

    def __init__(self, expression_input, wrap=False):
        self.is_binary = False
        self.is_atomic = False
        self.wrap = wrap

        if isinstance(expression_input, tuple):
            if len(expression_input) == 3:
                op1, op_str, op2 = expression_input
                if op1 is not None and op2 is None: # (formula, op, None) -> atomic(formula)
                    if not (hasattr(op1, 'negate') and callable(op1.negate)):
                        raise TypeError("Operand 1 for unary promotion lacks .negate().")
                    self.operant_1 = op1
                    self.operator = None
                    self.operant_2 = None
                    self.is_atomic = True
                elif op1 is None and op2 is not None: # (None, op, formula) -> atomic(formula)
                    if not (hasattr(op2, 'negate') and callable(op2.negate)):
                        raise TypeError("Operand 2 for unary promotion lacks .negate().")
                    self.operant_1 = op2
                    self.operator = None
                    self.operant_2 = None
                    self.is_atomic = True
                elif op1 is not None and op2 is not None: # (formula1, op, formula2) -> binary
                    if not (hasattr(op1, 'negate') and callable(op1.negate)):
                        raise TypeError("Operand 1 lacks .negate().")
                    if not (hasattr(op2, 'negate') and callable(op2.negate)):
                        raise TypeError("Operand 2 lacks .negate().")
                    if op_str not in ['and', 'or', '=>', '<=>', '^']:
                        raise ValueError(f"Unknown binary operator: {op_str}.")
                    self.operant_1 = op1
                    self.operator = op_str
                    self.operant_2 = op2
                    self.is_binary = True
                elif op1 is None and op2 is None: # (None, op, None) -> invalid
                    raise ValueError("Binary expression with both operands None is disallowed.")
                else:
                     raise RuntimeError("Internal logic error in tuple-based expression init.")
            else:
                raise ValueError("Expression tuple must have 3 elements.")
        elif hasattr(expression_input, 'negate') and callable(expression_input.negate): # Atomic
            self.operant_1 = expression_input
            self.operator = None
            self.operant_2 = None
            self.is_atomic = True
        else:
            raise TypeError("Expression input must be a tuple or a formula with .negate().")

    def __str__(self):
        if self.is_binary:
            op1_str = str(self.operant_1)
            if isinstance(self.operant_1, expression) and not self.operant_1.is_atomic:
                if self.wrap: op1_str = f"({op1_str})"
            elif isinstance(self.operant_1, (ForAll, Exists)):
                if self.wrap: op1_str = f"({op1_str})"
            op2_str = str(self.operant_2)
            if isinstance(self.operant_2, expression) and not self.operant_2.is_atomic:
                if self.wrap: op2_str = f"({op2_str})"
            elif isinstance(self.operant_2, (ForAll, Exists)):
                if self.wrap: op2_str = f"({op2_str})"
            binary_content = f"({op1_str}) {self.operator} ({op2_str})" if self.wrap else f"{op1_str} {self.operator} {op2_str}"
            return f"({binary_content})" if self.wrap else binary_content
        elif self.is_atomic:
            return str(self.operant_1)
        else:
            return "[Invalid Expression State]"

    def negate(self):
        if self.is_binary:
            op1_negated = self.operant_1.negate()
            op2_negated = self.operant_2.negate()
            if self.operator == 'and': return expression((op1_negated, 'or', op2_negated), wrap=self.wrap)
            elif self.operator == 'or': return expression((op1_negated, 'and', op2_negated), wrap=self.wrap)
            elif self.operator == '=>':
                op1_copy = copy.deepcopy(self.operant_1)
                return expression((op1_copy, 'and', op2_negated), wrap=self.wrap)
            elif self.operator == '<=>':
                op1_copy = copy.deepcopy(self.operant_1)
                op2_copy = copy.deepcopy(self.operant_2)
                left_expr = expression((op1_copy, 'and', op2_negated), wrap=True)
                right_expr = expression((op1_negated, 'and', op2_copy), wrap=True)
                return expression((left_expr, 'or', right_expr), wrap=self.wrap)
            elif self.operator == '^':
                op1_copy = copy.deepcopy(self.operant_1)
                op2_copy = copy.deepcopy(self.operant_2)
                left_expr = expression((op1_copy, 'and', op2_copy), wrap=True)
                right_expr = expression((op1_negated, 'and', op2_negated), wrap=True)
                return expression((left_expr, 'or', right_expr), wrap=self.wrap)
            else:
                raise ValueError(f"Negation rule undefined for operator: {self.operator}")
        elif self.is_atomic:
            return self.operant_1.negate()
        else:
            raise RuntimeError("Cannot negate expression in invalid state.")

    def __eq__(self, other):
        if not isinstance(other, expression):
            return NotImplemented
        if self.is_binary != other.is_binary or self.is_atomic != other.is_atomic:
            return False
        if self.is_binary:
            return self.operator == other.operator and \
                   self.operant_1 == other.operant_1 and \
                   self.operant_2 == other.operant_2
        elif self.is_atomic:
            return self.operant_1 == other.operant_1
        else:
            return False

    def __hash__(self):
        if self.is_binary:
            return hash(('binary', self.operator, self.operant_1, self.operant_2))
        elif self.is_atomic:
            return hash(('atomic', self.operant_1))
        else:
            return hash(('invalid_expression_state', tuple(vars(self).items())))

class ForAll:
    # Represents a universally quantified formula.
    def __init__(self, variable_names, formula):
        if not isinstance(variable_names, list) or not all(isinstance(v, str) for v in variable_names):
            raise TypeError("Variable names must be a list of strings.")
        if not variable_names:
            raise ValueError("Quantifier needs at least one variable.")
        if formula is not None and not (hasattr(formula, 'negate') and callable(formula.negate)):
            raise TypeError("Quantified formula lacks .negate().")
        self.variables = variable_names
        self.formula = formula

    def __str__(self):
        vars_str = ", ".join(self.variables)
        formula_str = str(self.formula) if self.formula is not None else "[None]"
        return f"all({vars_str})({formula_str})"

    def negate(self):
        negated_formula = self.formula.negate() if self.formula is not None else None
        return Exists(copy.deepcopy(self.variables), negated_formula)

    def __eq__(self, other):
        if not isinstance(other, ForAll):
            return NotImplemented
        return self.variables == other.variables and self.formula == other.formula

    def __hash__(self):
        return hash(('all', tuple(self.variables), self.formula))

class Exists:
    # Represents an existentially quantified formula.
    def __init__(self, variable_names, formula):
        if not isinstance(variable_names, list) or not all(isinstance(v, str) for v in variable_names):
            raise TypeError("Variable names must be a list of strings.")
        if not variable_names:
            raise ValueError("Quantifier needs at least one variable.")
        if formula is not None and not (hasattr(formula, 'negate') and callable(formula.negate)):
            raise TypeError("Quantified formula lacks .negate().")
        self.variables = variable_names
        self.formula = formula

    def __str__(self):
        vars_str = ", ".join(self.variables)
        formula_str = str(self.formula) if self.formula is not None else "[None]"
        return f"exists({vars_str})({formula_str})"

    def negate(self):
        negated_formula = self.formula.negate() if self.formula is not None else None
        return ForAll(copy.deepcopy(self.variables), negated_formula)

    def __eq__(self, other):
        if not isinstance(other, Exists):
            return NotImplemented
        return self.variables == other.variables and self.formula == other.formula

    def __hash__(self):
        return hash(('exists', tuple(self.variables), self.formula))
