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

    def normalize(self):
        # Predicates are atomic, normalization primarily involves ensuring it's a copy.
        # Negation is handled by the negate() method, which normalize() might call on operands.
        return copy.deepcopy(self)

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
        self.wrap = wrap # wrap controls parenthesization in __str__

        if isinstance(expression_input, tuple):
            if len(expression_input) == 3:
                op1, op_str, op2 = expression_input
                if op1 is not None and op2 is None: 
                    if not (hasattr(op1, 'negate') and callable(op1.negate)):
                        raise TypeError("Operand 1 for unary promotion lacks .negate().")
                    self.operant_1 = op1
                    self.operator = None
                    self.operant_2 = None
                    self.is_atomic = True
                elif op1 is None and op2 is not None: 
                    if not (hasattr(op2, 'negate') and callable(op2.negate)):
                        raise TypeError("Operand 2 for unary promotion lacks .negate().")
                    self.operant_1 = op2
                    self.operator = None
                    self.operant_2 = None
                    self.is_atomic = True
                elif op1 is not None and op2 is not None: 
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
                elif op1 is None and op2 is None: 
                    raise ValueError("Binary expression with both operands None is disallowed.")
                else: # Should not be reached
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
            # Parenthesize if operand1 is a non-atomic expression and self.wrap is True
            if isinstance(self.operant_1, expression) and self.operant_1.is_binary and self.wrap :
                 op1_str = f"({op1_str})"
            # Also wrap quantifiers if they are operands and self.wrap is True
            elif isinstance(self.operant_1, (ForAll, Exists)) and self.wrap:
                 op1_str = f"({op1_str})"

            op2_str = str(self.operant_2)
            # Parenthesize if operand2 is a non-atomic expression and self.wrap is True
            if isinstance(self.operant_2, expression) and self.operant_2.is_binary and self.wrap:
                 op2_str = f"({op2_str})"
            elif isinstance(self.operant_2, (ForAll, Exists)) and self.wrap:
                 op2_str = f"({op2_str})"
            
            binary_content = f"{op1_str} {self.operator} {op2_str}"
            # Only add outer parentheses if self.wrap is True
            return f"({binary_content})" if self.wrap else binary_content

        elif self.is_atomic:
            return str(self.operant_1)
        else:
            # This state should ideally not be reachable if constructors are correct.
            return "[Invalid Expression State]"

    def negate(self):
        if self.is_binary:
            # Apply De Morgan's laws and other negation rules
            op1_negated = self.operant_1.negate()
            op2_negated = self.operant_2.negate()
            if self.operator == 'and': 
                return expression((op1_negated, 'or', op2_negated), wrap=self.wrap)
            elif self.operator == 'or': 
                return expression((op1_negated, 'and', op2_negated), wrap=self.wrap)
            elif self.operator == '=>':
                # Negation of (A => B) is (A and ~B)
                op1_copy = copy.deepcopy(self.operant_1) # A remains A
                return expression((op1_copy, 'and', op2_negated), wrap=self.wrap)
            elif self.operator == '<=>':
                # Negation of (A <=> B) is (A and ~B) or (~A and B), or A ^ B
                # Using (A and ~B) or (~A and B) for clarity
                op1_copy = copy.deepcopy(self.operant_1)
                op2_copy = copy.deepcopy(self.operant_2)
                left_expr = expression((op1_copy, 'and', op2_negated), wrap=True) # (A and ~B)
                right_expr = expression((op1_negated, 'and', op2_copy), wrap=True) # (~A and B)
                return expression((left_expr, 'or', right_expr), wrap=self.wrap)
            elif self.operator == '^': # XOR
                # Negation of (A ^ B) is (A and B) or (~A and ~B), which is A <=> B
                op1_copy = copy.deepcopy(self.operant_1)
                op2_copy = copy.deepcopy(self.operant_2)
                left_expr = expression((op1_copy, 'and', op2_copy), wrap=True) # (A and B)
                right_expr = expression((op1_negated, 'and', op2_negated), wrap=True) # (~A and ~B)
                return expression((left_expr, 'or', right_expr), wrap=self.wrap)
            else:
                # Should not happen if operator is validated in __init__
                raise ValueError(f"Negation rule undefined for operator: {self.operator}")
        elif self.is_atomic:
            # Negate the atomic formula (e.g., a predicate or a quantified expression)
            return self.operant_1.negate()
        else:
            raise RuntimeError("Cannot negate expression in invalid state.")

    def normalize(self):
        # Converts the expression to Negation Normal Form (NNF)
        # 1. Eliminates =>, <=>, ^
        # 2. Pushes negations inward using negate()
        if self.is_atomic:
            # If operant_1 has its own normalize method (e.g., it's an expression, ForAll, Exists)
            if hasattr(self.operant_1, 'normalize') and callable(self.operant_1.normalize):
                 normalized_operant_1 = self.operant_1.normalize()
                 # Re-wrap as an atomic expression, respecting original wrap intent for this level
                 return expression(normalized_operant_1, wrap=self.wrap)
            else: # It's a base type like predicate (which has a basic normalize)
                return expression(copy.deepcopy(self.operant_1), wrap=self.wrap)

        elif self.is_binary:
            if self.operator == '=>':
                # A => B  is equivalent to ~A or B
                negated_op1 = self.operant_1.negate() # This pushes negation into op1
                # The new expression is (~A or B). We then normalize this structure.
                # Pass original wrap status to the new expression
                new_expr = expression((negated_op1, 'or', copy.deepcopy(self.operant_2)), wrap=self.wrap)
                return new_expr.normalize() # Recursively normalize

            elif self.operator == '<=>':
                # A <=> B is equivalent to (A => B) and (B => A)
                # which is (~A or B) and (~B or A)
                # Build these intermediate expressions and then normalize the final structure.
                
                # (~A or B)
                term1_op1_neg = self.operant_1.negate()
                term1 = expression((term1_op1_neg, 'or', copy.deepcopy(self.operant_2)), wrap=True)
                
                # (~B or A)
                term2_op2_neg = self.operant_2.negate() # Corrected from term2_op1_neg
                term2 = expression((term2_op2_neg, 'or', copy.deepcopy(self.operant_1)), wrap=True)
                
                new_expr = expression((term1, 'and', term2), wrap=self.wrap)
                return new_expr.normalize()

            elif self.operator == '^': # XOR
                # A ^ B is equivalent to (A and ~B) or (~A and B)
                
                # (A and ~B)
                term1_op2_neg = self.operant_2.negate()
                term1 = expression((copy.deepcopy(self.operant_1), 'and', term1_op2_neg), wrap=True)

                # (~A and B)
                term2_op1_neg = self.operant_1.negate()
                term2 = expression((term2_op1_neg, 'and', copy.deepcopy(self.operant_2)), wrap=True)
                
                new_expr = expression((term1, 'or', term2), wrap=self.wrap)
                return new_expr.normalize()

            elif self.operator in ['and', 'or']:
                # For 'and' and 'or', normalize the operands.
                # The negate() calls within normalization of =>, <=>, ^ will handle DeMorgan's
                norm_op1 = self.operant_1.normalize()
                norm_op2 = self.operant_2.normalize()
                return expression((norm_op1, self.operator, norm_op2), wrap=self.wrap)
            else:
                # This case should ideally not be reached if operators are validated.
                raise ValueError(f"Normalization rule undefined for operator: {self.operator}")
        else:
            raise RuntimeError("Expression in invalid state for normalization.")


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
        else: # Invalid state
            return False

    def __hash__(self):
        if self.is_binary:
            return hash(('binary', self.operator, self.operant_1, self.operant_2))
        elif self.is_atomic:
            return hash(('atomic', self.operant_1))
        else:
            # Ensure all attributes are hashable and consistently ordered for invalid state
            # This might be fragile if new unhashable attributes are added without updating.
            sorted_vars = tuple(sorted(vars(self).items(), key=lambda item: str(item[0])))
            return hash(('invalid_expression_state', sorted_vars))


    def __getnewargs_ex__(self):
        """
        Provides arguments for __new__ to support deepcopy and pickle.
        Returns ((expression_input_arg, wrap_arg), {kwargs_for_new}).
        """
        if self.is_atomic:
            expression_input_val = self.operant_1
        elif self.is_binary:
            expression_input_val = (self.operant_1, self.operator, self.operant_2)
        else:
            # This case should ideally not be reached if the object is valid.
            raise RuntimeError("Expression is in an invalid state (neither atomic nor binary) and cannot be deepcopied.")
        return (expression_input_val, self.wrap), {}


