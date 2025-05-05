import copy

# --- Predicate Class ---
import copy

class predicate:
    """
    Represents either a logical predicate OR a set of constants.

    1. Logical Predicate Mode:
       - Initialized as: predicate('PredicateName', [arg1, arg2, ...])
       - Represents: PredicateName(arg1, arg2, ...)
       - Can be negated using .negate(), toggling the `neg` attribute.
       - Example: predicate('P', ['x']) -> "P(x)"
                  predicate('Likes', ['Alice', 'y']).negate() -> "~Likes(Alice, y)"

    2. Constant Set Mode:
       - Initialized as: predicate([const1, const2, ...])
       - Represents: A single constant or a set of constants.
       - String format:
         - One constant: "const1"
         - Multiple constants: "{const1, const2, ...}"
       - Negation is not applicable in this mode.
       - Example: predicate(['x']) -> "x"
                  predicate(['x', 'y', 'z']) -> "{x, y, z}"

    Attributes:
        predicate (str | None): The name of the predicate (e.g., "P", "Likes")
                                 or None if representing constants.
        args (list[str]): A list of string arguments or constants.
        neg (bool): Flag indicating if the predicate is negated (True means negated).
                    Only applicable in logical predicate mode.
        _is_constant_set (bool): Internal flag; True if in constant set mode.
    """
    def __init__(self, first_arg, second_arg=None):
        """
        Initializes a predicate or a constant set.

        Args:
            first_arg (str | list):
                - If str: The predicate name. `second_arg` must be a list of arguments.
                - If list: A list of constants. `second_arg` must be None.
            second_arg (list | None):
                - If first_arg is str: A list of arguments (will be converted to strings).
                - If first_arg is list: Must be None.

        Raises:
            TypeError: If arguments are not provided in the expected combinations.
            ValueError: If the constant list is empty when initializing in constant set mode.
        """
        if isinstance(first_arg, str) and isinstance(second_arg, list):
            # Standard Predicate Mode
            self.predicate = first_arg
            self.args = [str(arg) for arg in second_arg]
            self.neg = False
            self._is_constant_set = False
        elif isinstance(first_arg, list) and second_arg is None:
            # Constant Set Mode
            if not first_arg:
                raise ValueError("Constant list cannot be empty when initializing a constant set.")
            self.predicate = None # No predicate name for constant sets
            self.args = sorted([str(arg) for arg in first_arg]) # Store constants sorted
            self.neg = False # Negation doesn't apply
            self._is_constant_set = True
        else:
            # Invalid argument combination
            raise TypeError(
                "Initialize with (predicate_name: str, args: list) "
                "or (constants: list)"
            )

    def __str__(self):
        """
        Returns the string representation based on the mode.

        Returns:
            str: The formatted string representation.
        """
        if self._is_constant_set:
            # Constant Set Mode Representation
            if len(self.args) == 1:
                return self.args[0] # Single constant: "x"
            else:
                # Sort args for consistent output like {x, y}
                args_str = ", ".join(sorted(self.args))
                return f"{{{args_str}}}" # Multiple constants: "{x, y}"
        else:
            # Standard Predicate Mode Representation
            prefix = "~" if self.neg else ""
            args_str = ", ".join(self.args)
            return f"{prefix}{self.predicate}({args_str})" # ~Predicate(arg1, arg2)

    def negate(self):
        """
        Returns a NEW predicate object representing the logical negation.
        The original predicate object is unchanged.
        Raises TypeError if called on a constant set.

        Returns:
            predicate: A new predicate object with the negation state flipped.

        Raises:
            TypeError: If the instance represents a constant set.
        """
        if self._is_constant_set:
            raise TypeError("Cannot negate a constant set representation.")

        # Create a deep copy for standard predicates
        new_pred = copy.deepcopy(self)
        # Toggle the negation flag on the new object
        new_pred.neg = not self.neg
        return new_pred

    def __eq__(self, other):
        """
        Checks for structural equality between two predicate objects.
        Considers whether they are predicates or constant sets.

        Args:
            other: The object to compare against.

        Returns:
            bool: True if structurally equal, False otherwise.
            NotImplemented: If 'other' is not a predicate object.
        """
        if not isinstance(other, predicate):
            return NotImplemented

        # Must be the same type (both constant sets or both predicates)
        if self._is_constant_set != other._is_constant_set:
            return False

        if self._is_constant_set:
            # Compare constant sets (order doesn't matter, handled by sorting in __init__)
            return self.args == other.args
        else:
            # Compare standard predicates (name, args order, negation state matter)
            return self.predicate == other.predicate and \
                   self.args == other.args and \
                   self.neg == other.neg

    def __hash__(self):
        """
        Computes a hash value for the object.
        Distinguishes between constant sets and predicates in the hash.

        Returns:
            int: The computed hash value.
        """
        if self._is_constant_set:
            # Hash for constant sets depends only on the (sorted) args tuple
            # Include the type flag (_is_constant_set) in the hash tuple
            return hash((self._is_constant_set, tuple(self.args)))
        else:
            # Hash for predicates depends on type, name, args tuple, and negation
            return hash((self._is_constant_set, self.predicate, tuple(self.args), self.neg))

