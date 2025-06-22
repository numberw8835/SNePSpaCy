import hashlib
from collections import defaultdict
from spacy.tokens import Token
from logic_utls.logica import predicate, expression, ForAll, intentionalize

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
    """Checks whether the token is a Proper Noun"""
    return token.pos_ == "PROPN"

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
    return any(is_not(child) for child in token.children)

def create_var(string: str, seed: int = 0, length: int = 5) -> str:
    """Creates a SHA-HASH of the given string with the given seed and length"""
    string = string + str(seed)
    hash_object = hashlib.sha256(string.encode())
    hex_dig = hash_object.hexdigest()
    return hex_dig[:length]

def ref(token: Token, seed: int = 0, length: int = 5) -> str:
    """Returns a reference var to the given token"""
    if is_distinct(token):
        return token.text
    elif is_action(token):
        return "e" + create_var(token.text, seed, length-1)
    elif is_state(token):
        return "s" + create_var(token.text, seed, length-1)
    elif is_thing(token):
        return token.text[0] + create_var(token.text, seed, length-1)
    elif is_modifier(token):
        return "m" + create_var(token.text, seed, length-1)
    elif is_num(token):
        return token.text
    elif is_pron(token):
        if token.head.head.pos_ in ["NOUN", "PROPN"]:
            return ref(token.head.head)
        else:
            return token.lemma_.lower()[0] + create_var(token.lemma_.lower(), seed, length-1)
    elif is_particle(token):
        return "p" + create_var(token.text, seed, length-1)
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
  
    if not isinstance(input_expr, expression) or not hasattr(input_expr, 'predicates'):
        return None

    # Extract all predicate objects from the input expression
    predicate_list = list(input_expr.predicates)

    if not predicate_list:
        return None

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

def _get_components(token: Token, reference: str=None, var: str=None, level: int=0, main_level: int=0) -> list:
    _components = []
    if token is None:
        return _components
    true_ref = var if var else ref(token)

    for child in token.children:
        if child.dep_ == "amod":
            mod = predicate(child.lemma_, [true_ref])
            mod = mod.negate() if has_dependant(child, "neg") else mod
            _components.append(mod)
            other = _get_components(child, reference, var, level, main_level)
            if other:
                _components.extend(other)
        elif child.dep_ == "advmod":
            mod = predicate(child.lemma_, [true_ref, token.lemma_])
            mod = mod.negate() if has_dependant(child, "neg") else mod
            _components.append(mod)
            other = _get_components(child, reference, var, level, main_level)
            if other:
                _components.extend(other)
        elif child.dep_ == "acl":
            other = main_snepslog(child, main_level+1)
            if other:
                _components.append(predicate("concerns", [true_ref, f"({other})"]))
        elif child.dep_ == "relcl":
            other = main_snepslog(child, main_level+1)
            if other:
                _components.append(predicate("concerns", [true_ref, f"({other})"]))
        elif child.dep_ == "xcomp":
            other = main_snepslog(child, main_level+1)
            if other:
                _components.append(predicate("concerns", [true_ref, f"({other})"]))
        elif child.dep_ == "ccomp":
            other = main_snepslog(child, main_level+1)
            if other:
                _components.append(predicate("concerns", [true_ref, f"({other})"]))
        elif child.dep_ == "prep":
            _components.extend(get_components(child, child.text, true_ref, var, level, main_level))
        elif child.dep_ == "compound":
            _components.append(predicate(child.lemma_, [true_ref]))
            other = _get_components(child, reference, var, level, main_level)
            if other:
                _components.extend(other)
        elif child.dep_ == "det": # Potential for change
            continue
            # _components.append(predicate(child.lemma_, [true_ref]))
        elif child.dep_ == "nummod":
            _components.append(predicate("quantity", [child.lemma_, true_ref]))
        elif child.dep_ == "conj":
            continue
        elif child.dep_ == "cc":
            continue
        elif child.dep_ == "mark":
            continue
        else:
            print(f"Warning: {child.dep_} not implemented BASE_2")
    return _components