class ForAll:
    # Represents a universally quantified formula.
    def __init__(self, variable_names, formula):
        if not isinstance(variable_names, list) or not all(isinstance(v, str) for v in variable_names):
            raise TypeError("Variable names must be a list of strings.")
        if not variable_names:
            raise ValueError("Quantifier needs at least one variable.")
        # Ensure the formula part has a negate method, if it's not None
        if formula is not None and not (hasattr(formula, 'negate') and callable(formula.negate)):
            raise TypeError("Quantified formula lacks .negate().")
        self.variables = variable_names
        self.formula = formula # This can be an expression, predicate, or another quantifier

    def __str__(self):
        vars_str = ", ".join(self.variables)
        formula_str = str(self.formula) if self.formula is not None else "(Phi)"
        # If formula is a binary expression, wrap it in parentheses for clarity.
        if isinstance(self.formula, expression) and self.formula.is_binary : # and self.formula.wrap:
             return f"all({vars_str})({formula_str})" # Rely on expression's __str__ for its own wrapping
        return f"all({vars_str}){formula_str}"


    def negate(self):
        # Negation of all(vars) F is exists(vars) ~F
        negated_formula = self.formula.negate() if self.formula is not None else None
        return Exists(copy.deepcopy(self.variables), negated_formula)

    def normalize(self):
        # Normalizes the quantified formula.
        # The quantifier itself (all vs exists) is handled by negation rules if a negation is outside.
        normalized_formula = self.formula.normalize() if self.formula is not None else None
        return ForAll(copy.deepcopy(self.variables), normalized_formula)

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
        formula_str = str(self.formula) if self.formula is not None else "(Phi)"
        if isinstance(self.formula, expression) and self.formula.is_binary : # and self.formula.wrap:
             return f"exists({vars_str})({formula_str})"
        return f"exists({vars_str}){formula_str}"


    def negate(self):
        # Negation of exists(vars) F is all(vars) ~F
        negated_formula = self.formula.negate() if self.formula is not None else None
        return ForAll(copy.deepcopy(self.variables), negated_formula)

    def normalize(self):
        normalized_formula = self.formula.normalize() if self.formula is not None else None
        return Exists(copy.deepcopy(self.variables), normalized_formula)

    def __eq__(self, other):
        if not isinstance(other, Exists):
            return NotImplemented
        return self.variables == other.variables and self.formula == other.formula

    def __hash__(self):
        return hash(('exists', tuple(self.variables), self.formula))