# --- Forward declarations for type hints ---
# Use typing.Union for more precise type hints if needed
FormulaType = object # Placeholder for predicate, expression, ForAll, Exists
class expression: pass
class ForAll: pass
class Exists: pass


# --- Expression Class (Handles Predicates, Quantifiers, and other Expressions) ---
class expression:
    """
    Represents a logical expression, which can be:
    1. A binary operation combining two formulas (operands) with an operator
       ('and', 'or', '=>', '<=>', '^'). Operands can be predicates,
       quantifiers (ForAll, Exists), or other expressions.
    2. An atomic wrapper around a single predicate, quantifier, or other formula object.

    The `negate()` method applies logical negation rules structurally.

    Attributes:
        operant_1 (FormulaType): The first operand (or the single operand for atomic).
        operator (str | None): The operator ('and', 'or', '=>', '<=>', '^', or None for atomic).
        operant_2 (FormulaType | None): The second operand (for binary) or None.
        is_binary (bool): True if this is a binary operation expression.
        is_atomic (bool): True if this wraps a single formula.
        wrap (bool): Internal flag affecting string representation parentheses.
    """
    def __init__(self, expression_input, wrap=False):
        """
        Initializes the expression based on the input structure.

        Args:
            expression_input: Determines the type of expression:
                - Tuple (operand1, operator, operand2): Creates a binary expression.
                  `operand1` and `operand2` can be predicate, ForAll, Exists,
                  or expression objects.
                  `operator` must be 'and', 'or', '=>', '<=>', or '^'.
                - Any object with a `negate` method: Creates an atomic wrapper.
            wrap (bool): Controls adding parentheses in __str__ for nested expressions.

        Raises:
            ValueError: If the input tuple structure or operator is invalid.
            TypeError: If the input type is not a tuple and does not have a `negate` method.
        """
        # Initialize state flags
        self.is_binary = False
        self.is_atomic = False
        self.wrap = wrap # Store wrap flag

        # Determine structure based on input type and content
        if isinstance(expression_input, tuple):
            # --- Tuple Input: Must be Binary ---
            if len(expression_input) == 3:
                # Binary operation
                op1, op, op2 = expression_input
                # Validate operands (must support negation - duck typing)
                if not (hasattr(op1, 'negate') and callable(op1.negate)):
                    raise TypeError(f"Operand 1 '{op1}' ({type(op1)}) does not seem to be a valid formula (missing negate method).")
                if not (hasattr(op2, 'negate') and callable(op2.negate)):
                    raise TypeError(f"Operand 2 '{op2}' ({type(op2)}) does not seem to be a valid formula (missing negate method).")
                # Validate binary operator
                if op not in ['and', 'or', '=>', '<=>', '^']:
                    raise ValueError(f"Unknown binary operator: {op}. Must be 'and', 'or', '=>', '<=>', or '^'.")

                # Assign attributes for binary expression
                self.operant_1 = op1
                self.operator = op
                self.operant_2 = op2
                self.is_binary = True
            else:
                # Invalid tuple length for binary operation
                raise ValueError("Expression tuple for binary operations must have 3 elements (operand1, operator, operand2).")

        # --- Single Formula Input: Atomic Wrapper ---
        # Check if the input is a valid formula (has a negate method)
        elif hasattr(expression_input, 'negate') and callable(expression_input.negate):
             self.operant_1 = expression_input # Store the formula
             self.operator = None
             self.operant_2 = None
             self.is_atomic = True # Mark as an atomic wrapper

        else:
            # Invalid input type
            raise TypeError(f"Expression input must be a tuple (operand1, operator, operand2) or an object with a 'negate' method. Got: {type(expression_input)}")


    def __str__(self):
        """
        Returns the string representation of the logical expression.
        Adds parentheses around operands where necessary for clarity,
        controlled partly by the 'wrap' flag during initialization.

        Returns:
            str: The formatted string representation.
        """
        if self.is_binary:
            # --- Format Binary Expression ---
            op1_str = str(self.operant_1)
            # Add parentheses if operand 1 is a non-atomic expression or quantifier
            # and the wrap flag suggests it (to avoid excessive parentheses)
            # This logic might need refinement based on desired output format
            if isinstance(self.operant_1, expression) and not self.operant_1.is_atomic:
                 if self.wrap: # Check wrap flag
                     op1_str = f"({op1_str})"
            elif isinstance(self.operant_1, (ForAll, Exists)):
                 if self.wrap: # Check wrap flag
                     op1_str = f"({op1_str})"
             # No else needed, default is no extra parens

            op2_str = str(self.operant_2)
            # Add parentheses if operand 2 is a non-atomic expression or quantifier
            # and the wrap flag suggests it
            # This logic might need refinement based on desired output format
            if isinstance(self.operant_2, expression) and not self.operant_2.is_atomic:
                 if self.wrap: # Check wrap flag
                     op2_str = f"({op2_str})"
            elif isinstance(self.operant_2, (ForAll, Exists)):
                 if self.wrap: # Check wrap flag
                     op2_str = f"({op2_str})"
             # No else needed, default is no extra parens

            return f"{op1_str} {self.operator} {op2_str}" if not self.wrap else f"({op1_str} {self.operator} {op2_str})"

        elif self.is_atomic:
             # --- Format Atomic Wrapper ---
             return str(self.operant_1)

        else:
             # Should not be reachable
             return "[Invalid Expression State]"

    def negate(self):
        """
        Returns a NEW object representing the logical negation of this expression.
        Applies standard logical rules for binary operators or delegates to the
        wrapped formula's `negate` method for atomic wrappers.
        Uses `copy.deepcopy` when necessary to avoid modifying original operands.

        Returns:
            predicate | expression | ForAll | Exists: The negated logical formula.

        Raises:
            ValueError: If a negation rule is not defined for a binary operator.
            RuntimeError: If the expression is in an invalid internal state.
        """
        if self.is_binary:
            # --- Negating a Binary Expression ---
            # Negate operands first
            op1_negated = self.operant_1.negate()
            op2_negated = self.operant_2.negate()

            if self.operator == 'and': # De Morgan: ~(A and B) <=> (~A or ~B)
                # Create a new expression with negated operands and swapped operator
                return expression((op1_negated, 'or', op2_negated), wrap=self.wrap) # Preserve wrap setting
            elif self.operator == 'or': # De Morgan: ~(A or B) <=> (~A and ~B)
                return expression((op1_negated, 'and', op2_negated), wrap=self.wrap)
            elif self.operator == '=>': # Implication Negation: ~(A => B) <=> (A and ~B)
                # Need a copy of the original operand 1
                op1_copy = copy.deepcopy(self.operant_1)
                return expression((op1_copy, 'and', op2_negated), wrap=self.wrap)
            elif self.operator == '<=>': # Biconditional Negation: ~(A <=> B) <=> (A ^ B)
                                         # Expanded: (A and ~B) or (~A and B) - Note: standard expansion is (A and ~B) or (B and ~A)
                op1_copy = copy.deepcopy(self.operant_1)
                op2_copy = copy.deepcopy(self.operant_2)
                # Create the two parts of the expanded XOR
                left_expr = expression((op1_copy, 'and', op2_negated), wrap=True) # Inner expressions usually need wrapping
                right_expr = expression((op1_negated, 'and', op2_copy), wrap=True) # Use op1_negated and op2_copy
                # Combine with 'or'
                return expression((left_expr, 'or', right_expr), wrap=self.wrap) # Outer expression respects original wrap
            elif self.operator == '^': # XOR Negation: ~(A ^ B) <=> (A <=> B)
                                         # Expanded: (A and B) or (~A and ~B)
                op1_copy = copy.deepcopy(self.operant_1)
                op2_copy = copy.deepcopy(self.operant_2)
                # Create the two parts of the expanded biconditional
                left_expr = expression((op1_copy, 'and', op2_copy), wrap=True)
                right_expr = expression((op1_negated, 'and', op2_negated), wrap=True)
                # Combine with 'or'
                return expression((left_expr, 'or', right_expr), wrap=self.wrap)
            else:
                # Should not happen if constructor validation works
                raise ValueError(f"Internal Error: Negation rule not defined for binary operator: {self.operator}")

        elif self.is_atomic:
             # --- Negating an Atomic Wrapper ---
             # Delegate negation to the wrapped formula.
             # The result might be a predicate, quantifier, or another expression.
             return self.operant_1.negate()

        else:
            # Should not happen
            raise RuntimeError("Internal Error: Cannot negate expression in invalid state.")


    def __eq__(self, other):
        """
        Checks for structural equality between this expression and another object.
        Equal if they are of the same type (binary or atomic) and their
        corresponding components (operator, operands) are equal.

        Args:
            other: The object to compare against.

        Returns:
            bool: True if structurally equal, False otherwise.
            NotImplemented: If 'other' is not an expression object.
        """
        if not isinstance(other, expression):
            return NotImplemented

        # Check if the fundamental type (binary, atomic) matches
        if self.is_binary != other.is_binary or \
           self.is_atomic != other.is_atomic:
            return False # Types differ

        # Compare components based on the matched type
        if self.is_binary:
            # Binary: check operator and both operands
            return self.operator == other.operator and \
                   self.operant_1 == other.operant_1 and \
                   self.operant_2 == other.operant_2
        elif self.is_atomic:
             # Atomic: check the wrapped formula
             return self.operant_1 == other.operant_1
        else:
             # Should not happen
             return False

    def __hash__(self):
        """
        Computes a hash value for the expression object.
        Depends on the type (binary, atomic) and components.

        Returns:
            int: The computed hash value.
        """
        if self.is_binary:
            # Hash includes type marker, operator, and operands
            return hash(('binary', self.operator, self.operant_1, self.operant_2))
        elif self.is_atomic:
             # Hash includes type marker and the wrapped formula
             return hash(('atomic', self.operant_1))
        else:
             # Fallback hash for potential invalid state
             return hash(('invalid_expression'))


