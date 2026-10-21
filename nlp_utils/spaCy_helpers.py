import contextlib
import contextvars
import hashlib
import re
import warnings
from collections import defaultdict
from spacy.tokens import Token
from logic_utls.logica import predicate, expression, ForAll, intentionalize


class TranscriptionWarning(UserWarning):
    """Part of a sentence could not be translated and was left out of the result."""


# Identifiers such as car_1, person2 or stop_sign_1: letters plus digits or underscores, no spaces.
_IDENTIFIER = re.compile(r"(?=.*[A-Za-z])(?=.*[0-9_])[A-Za-z0-9_]+")

# Number of the sentence being transcribed. It is part of every generated constant, so the
# states, events and things of one sentence never share a constant with another sentence's.
_SENTENCE = contextvars.ContextVar("snepspacy_sentence", default=0)


@contextlib.contextmanager
def sentence_scope(number):
    """Generate constants for sentence `number` inside this block."""
    token = _SENTENCE.set(number)
    try:
        yield
    finally:
        _SENTENCE.reset(token)

def get_root(sentence: list) -> Token:
    """Returns the root token"""
    return next((token for token in sentence if token.dep_ == "ROOT"), None)

def get_dependant(token: Token, dependency: str) -> Token:
    """Returns the dependant of a token with the given dependency"""
    return next((child for child in token.children if child.dep_ == dependency), None)

def has_dependant(token: Token, dependency: str) -> bool:
    """Checks if a token has a dependant with the given dependency"""
    return any(child.dep_ == dependency for child in token.children)

def is_distinct(token: Token) -> bool:
    """Checks whether the token names an individual: a proper noun, a token spaCy could not
    tag (X), or an identifier such as car_1. spaCy tags the same identifier as NOUN, PROPN, NUM
    or X depending on context, so identifiers are recognised by their form."""
    return token.pos_ in ("PROPN", "X") or bool(_IDENTIFIER.fullmatch(token.text))

def is_action(token: Token) -> bool:
    """Checks whether the token is a Verb"""
    return token.pos_ == "VERB"

def is_state(token: Token) -> bool:
    """Checks if the token is a state of being"""
    return token.pos_ == "AUX"

def is_thing(token: Token) -> bool:
    """Checks whether the token is a Noun"""
    return token.pos_ == "NOUN"

def is_adj_modifier(token: Token) -> bool:
    """Checks whether the token is a modifier"""
    return token.pos_ == "ADJ"

def is_adv_modifier(token: Token) -> bool:
    """Checks whether the token is a adverbial modifier"""
    return token.pos_ == "ADV"

def is_modifier(token: Token) -> bool:
    """Checks whether the token is a modifier"""
    return is_adj_modifier(token) or is_adv_modifier(token)

def is_num(token: Token) -> bool:
    """Checks whether the token is a number"""
    return token.pos_ == "NUM"

def is_pron(token: Token) -> bool:
    """Checks whether the token is a pronoun"""
    return token.pos_ == "PRON"

def is_particle(token: Token) -> bool:
    """Checks whether the token is a positional marker"""
    return token.pos_ == "ADP"

def is_many(token: Token) -> bool:
    """Checks whether the token is a plural quantifier"""
    return (
        (token.tag_ in ["NNS", "NNPS"]) or 
        (any(child.lemma_.lower() in ["all", "forall", "every", "each"] for child in token.children))
    ) and not (any(child.lemma_.lower() in ["some", "many", "few", "the"] for child in token.children))

def is_group(token: Token) -> bool:
    """Checks whether the token is a group of items"""
    return (
        token.tag_ in ["NNS", "NNPS"] and any(child.lemma_.lower() in ["some", "many", "few", "the"] for child in token.children))

def is_not(token: Token) -> bool:
    """Checks whether the token or its children indicate negation."""
    if token.dep_ == "neg" or token.lemma_.lower() in ["not", "no", "never"]:
        return True
    return any(child.dep_ == "neg" or child.lemma_.lower() in ["not", "no", "never"] for child in token.children)

