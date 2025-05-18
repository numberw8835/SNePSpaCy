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
        return f"all({vars_str}){formula_str}"

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
        return f"exists({vars_str}){formula_str}"

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

def coordinate(input: list, operator: str='and', wrap=False) -> expression:
    """Returns a coordination of the given input"""
    if not input:
        return None
    elif len(input) == 1:
        return expression(input[0])
    else:
        result = expression(input[0])
        for predicate in input[1:]:
            result = expression((result, operator, predicate), wrap=wrap)
        return result

def intentionalize(formula: expression) -> expression:
    """Transforms the universal intention of the expression"""
    antecedent, consequent, other = [], [], []
    vars = []
    for segment in formula.segments:
        if isinstance(segment, ForAll) and segment.formula.operator == '=>':
            vars.extend(segment.variables)
            antecedent.append(segment.formula.operant_1)
            consequent.append(segment.formula.operant_2)
        elif isinstance(segment, ForAll):
            other.append(segment)
        else:
            consequent.append(segment)
    
    specification = expression((
        coordinate(antecedent),
        "=>",
        coordinate(consequent)
    ))
    
    result = expression((
        ForAll(vars, specification),
        "and",
        coordinate(other)
    ))
    
    return result

# Example:::
# --- Atomic Predicates ---
play_e = predicate("Play", ["e"])
agent_e_bob = predicate("agent", ["e", "bob"])
member_x_beta = predicate("member", ["x", "beta"]) # Using "beta" for β
boy_x = predicate("boy", ["x"])
agent_e_x = predicate("agent", ["e", "x"])
student_s = predicate("student", ["s"])
agent_e_s = predicate("agent", ["e", "s"])
volleyball_v = predicate("Volleyball", ["v"])
object_e_v = predicate("object", ["e", "v"])

# --- Quantified Expressions ---
# ∀x (member(x, β) ⇔ boy(x))
expr_member_iff_boy = expression((member_x_beta, '<=>', boy_x))
q1_forall_member_boy = ForAll(["x"], expr_member_iff_boy)

# ∀x (member(x, β) → agent(e,x))
expr_member_implies_agent = expression((member_x_beta, '=>', agent_e_x))
q2_forall_member_agent = ForAll(["x"], expr_member_implies_agent)

# ∀s (student(s) → agent(e,s))
expr_student_implies_agent = expression((student_s, '=>', agent_e_s))
q3_forall_student_agent = ForAll(["s"], expr_student_implies_agent)

# --- Build the Full Conjunction ---
# The expression class builds a tree. The default wrap=False for intermediate
# 'and' expressions is fine for the logical structure. The __str__ method
# will render it as a flat conjunction.

# Play(e) ∧ agent(e,bob)
conj1 = expression((play_e, 'and', agent_e_bob))
# conj1 ∧ ∀x (member(x, β) ⇔ boy(x))
conj2 = expression((conj1, 'and', q1_forall_member_boy))
# conj2 ∧ ∀x (member(x, β) → agent(e,x))
conj3 = expression((conj2, 'and', q2_forall_member_agent))
# conj3 ∧ ∀s (student(s) → agent(e,s))
conj4 = expression((conj3, 'and', q3_forall_student_agent))
# conj4 ∧ Volleyball(v)
conj5 = expression((conj4, 'and', volleyball_v))
# conj5 ∧ object(e,v)
final_fol_expression = expression((conj5, 'and', object_e_v))

# print(final_fol_expression)

# print(intentionalize(final_fol_expression))