# --- Quantifier Classes ---

class ForAll:
    """
    Represents a universally quantified formula (∀ variables... formula).
    Example: all(x, y)(P(x) => Q(y))

    Attributes:
        variables (list[str]): The list of universally quantified variable names.
        formula (FormulaType): The formula being quantified (predicate, expression, ForAll, Exists).
    """
    def __init__(self, variable_names, formula):
        """
        Initializes a universally quantified formula.

        Args:
            variable_names (list[str]): A non-empty list of variable names (strings).
            formula (FormulaType): The logical formula being quantified (must have a `negate` method).

        Raises:
            TypeError: If variable_names is not a list of strings, or formula is invalid.
            ValueError: If variable_names list is empty.
        """
        # Validate variable_names
        if not isinstance(variable_names, list) or not all(isinstance(v, str) for v in variable_names):
            raise TypeError("Quantified variable names must be a list of strings.")
        if not variable_names:
             raise ValueError("Quantifier must have at least one variable.")
        # Validate formula (duck typing: needs negate method)
        if not (hasattr(formula, 'negate') and callable(formula.negate)):
             raise TypeError(f"Quantified formula '{formula}' ({type(formula)}) does not seem to be valid (missing negate method).")

        self.variables = variable_names # Store variable names
        self.formula = formula         # Store the quantified formula

    def __str__(self):
        """
        Returns the string representation using 'all'.
        Example: "all(x, y)(P(x) => Q(y))"

        Returns:
            str: The formatted string representation.
        """
        vars_str = ", ".join(self.variables)
        # Format the inner formula, adding parentheses if it's a binary expression
        # or another quantifier to ensure correct scope visually.
        formula_str = str(self.formula)
        # Check if wrapping is needed for clarity
        if isinstance(self.formula, expression) and self.formula.is_binary:
             formula_str = f"{formula_str}"
        elif isinstance(self.formula, (ForAll, Exists)): # Also wrap nested quantifiers for visual clarity
             formula_str = f"{formula_str}"
        # Combine parts: all(vars)(formula)
        return f"all({vars_str})({formula_str})"

    def negate(self):
        """
        Applies the quantifier negation rule: ~∀x P(x) <=> ∃x ~P(x).
        Returns a NEW Exists object with the same variables and the negated formula.

        Returns:
            Exists: The corresponding existentially quantified negated formula.
        """
        # Return an Exists object with copied variables and negated formula
        # The negated formula might be complex, handled by its own negate method.
        return Exists(copy.deepcopy(self.variables), self.formula.negate())

    def __eq__(self, other):
        """
        Checks for structural equality with another object.
        Equal if 'other' is a ForAll with the same variables (order matters)
        and an equal formula.

        Args:
            other: The object to compare against.

        Returns:
            bool: True if structurally equal, False otherwise.
            NotImplemented: If 'other' is not a ForAll object.
        """
        if not isinstance(other, ForAll):
            return NotImplemented
        # Check variables list and the quantified formula
        return self.variables == other.variables and self.formula == other.formula

    def __hash__(self):
        """
        Computes a hash value based on the quantifier type ('all'),
        variables (as a tuple), and the formula.

        Returns:
            int: The computed hash value.
        """
        # Convert variables list to tuple for hashing
        return hash(('all', tuple(self.variables), self.formula))