def create_var(string: str, seed: int = 0, length: int = 5) -> str:
    """Creates a SHA-HASH of the given string with the given seed and length"""
    string = string + str(seed)
    hash_object = hashlib.sha256(string.encode())
    hex_dig = hash_object.hexdigest()
    return hex_dig[:length]

def ref(token: Token, seed: int = 0, length: int = 9) -> str:
    """Returns a reference var to the given token.

    Names and numbers stand for themselves. Every other token gets a constant derived from its
    text, its position in the sentence and the sentence number, so two occurrences of "is" (or
    "a car") denote different individuals, within a sentence and across sentences.
    """
    key = f"{token.text}|{token.i}|{_SENTENCE.get()}"
    if is_distinct(token):
        return token.text
    elif is_action(token):
        return "e" + create_var(key, seed, length-1)
    elif is_state(token):
        return "s" + create_var(key, seed, length-1)
    elif is_thing(token):
        return token.text[0] + create_var(key, seed, length-1)
    elif is_modifier(token):
        return "m" + create_var(key, seed, length-1)
    elif is_num(token):
        return token.text
    elif is_pron(token):
        if token.head.head.pos_ in ["NOUN", "PROPN"]:
            return ref(token.head.head)
        else:
            return token.lemma_.lower()[0] + create_var(token.lemma_.lower(), seed, length-1)
    elif is_particle(token):
        return "p" + create_var(key, seed, length-1)
    else:
        raise Exception(f"({token}, {token.pos_}) Is an unknown token type")

def get_actors(token: Token) -> list:
    """Returns a list of actors of the given token"""
    actors = []
    if token is None:
        return actors
    elif is_distinct(token) or is_thing(token):
        actors.append(token)
    else:
        for child in token.children:
            actors.extend(get_actors(child))
    return actors

def combine(input_expr: expression, negation: bool = False) -> expression:
    """
    Combines predicates found within a given expression into a single new expression.
    It extracts all predicates from the input expression, ignoring other logical constructs.

    If negation is False:
    - Conjoins the extracted predicates in order, dropping exact duplicates. Repeating a
      predicate name in a statement asserts each instance, so they must not become a disjunction.
    Example: from expression(p(a) and q(c) and p(b)) -> p(a) and q(c) and p(b)

    If negation is True:
    - Groups extracted predicates by name.
    - Negates each predicate.
    - Combines negated predicates within the same group using 'and'.
    - Combines the resulting groups using 'or'.
    Example: from expression(p(a) and q(c) and p(b)) -> (~p(a) and ~p(b)) or ~q(c)
    """
    if not isinstance(input_expr, expression) or not hasattr(input_expr, 'predicates'):
        return None

    # Extract all predicate objects from the input expression
    predicate_list = list(input_expr.predicates)

    if not predicate_list:
        return None

    if not negation:
        return coordinate(list(dict.fromkeys(p for p in predicate_list if isinstance(p, predicate))), "and")

    # Group predicates by their name (e.g., 'agent', 'like')
    groups = defaultdict(list)
    for pred in predicate_list:
        if isinstance(pred, predicate):
            groups[pred.predicate_name].append(pred)

    if not groups:
        return None

    # Determine the operators based on the negation flag
    inner_op = 'and' if negation else 'or'
    outer_op = 'or' if negation else 'and'

    processed_groups = []
    for name, preds in groups.items():
        if negation:
            # Negate each predicate in the group for the negation case
            processed_preds = [p.negate() for p in preds]
        else:
            processed_preds = preds
        
        # Combine predicates within the group using the inner operator
        group_expr = coordinate(processed_preds, operator=inner_op, wrap=(len(processed_preds) > 1))
        if group_expr:
            processed_groups.append(group_expr)

    if not processed_groups:
        return None

    # Combine the processed groups using the outer operator
    return coordinate(processed_groups, operator=outer_op, wrap=False)

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

