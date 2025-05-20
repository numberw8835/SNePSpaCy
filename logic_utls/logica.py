import copy
from referencing import Specification

class predicate:
    # Represents a logical predicate or a set of constants.
    def __init__(self, first_arg, second_arg=None):
        if isinstance(first_arg, str) and isinstance(second_arg, list):
            self.predicate_name = first_arg
            self.args = [str(arg) for arg in second_arg]
            self.neg = False
            self._is_constant_set = False
        elif isinstance(first_arg, list) and second_arg is None:
            if not first_arg:
                raise ValueError("Constant list cannot be empty.")
            self.predicate_name = None
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
            return f"{prefix}{self.predicate_name}({args_str})"

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
            return self.predicate_name == other.predicate_name and \
                   self.args == other.args and \
                   self.neg == other.neg

    def __hash__(self):
        if self._is_constant_set:
            return hash((self._is_constant_set, tuple(self.args)))
        else:
            return hash((self._is_constant_set, self.predicate_name, tuple(self.args), self.neg))

    def normalize(self):
        return copy.deepcopy(self)

    def _get_all_binary_expressions(self):
        yield from ()

    def _get_all_predicates(self):
        yield self

    def _get_all_quantifiers(self):
        yield from ()

    def _get_all_segments(self):
        yield self


FormulaType = object
class expression: pass
class ForAll: pass
class Exists: pass

