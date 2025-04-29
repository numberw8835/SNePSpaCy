import copy

# --- Predicate Class ---
class predicate:
    """
    Represents a logical predicate with a name and string arguments.
    Can be negated.
    """
    def __init__(self, predicate_name, args):
        # The name of the predicate (e.g., "P", "Likes").
        self.predicate = predicate_name
        # Arguments are expected to be strings.
        self.args = [str(arg) for arg in args]
        # Flag indicating if the predicate is negated (starts as False).
        self.neg = False

    def __str__(self):
        """
        Returns the string representation of the predicate.
        Example: "P(x)" or "~Likes(Alice, y)".
        """
        prefix = "~" if self.neg else ""
        # Join string arguments
        args_str = ", ".join(self.args)
        return f"{prefix}{self.predicate}({args_str})"

    def negate(self):
        """
        Returns a NEW predicate object representing the logical negation.
        """
        # Create a new predicate instance
        new_pred = predicate(self.predicate, self.args)
        # Toggle the negation flag
        new_pred.neg = not self.neg
        return new_pred

    def __eq__(self, other):
        """ Checks for structural equality. """
        if not isinstance(other, predicate):
            return NotImplemented
        return self.predicate == other.predicate and \
               self.args == other.args and \
               self.neg == other.neg

    def __hash__(self):
        """ Basic hash implementation. """
        # Args list needs to be a tuple for hashing
        return hash((self.predicate, tuple(self.args), self.neg))


# --- Expression Class (Binary Operators) ---
class expression:
    """
    Represents a logical expression combining two formulas with a binary operator.
    Operands can be predicates, expressions, or quantified formulas.
    Negation applies logical rules structurally.
    Uses 'and', 'or', '=>', '<=>', '^' as operators.
    """
    def __init__(self, expression_tuple):
        """
        Initializes the expression from a tuple.
        Args:
            expression_tuple (tuple): A tuple of the form (operand1, operator, operand2).
                                     Operands should have a 'negate' method.
                                     Operator is a string (e.g., "=>", "and", "or").
        """
        if len(expression_tuple) != 3:
             raise ValueError("Expression tuple must have 3 elements (operand1, operator, operand2)")
        op1, op, op2 = expression_tuple

        # Basic check if operands seem valid (have negate method - duck typing)
        if not (hasattr(op1, 'negate') and callable(op1.negate)):
             raise TypeError(f"Operand 1 '{op1}' does not seem to be a valid formula (missing negate method).")
        if not (hasattr(op2, 'negate') and callable(op2.negate)):
             raise TypeError(f"Operand 2 '{op2}' does not seem to be a valid formula (missing negate method).")
        # Check operator validity
        if op not in ['and', 'or', '=>', '<=>', '^']:
            raise ValueError(f"Unknown operator: {op}")

        self.operant_1 = op1
        self.operator = op
        self.operant_2 = op2

    def __str__(self):
        """
        Returns the string representation of the logical expression.
        Handles nested structures by adding parentheses.
        """
        # Convert operand 1 to string, add parentheses if complex
        op1_str = str(self.operant_1)
        # Check types that need parentheses
        if isinstance(self.operant_1, (expression, ForAll, Exists)):
            op1_str = f"({op1_str})"

        # Convert operand 2 to string, add parentheses if complex
        op2_str = str(self.operant_2)
        if isinstance(self.operant_2, (expression, ForAll, Exists)):
            op2_str = f"({op2_str})"

        # Combine parts
        return f"{op1_str} {self.operator} {op2_str}"

    def negate(self):
        """
        Returns a NEW expression object representing the logical negation,
        applying standard rules structurally.
        """
        op1_negated = self.operant_1.negate()
        op2_negated = self.operant_2.negate()

        if self.operator == 'and': # ~(A and B) <=> ~A or ~B
            return expression((op1_negated, 'or', op2_negated))
        elif self.operator == 'or': # ~(A or B) <=> ~A and ~B
            return expression((op1_negated, 'and', op2_negated))
        elif self.operator == '=>': # ~(A => B) <=> A and ~B
            # Note: Operand 1 is NOT negated here
            return expression((self.operant_1, 'and', op2_negated))
        elif self.operator == '<=>': # ~(A <=> B) <=> (A and ~B) or (B and ~A)
            left_expr = expression((self.operant_1, 'and', op2_negated))
            right_expr = expression((self.operant_2, 'and', op1_negated))
            return expression((left_expr, 'or', right_expr))
        elif self.operator == '^': # ~(A ^ B) <=> (A and B) or (~A and ~B)
            left_expr = expression((self.operant_1, 'and', self.operant_2))
            right_expr = expression((op1_negated, 'and', op2_negated))
            return expression((left_expr, 'or', right_expr))
        else:
            # Should not be reached due to __init__ check
            raise ValueError(f"Negation rule not defined for operator: {self.operator}")

    def __eq__(self, other):
        """ Checks for structural equality. """
        if not isinstance(other, expression):
            return NotImplemented
        return self.operator == other.operator and \
               self.operant_1 == other.operant_1 and \
               self.operant_2 == other.operant_2

    def __hash__(self):
        """ Basic hash implementation. """
        return hash((self.operator, self.operant_1, self.operant_2))