def _get_components(token: Token, reference: str=None, var: str=None, level: int=0, inline: bool=False) -> list:
    """Modifiers of `token` as predicates about it.

    With `inline`, a relative or adjectival clause contributes its own facts rather than a
    concerns(x, (...)) term, so it can serve as the condition of a rule ("every person that ...").
    """
    _components = []
    if token is None:
        return _components
    true_ref = var if var else ref(token)

    for child in token.children:
        if child.dep_ == "amod":
            mod = predicate(child.lemma_, [true_ref])
            mod = mod.negate() if has_dependant(child, "neg") else mod
            _components.append(mod)
            other = _get_components(child, reference, var, level)
            if other:
                _components.extend(other)
        elif child.dep_ == "advmod":
            mod = predicate(child.lemma_, [true_ref, token.lemma_])
            mod = mod.negate() if has_dependant(child, "neg") else mod
            _components.append(mod)
            other = _get_components(child, reference, var, level)
            if other:
                _components.extend(other)
        elif child.dep_ in ("acl", "relcl"):
            other = main_snepslog(child)
            if other and inline and not list(other.quantifiers):
                _components.extend(other.segments)
            elif other:
                _components.append(predicate("concerns", [true_ref, f"({other})"]))
        elif child.dep_ == "xcomp":
            other = main_snepslog(child)
            if other:
                _components.append(predicate("concerns", [true_ref, f"({other})"]))
        elif child.dep_ == "prep":
            _components.extend(get_components(child, child.text, true_ref, var, level))
        elif child.dep_ == "compound":
            _components.append(predicate(child.lemma_, [true_ref]))
        elif child.dep_ == "det":
            continue
        elif child.dep_ == "conj":
            continue
        elif child.dep_ == "cc":
            continue
        elif child.dep_ == "mark":
            continue
        else:
            warnings.warn(f"dependency '{child.dep_}' of '{token}' is not handled; '{child}' was left out",
                          TranscriptionWarning, stacklevel=2)
    return _components

def _restrictor_variables(token: Token, restrictor: list) -> list:
    """Constants that a quantified noun's modifiers introduce (the state of its relative clause,
    "a car", ...). They must be quantified too, or the rule would only match those exact constants."""
    used = {arg for item in restrictor if isinstance(item, predicate) for arg in item.args}
    variables = []
    for t in token.subtree:
        if t is token or is_distinct(t) or is_num(t) or is_pron(t):
            continue
        try:
            constant = ref(t)
        except Exception:
            continue
        if constant in used and constant not in variables:
            variables.append(constant)
    return variables

def get_components(token: Token, role: str=None, reference: str=None, var: str=None, level: int=0) -> list:
    """Returns a list of modifiers of the given token"""
    components = []
    if token is None:
        return components
    
    elif is_distinct(token) or is_pron(token) or is_num(token):
    
        components.append(predicate(role, [reference, ref(token)]))
        components.extend(_get_components(token, reference, var, level))
    
    elif is_thing(token):

        if is_many(token):

            # "Every person that is in front of a car ...": the noun and everything that restricts
            # it (relative clauses, prepositional phrases, adjectives) form the rule's condition.
            variable = ref(token)
            restrictor = [predicate(token.lemma_, [variable])] + \
                _get_components(token, reference, variable, level, inline=True)
            components.append(
                ForAll(
                    [variable] + _restrictor_variables(token, restrictor),
                    expression((
                        coordinate(restrictor),
                        "=>",
                        predicate(role, [reference, variable])
                    ))
                )
            )

        elif is_group(token):

            components.append(
                ForAll(
                    [create_var("thing", level)],
                    expression( (
                        predicate("member", [create_var("thing", level), ref(token)]),
                        "<=>",
                        # SNePS rejects an unparenthesised conjunction on the right of <=>.
                        expression((
                            coordinate(_get_components(token, reference, create_var("thing", level), level)),
                            "and",
                            predicate(token.lemma_, [create_var("thing", level)])
                        ), wrap=True)
                    ))
                )
            )

            components.append(
                ForAll(
                    [create_var("thing", level)],
                    expression( (
                        predicate("member", [create_var("thing", level), ref(token)]),
                        "=>",
                        predicate(role, [reference, create_var("thing", level)])
                    ))
                )
            )

        else:
            components.append(predicate(role, [reference, ref(token)]))
            components.append(predicate(token.text, [ref(token)])) # Add the token it self: boy(b) or cat(c)
            components.extend(_get_components(token, reference, var, level))

    elif is_action(token):

        components.append(predicate(role, [reference, ref(token)]))
        components.append(main_snepslog(token))

    elif is_modifier(token):

        components.append(predicate(role, [reference, ref(token)]))
        components.append(predicate(token.text, [ref(token)]))
        components.extend(_get_components(token, reference, var, level))

    elif is_particle(token):

        # Follow the preposition's object. An adverb attached to the preposition ("completely
        # to the left of") modifies the relation, so it is kept as a modifier of the reference.
        for child in token.children:
            if child.dep_ == "advmod":
                components.append(predicate(child.lemma_, [reference]))
        skip = next((child for child in token.children if child.dep_ in ("pobj", "pcomp")), None)
        if skip is None:
            skip = next((child for child in token.children if child.dep_ != "advmod"), None)
        if skip is not None:
            components.extend(get_components(skip, role, reference, var, level))

    elif token.pos_ in ["SCONJ"]:
        skip = next((child for child in token.children), None)
        if skip is not None:
            components.extend(get_components(skip, token.text, reference, var, level))
    else:
        warnings.warn(f"'{token}' ({token.pos_}) is not a handled token type and was left out",
                      TranscriptionWarning, stacklevel=2)
    
    conjs = [child for child in token.children if child.dep_ == "conj"]

    if conjs:
        for conj in conjs:
            components.extend(get_components(conj, role, reference, var, level+1))

    return components