def get_components(token: Token, role: str=None, reference: str=None, var: str=None, level: int=0, main_level: int=0) -> list:
    """Returns a list of modifiers of the given token"""
    components = []
    if token is None:
        return components
    
    elif is_distinct(token) or is_pron(token) or is_num(token):
    
        components.append(predicate(role, [reference, ref(token)]))
        components.extend(_get_components(token, reference, var, level, main_level))
    
    elif is_thing(token):

        if is_many(token):
            
            components.append(
                ForAll(
                    [ref(token)],
                    expression((
                        predicate(token.lemma_, [ref(token)]),
                        "=>",
                        expression((
                            coordinate(_get_components(token, reference, ref(token), level, main_level)),
                            "and", 
                            predicate(role, [reference, ref(token)])
                        ))
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
                        expression((
                            coordinate(_get_components(token, reference, create_var("thing", level), level, main_level)),
                            "and",
                            predicate(token.lemma_, [create_var("thing", level)])
                        ))
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
            components.extend(_get_components(token, reference, var, level, main_level))

    elif is_action(token) or is_state(token):

        components.append(predicate(role, [reference, ref(token, main_level+1)]))
        components.append(main_snepslog(token, main_level+1))

    elif is_modifier(token):

        if token.tag_ == "JJR":
            pred = token.text
            cont = next(next(token.children, None).children, None)
            pred = pred + "_" + next(token.children, None).text
            components.append(predicate(role, [reference, ref(token)]))
            components.append(predicate(pred, [ref(token), cont.text]))
            components.extend(_get_components(cont, reference, var, level, main_level))
        else:
            components.append(predicate(role, [reference, ref(token)]))
            components.append(predicate(token.text, [ref(token)]))
            components.extend(_get_components(token, reference, var, level, main_level))

    elif is_particle(token):

        skip = next((child for child in token.children), True)
        if skip:
            components.extend(get_components(skip, role, reference, var, level, main_level))

    elif token.pos_ in ["SCONJ"]:
        skip = next((child for child in token.children), True)
        if skip:
            components.extend(get_components(skip, token.text, reference, var, level, main_level))    
    else:
        # raise Exception(f"({token}, {token.pos_}) Is an unknown token type, please account for it")
        print(f"Warning: ({token}, {token.pos_}) Is an unknown BASE_1 token type, please account for it")
    
    conjs = [child for child in token.children if child.dep_ == "conj"]

    if conjs:
        for conj in conjs:
            components.extend(get_components(conj, role, reference, var, level+1, main_level))

    return components

def main_snepslog(token: Token, level: int=0) -> expression:

    if token is None:
        raise Exception("No token provided")
    seed = 0
    name = token.text if not is_state(token) else "state"
    negation = is_not(token)
    result = [predicate(name, [ref(token, seed=level)])]
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
            extra.append(predicate("culminate", [ref(token, seed=level), "PAST"]))
        elif token.tag_ == "VBG":
            extra.append(predicate("culminate", [ref(token, seed=level), "PRESENT"]))
        elif child.dep_ == "aux" and child.text.lower() == "will":
                extra.append(predicate("culminate", [ref(token, seed=level), "FUTURE"]))
                
        if child.dep_ in roles:
            result.extend(get_components(child, roles[child.dep_], ref(token, seed=level), None, seed, level))
            seed += len(result)

        elif child.dep_ in ["amod", "advmod"]:
            if not list(child.children):
                result.append(predicate(child.lemma_, [ref(token, seed=level)]))
            result.extend(_get_components(child, None, ref(token, seed=level), seed, level))

        elif child.dep_ == "conj":
            conjunct = main_snepslog(child, level+1)

        elif child.dep_ == "cc":
            connective = child.text

    result.extend(list(dict.fromkeys(extra)))
    result = intentionalize(coordinate(result))

    if list(result.quantifiers):
        for quant in result.quantifiers:

            if isinstance(quant, ForAll):
                if not negation:
                    quant.skolemize_arg(ref(token, seed=level), list(dict.fromkeys(quant.variables)))
                else:
                    if isinstance(quant.formula, expression) and quant.formula.operator == "=>":
                        quant.variables.append(ref(token, seed=level))
                        if hasattr(quant.formula.operant_2, "negate") and isinstance(quant.formula.operant_2, expression):
                            quant.formula.operant_2 = combine(quant.formula.operant_2, negation)
    else:
        if negation:
            result = combine(result, negation)
            result = ForAll([ref(token, seed=level)], result)
    if conjunct:
        result = expression((result, connective, conjunct))
    return result