class expression:
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
                else:
                    raise RuntimeError("Internal logic error in tuple-based expression init.")
            else:
                raise ValueError("Expression tuple must have 3 elements.")
        elif hasattr(expression_input, 'negate') and callable(expression_input.negate):
            self.operant_1 = expression_input
            self.operator = None
            self.operant_2 = None
            self.is_atomic = True
        else:
            raise TypeError("Expression input must be a tuple or a formula with .negate().")

    def __str__(self):
        if self.is_binary:
            op1_str = str(self.operant_1)
            if isinstance(self.operant_1, expression) and self.operant_1.is_binary and self.wrap :
                 op1_str = f"({op1_str})"
            elif isinstance(self.operant_1, (ForAll, Exists)) and self.wrap:
                 op1_str = f"({op1_str})"

            op2_str = str(self.operant_2)
            if isinstance(self.operant_2, expression) and self.operant_2.is_binary and self.wrap:
                 op2_str = f"({op2_str})"
            elif isinstance(self.operant_2, (ForAll, Exists)) and self.wrap:
                 op2_str = f"({op2_str})"

            binary_content = f"{op1_str} {self.operator} {op2_str}"
            return f"({binary_content})" if self.wrap else binary_content
        elif self.is_atomic:
            return str(self.operant_1)
        else:
            return "[Invalid Expression State]"

    def negate(self):
        if self.is_binary:
            op1_negated = self.operant_1.negate()
            op2_negated = self.operant_2.negate()
            if self.operator == 'and':
                return expression((op1_negated, 'or', op2_negated), wrap=self.wrap)
            elif self.operator == 'or':
                return expression((op1_negated, 'and', op2_negated), wrap=self.wrap)
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

    def normalize(self):
        if self.is_atomic:
            if hasattr(self.operant_1, 'normalize') and callable(self.operant_1.normalize):
                 normalized_operant_1 = self.operant_1.normalize()
                 return expression(normalized_operant_1, wrap=self.wrap)
            else:
                return expression(copy.deepcopy(self.operant_1), wrap=self.wrap)
        elif self.is_binary:
            if self.operator == '=>':
                negated_op1 = self.operant_1.negate()
                new_expr = expression((negated_op1, 'or', copy.deepcopy(self.operant_2)), wrap=self.wrap)
                return new_expr.normalize()
            elif self.operator == '<=>':
                term1_op1_neg = self.operant_1.negate()
                term1 = expression((term1_op1_neg, 'or', copy.deepcopy(self.operant_2)), wrap=True)
                term2_op2_neg = self.operant_2.negate()
                term2 = expression((term2_op2_neg, 'or', copy.deepcopy(self.operant_1)), wrap=True)
                new_expr = expression((term1, 'and', term2), wrap=self.wrap)
                return new_expr.normalize()
            elif self.operator == '^':
                term1_op2_neg = self.operant_2.negate()
                term1 = expression((copy.deepcopy(self.operant_1), 'and', term1_op2_neg), wrap=True)
                term2_op1_neg = self.operant_1.negate()
                term2 = expression((term2_op1_neg, 'and', copy.deepcopy(self.operant_2)), wrap=True)
                new_expr = expression((term1, 'or', term2), wrap=self.wrap)
                return new_expr.normalize()
            elif self.operator in ['and', 'or']:
                norm_op1 = self.operant_1.normalize()
                norm_op2 = self.operant_2.normalize()
                return expression((norm_op1, self.operator, norm_op2), wrap=self.wrap)
            else:
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
        else:
            return False

    def __hash__(self):
        if self.is_binary:
            return hash(('binary', self.operator, self.operant_1, self.operant_2))
        elif self.is_atomic:
            return hash(('atomic', self.operant_1))
        else:
            sorted_vars = tuple(sorted(vars(self).items(), key=lambda item: str(item[0])))
            return hash(('invalid_expression_state', sorted_vars))

    def __getnewargs_ex__(self):
        if self.is_atomic:
            expression_input_val = self.operant_1
        elif self.is_binary:
            expression_input_val = (self.operant_1, self.operator, self.operant_2)
        else:
            raise RuntimeError("Expression is in an invalid state (neither atomic nor binary) and cannot be deepcopied.")
        return (expression_input_val, self.wrap), {}

    def _get_all_binary_expressions(self):
        if self.is_binary:
            yield self

        if self.operant_1 is not None and hasattr(self.operant_1, '_get_all_binary_expressions'):
            yield from self.operant_1._get_all_binary_expressions()

        if self.is_binary and self.operant_2 is not None and hasattr(self.operant_2, '_get_all_binary_expressions'):
            yield from self.operant_2._get_all_binary_expressions()

    def _get_all_predicates(self):
        if self.operant_1 is not None and hasattr(self.operant_1, '_get_all_predicates'):
            yield from self.operant_1._get_all_predicates()

        if self.is_binary and self.operant_2 is not None and hasattr(self.operant_2, '_get_all_predicates'):
            yield from self.operant_2._get_all_predicates()

    def _get_all_quantifiers(self):
        if self.operant_1 is not None and hasattr(self.operant_1, '_get_all_quantifiers'):
            yield from self.operant_1._get_all_quantifiers()

        if self.is_binary and self.operant_2 is not None and hasattr(self.operant_2, '_get_all_quantifiers'):
            yield from self.operant_2._get_all_quantifiers()

    def _get_all_segments(self):
        if self.is_binary and self.operator == 'and':
            if hasattr(self.operant_1, '_get_all_segments'):
                yield from self.operant_1._get_all_segments()
            else: # Should not happen if operant_1 is a valid formula component
                yield self.operant_1

            if hasattr(self.operant_2, '_get_all_segments'):
                yield from self.operant_2._get_all_segments()
            else: # Should not happen if operant_2 is a valid formula component
                yield self.operant_2
        elif self.is_atomic:
             # If the atomic operant itself can have segments (e.g. it's a nested 'and' expression)
            if hasattr(self.operant_1, '_get_all_segments'):
                yield from self.operant_1._get_all_segments()
            else: # It's a simple atomic like a predicate or quantifier
                yield self.operant_1
        else: # Not an 'and' expression, and not atomic (e.g. 'or', '=>', etc.)
            yield self


    @property
    def expressions(self):
        yield from self._get_all_binary_expressions()

    @property
    def predicates(self):
        yield from self._get_all_predicates()

    @property
    def quantifiers(self):
        yield from self._get_all_quantifiers()

    @property
    def segments(self):
        yield from self._get_all_segments()