def main_snepslog(token: Token) -> expression:

    if token is None:
        raise Exception("No token provided")
    seed = 0
    name = token.lemma_ if is_action(token) or is_particle(token) else "state"
    negation = is_not(token)
    result = [predicate(name, [ref(token)])]
    conjunct = None
    connective = None
    extra =[]

    for child in token.children:
        
        roles = {
            "nsubj": "reference" if is_state(token) else "agent",
            "dobj": "object",
            "nsubjpass": "object",
            "agent": "agent",
            "dative": "recipient",
            "prep": child.text,
            "xcomp": "concerns",
            "npadvmod": "time",
            "ccomp": "concerns",
            "dep": "dependant",
            "advcl": "cause",
            "acomp": "content",
            "attr": "attribute",
            "pobj": "object",
        }

        if child.dep_ in ["nsubjpass", "agent"]:
            extra.append(predicate("culminate", [ref(token), "PAST"]))
        elif token.tag_ == "VBG":
            extra.append(predicate("culminate", [ref(token), "PRESENT"]))
        elif child.dep_ == "aux" and child.text.lower() == "will":
                extra.append(predicate("culminate", [ref(token), "FUTURE"]))
                
        if child.dep_ in roles:
            result.extend(get_components(child, roles[child.dep_], ref(token), None, seed))
            seed += len(result)
        elif child.dep_ in ["amod", "advmod"]:
            if not list(child.children):
                result.append(predicate(child.lemma_, [ref(token)]))
            result.extend(_get_components(child, None, ref(token), seed))
        elif child.dep_ == "conj":
            conjunct = main_snepslog(child)
        elif child.dep_ == "cc":
            connective = child.text

    result.extend(list(dict.fromkeys(extra)))
    result = intentionalize(coordinate(result))

    if list(result.quantifiers):
        for quant in result.quantifiers:

            if isinstance(quant, ForAll):
                if not negation:
                    quant.skolemize_arg(ref(token), list(dict.fromkeys(quant.variables)))
                else:
                    if isinstance(quant.formula, expression) and quant.formula.operator == "=>":
                        quant.variables.append(ref(token))
                        if hasattr(quant.formula.operant_2, "negate") and isinstance(quant.formula.operant_2, expression):
                            quant.formula.operant_2 = combine(quant.formula.operant_2, negation)
    else:
        result = combine(result, negation)
        if negation:
            result = ForAll([ref(token)], result)
    if conjunct:
        result = expression((result, connective, conjunct))
    return result