# --- Quantifier Classes ---

class ForAll:
    """ Represents a universally quantified formula (∀ variables... formula). """
    def __init__(self, variable_names, formula):
        # Ensure variable_names is a list of strings
        if not isinstance(variable_names, list) or not all(isinstance(v, str) for v in variable_names):
            raise TypeError("Quantified variable names must be a list of strings.")
        if not variable_names:
             raise ValueError("Quantifier must have at least one variable.")
        # Check if formula looks valid (duck typing)
        if not (hasattr(formula, 'negate') and callable(formula.negate)):
             raise TypeError(f"Quantified formula '{formula}' does not seem to be valid (missing negate method).")

        self.variables = variable_names # Store list of variable names
        self.formula = formula

    def __str__(self):
        # Use 'forall' keyword for representation
        vars_str = ", ".join(self.variables)
        return f"all({vars_str})({str(self.formula)})"

    def negate(self):
        """ Negation rule: ~forall x,y P(x,y) <=> exists x,y ~P(x,y) """
        # Returns an Exists object with the same variable list and negated formula
        return Exists(self.variables, self.formula.negate())

    def __eq__(self, other):
        """ Checks for structural equality. """
        if not isinstance(other, ForAll):
            return NotImplemented
        # Requires same list of variable names and structurally equal formula
        # Order matters in the list comparison.
        return self.variables == other.variables and self.formula == other.formula

    def __hash__(self):
        """ Basic hash implementation. """
        # Convert variable list to tuple for hashing
        return hash(('all', tuple(self.variables), self.formula))


class Exists:
    """ Represents an existentially quantified formula (∃ variables... formula). """
    def __init__(self, variable_names, formula):
         # Ensure variable_names is a list of strings
        if not isinstance(variable_names, list) or not all(isinstance(v, str) for v in variable_names):
            raise TypeError("Quantified variable names must be a list of strings.")
        if not variable_names:
             raise ValueError("Quantifier must have at least one variable.")
        # Check if formula looks valid (duck typing)
        if not (hasattr(formula, 'negate') and callable(formula.negate)):
             raise TypeError(f"Quantified formula '{formula}' does not seem to be valid (missing negate method).")

        self.variables = variable_names # Store list of variable names
        self.formula = formula

    def __str__(self):
         # Use 'exists' keyword for representation
        vars_str = ", ".join(self.variables)
        return f"exists({vars_str})({str(self.formula)})"

    def negate(self):
        """ Negation rule: ~exists x,y P(x,y) <=> forall x,y ~P(x,y) """
        # Returns a ForAll object with the same variable list and negated formula
        return ForAll(self.variables, self.formula.negate())

    def __eq__(self, other):
        """ Checks for structural equality. """
        if not isinstance(other, Exists):
            return NotImplemented
        # Requires same list of variable names and structurally equal formula
        # Order matters in the list comparison.
        return self.variables == other.variables and self.formula == other.formula

    def __hash__(self):
        """ Basic hash implementation. """
         # Convert variable list to tuple for hashing
        return hash(('exists', tuple(self.variables), self.formula))