class Exists:
    """
    Represents an existentially quantified formula (∃ variables... formula).
    Example: exists(z)(R(z) and ~P(z))

    Attributes:
        variables (list[str]): The list of existentially quantified variable names.
        formula (FormulaType): The formula being quantified (predicate, expression, ForAll, Exists).
    """
    def __init__(self, variable_names, formula):
        """
        Initializes an existentially quantified formula.

        Args:
            variable_names (list[str]): A non-empty list of variable names (strings).
            formula (FormulaType): The logical formula being quantified (must have a `negate` method).

        Raises:
            TypeError: If variable_names is not a list of strings, or formula is invalid.
            ValueError: If variable_names list is empty.
        """
         # Validate variable_names
        if not isinstance(variable_names, list) or not all(isinstance(v, str) for v in variable_names):
            raise TypeError("Quantified variable names must be a list of strings.")
        if not variable_names:
             raise ValueError("Quantifier must have at least one variable.")
         # Validate formula (duck typing: needs negate method)
        if not (hasattr(formula, 'negate') and callable(formula.negate)):
             raise TypeError(f"Quantified formula '{formula}' ({type(formula)}) does not seem to be valid (missing negate method).")

        self.variables = variable_names # Store variable names
        self.formula = formula         # Store the quantified formula

    def __str__(self):
        """
        Returns the string representation using 'exists'.
        Example: "exists(z)(R(z) and ~P(z))"

        Returns:
            str: The formatted string representation.
        """
        vars_str = ", ".join(self.variables)
        # Format the inner formula, adding parentheses if it's a binary expression
        # or another quantifier to ensure correct scope visually.
        formula_str = str(self.formula)
        # Check if wrapping is needed for clarity
        if isinstance(self.formula, expression) and self.formula.is_binary:
             formula_str = f"({formula_str})"
        elif isinstance(self.formula, (ForAll, Exists)): # Also wrap nested quantifiers for visual clarity
             formula_str = f"({formula_str})"
        # Combine parts: exists(vars)(formula)
        return f"exists({vars_str})({formula_str})"

    def negate(self):
        """
        Applies the quantifier negation rule: ~∃x P(x) <=> ∀x ~P(x).
        Returns a NEW ForAll object with the same variables and the negated formula.

        Returns:
            ForAll: The corresponding universally quantified negated formula.
        """
        # Return a ForAll object with copied variables and negated formula
        # The negated formula might be complex, handled by its own negate method.
        return ForAll(copy.deepcopy(self.variables), self.formula.negate())

    def __eq__(self, other):
        """
        Checks for structural equality with another object.
        Equal if 'other' is an Exists with the same variables (order matters)
        and an equal formula.

        Args:
            other: The object to compare against.

        Returns:
            bool: True if structurally equal, False otherwise.
            NotImplemented: If 'other' is not an Exists object.
        """
        if not isinstance(other, Exists):
            return NotImplemented
        # Check variables list and the quantified formula
        return self.variables == other.variables and self.formula == other.formula

    def __hash__(self):
        """
        Computes a hash value based on the quantifier type ('exists'),
        variables (as a tuple), and the formula.

        Returns:
            int: The computed hash value.
        """
         # Convert variables list to tuple for hashing
        return hash(('exists', tuple(self.variables), self.formula))