class ForAll:
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
        if isinstance(self.formula, expression) and self.formula.is_binary :
             return f"all({vars_str})({formula_str})"
        return f"all({vars_str})({formula_str})"

    def negate(self):
        negated_formula = self.formula.negate() if self.formula is not None else None
        return Exists(copy.deepcopy(self.variables), negated_formula)

    def normalize(self):
        normalized_formula = self.formula.normalize() if self.formula is not None else None
        return ForAll(copy.deepcopy(self.variables), normalized_formula)

    def __eq__(self, other):
        if not isinstance(other, ForAll):
            return NotImplemented
        return self.variables == other.variables and self.formula == other.formula

    def __hash__(self):
        return hash(('all', tuple(self.variables), self.formula))

    def _get_all_binary_expressions(self):
        if self.formula is not None and hasattr(self.formula, '_get_all_binary_expressions'):
            yield from self.formula._get_all_binary_expressions()

    def _get_all_predicates(self):
        if self.formula is not None and hasattr(self.formula, '_get_all_predicates'):
            yield from self.formula._get_all_predicates()

    def _get_all_quantifiers(self):
        yield self
        if self.formula is not None and hasattr(self.formula, '_get_all_quantifiers'):
            yield from self.formula._get_all_quantifiers()

    def _get_all_segments(self):
        yield self

    def skolemize_arg(self, arg_to_functionalize: str, universal_vars_as_params: list[str]):
        """
        Modifies the instance in-place.
        Replaces occurrences of 'arg_to_functionalize' in predicates within the formula
        with 'arg_to_functionalize({var1, var2, ...})'.
        All variables in 'universal_vars_as_params' must be quantified by this ForAll.
        Example: all(s, t)(P(s) => agent(e, s, t)) with skolemize_arg("e", ["s", "t"])
                 becomes all(s, t)(P(s) => agent(e({s,t}), s, t)) within the instance.
        """
        if not isinstance(universal_vars_as_params, list) or \
           not all(isinstance(v, str) for v in universal_vars_as_params):
            raise TypeError("universal_vars_as_params must be a list of strings.")

        if not universal_vars_as_params:
            raise ValueError("universal_vars_as_params cannot be empty.")

        for var_param in universal_vars_as_params:
            if var_param not in self.variables:
                raise ValueError(
                    f"Variable '{var_param}' in universal_vars_as_params is not universally quantified "
                    f"by this ForAll statement. Quantified variables are: {self.variables}"
                )

        # Sort variables for consistent set representation
        param_string = ", ".join(sorted(universal_vars_as_params))

        def modify_recursive(form_component):
            if isinstance(form_component, predicate):
                new_args = []
                modified = False
                for arg_val in form_component.args:
                    if arg_val == arg_to_functionalize:
                        new_args.append(f"{arg_to_functionalize}({{{param_string}}})")
                        modified = True
                    else:
                        new_args.append(arg_val)
                if modified:
                    form_component.args = new_args # Modify predicate args in-place
            elif isinstance(form_component, expression):
                if form_component.operant_1:
                    modify_recursive(form_component.operant_1)
                if form_component.is_binary and form_component.operant_2:
                    modify_recursive(form_component.operant_2)
            elif isinstance(form_component, (ForAll, Exists)):
                # If a nested quantifier needs its own skolemization, it should be handled by a separate call on that instance.
                # This ensures skolemization variables are from the correct scope.
                if form_component.formula:
                    modify_recursive(form_component.formula)

        if self.formula:
            modify_recursive(self.formula) # Modify self.formula in-place

        return None # Convention for methods that modify in-place


class Exists:
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
        if isinstance(self.formula, expression) and self.formula.is_binary :
             return f"exists({vars_str})({formula_str})"
        return f"exists({vars_str})({formula_str})"

    def negate(self):
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

    def _get_all_binary_expressions(self):
        if self.formula is not None and hasattr(self.formula, '_get_all_binary_expressions'):
            yield from self.formula._get_all_binary_expressions()

    def _get_all_predicates(self):
        if self.formula is not None and hasattr(self.formula, '_get_all_predicates'):
            yield from self.formula._get_all_predicates()

    def _get_all_quantifiers(self):
        yield self
        if self.formula is not None and hasattr(self.formula, '_get_all_quantifiers'):
            yield from self.formula._get_all_quantifiers()

    def _get_all_segments(self):
        yield self

def coordinate(input_list: list, operator: str='and', wrap=False) -> expression: # Renamed input to input_list
    """Returns a coordination of the given input_list"""
    if not input_list:
        return None
    elif len(input_list) == 1:
        # Ensure that even single items are wrapped in an expression if they aren't already
        return expression(input_list[0]) if not isinstance(input_list[0], expression) else input_list[0]
    else:
        # Ensure the first item is an expression
        result = expression(input_list[0]) if not isinstance(input_list[0], expression) else input_list[0]
        for item in input_list[1:]: # Renamed predicate to item for generality
            # Ensure the item is an expression before coordinating
            current_expr = expression(item) if not isinstance(item, expression) else item
            result = expression((result, operator, current_expr), wrap=wrap)
        return result

def intentionalize(formula: expression, negation: bool = False) -> expression:
    """Transforms the universal intention of the expression"""
    # Ensure formula.quantifiers is available and produces a list for the check
    all_quantifiers = list(formula.quantifiers) if hasattr(formula, 'quantifiers') and formula.quantifiers is not None else []
    if not all_quantifiers:
        return formula

    antecedent, consequent, other = [], [], []
    vars_collected = [] # Renamed from vars

    # Ensure formula.segments is available and produces a list
    formula_segments = list(formula.segments) if hasattr(formula, 'segments') and formula.segments is not None else []

    for segment in formula_segments:
        if isinstance(segment, ForAll) and \
           hasattr(segment, 'formula') and segment.formula is not None and \
           hasattr(segment.formula, 'operator') and segment.formula.operator == '=>' and \
           hasattr(segment.formula, 'operant_1') and hasattr(segment.formula, 'operant_2'):
            vars_collected.extend(segment.variables)
            antecedent.append(segment.formula.operant_1)
            consequent.append(segment.formula.operant_2)
        elif isinstance(segment, ForAll):
            other.append(segment)
        elif segment is not None : # Ensure segment is not None before appending
            consequent.append(segment)
    
    # Coordinate returns expression or None
    logic = "and" if not negation else "or"
    coord_antecedent = coordinate(antecedent) if antecedent else None
    coord_consequent = coordinate(consequent, logic) if consequent else None
    coord_other = coordinate(other) if other else None

    specification = None
    if coord_antecedent and coord_consequent:
        specification = expression((coord_antecedent, "=>", coord_consequent), wrap=True)
    elif coord_consequent: # If only consequent
        specification = coord_consequent
    elif coord_antecedent: # If only antecedent
        specification = coord_antecedent


    main_forall_expr = None
    # Ensure vars_collected is not empty and specification is not None
    if vars_collected and specification:
        main_forall_expr = ForAll(vars_collected, specification)
    elif specification: # No universal vars collected, but there's a specification
         main_forall_expr = specification


    if main_forall_expr and coord_other:
        # Ensure both are expressions before combining
        main_expr_to_combine = main_forall_expr if isinstance(main_forall_expr, expression) else expression(main_forall_expr)
        other_expr_to_combine = coord_other if isinstance(coord_other, expression) else expression(coord_other)
        return expression((main_expr_to_combine, "and", other_expr_to_combine))
    elif main_forall_expr:
        return main_forall_expr if isinstance(main_forall_expr, expression) else expression(main_forall_expr)
    elif coord_other:
        return coord_other if isinstance(coord_other, expression) else expression(coord_other)

    return formula # Fallback