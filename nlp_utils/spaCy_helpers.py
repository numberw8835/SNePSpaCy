import hashlib
from spacy.tokens import Token
# import spacy
# from ..logic_utls.logica import predicate, expression, ForAll, intentionalize
from logic_utls.logica import predicate, expression, ForAll, intentionalize

def get_root(sentence: list) -> Token:
    """Returns the root token"""
    return next((token for token in sentence if token.dep_ == "ROOT"), None)

def get_dependant(token: Token, dependency: str) -> Token:
    """Returns the dependant of a token with the given dependency"""
    return next((child for child in token.children if child.dep_ == dependency), None)

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
    return any(child.dep_ == "neg" or child.lemma_.lower() in ["not", "no", "never"] for child in token.children)

def create_var(string: str, seed: int = 0, length: int = 3) -> str:
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

def _get_components(token: Token, negation: bool=False, reference: str=None, var: str=None, level: int=0) -> list:
    _components = []
    if token is None:
        return _components
    true_ref = var if var else ref(token)

    for child in token.children:
        if child.dep_ == "amod":
            _components.append(predicate(child.lemma_, [true_ref]))
        elif child.dep_ == "advmod":
            _components.append(predicate(child.lemma_, [true_ref, token.lemma_]))
            other = _get_components(child, negation, reference, var, level)
            if other:
                _components.extend(other)
        elif child.dep_ == "acl":
            other = main_snepslog(child)
            if other:
                _components.append(predicate("concerns", [true_ref, other]))
        elif child.dep_ == "relcl":
            other = main_snepslog(child)
            if other:
                _components.append(predicate("concerns", [true_ref, other]))
        elif child.dep_ == "prep":
            _components.extend(get_components(child, child.text, negation, true_ref, var, level))
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
            print(f"Warning: {child.dep_} not implemented")
    return _components

def get_components(token: Token, role: str=None, negation: bool=False, reference: str=None, var: str=None, level: int=0) -> list:
    """Returns a list of modifiers of the given token"""
    components = []
    if token is None:
        return components
    
    elif is_distinct(token) or is_pron(token) or is_num(token):
    
        components.append(predicate(role, [reference, ref(token)]))
        components.extend(_get_components(token, negation, reference, var, level))
    
    elif is_thing(token):

        if is_many(token):
            
            components.append(
                ForAll(
                    [ref(token)],
                    expression((
                        predicate(token.lemma_, [ref(token)]),
                        "=>",
                        expression((
                            coordinate(_get_components(token, negation, reference, ref(token), level),
                                        "and" if not negation else "or"),
                            "and" if not negation else "or",
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
                            coordinate(_get_components(token, negation, reference, create_var("thing", level), level),
                                        "and" if not negation else "or"),
                            "and" if not negation else "or",
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
            components.extend(_get_components(token, negation, reference, var, level))

    elif is_action(token):

        components.append(predicate(role, [reference, ref(token)]))
        components.append(main_snepslog(token))

    elif is_modifier(token):

        components.append(predicate(role, [reference, ref(token)]))
        components.append(predicate(token.text, [ref(token)]))
        components.extend(_get_components(token, negation, reference, var, level))

    elif is_particle(token):

        skip = next((child for child in token.children), True)
        
        if skip:
            combination = []
            combination.extend(get_components(skip, token.text, negation, reference, var, level))
            combination.extend(get_components(skip, role, negation, reference, var, level))
            components.extend(set(combination))
    elif token.pos_ in ["SCONJ"]:
        skip = next((child for child in token.children), True)
        if skip:
            components.extend(get_components(skip, token.text, negation, reference, var, level))    
    else:
        raise Exception(f"({token}, {token.pos_}) Is an unknown token type, please account for it")
    
    conjs = [child for child in token.children if child.dep_ == "conj"]
    if conjs:
        for conj in conjs:
            components.extend(get_components(conj, role, negation, reference, var, level+1))

    return components

#TODO: Handle the negation 
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
            "nsubj": "agent",
            "dobj": "object",
            "nsubjpass": "object",
            "agent": "agent",
            "dative": "recipient",
            "prep": child.text,
            "xcomp": "concerns",
            "npadvmod": "time",
            "ccomp": "concerns",
            "advcl": "cause",
            "acomp": "content",
            "attr": "attribute",
            "pobj": "object",
        }

        if child.dep_ in roles:
            
            if child.dep_ in ["nsubjpass", "agent"]:
                extra.append(predicate("culminate", [ref(token), "PAST"]))
            elif token.tag_ == "VBG":
                extra.append(predicate("culminate", [ref(token), "PRESENT"]))
            elif child.dep_ == "aux" and child.text.lower() == "will":
                extra.append(predicate("culminate", [ref(token), "FUTURE"]))

            result.extend(get_components(child, roles[child.dep_], negation, ref(token), None, seed))
            seed += len(result)
        elif child.dep_ in ["amod", "advmod"]:
            if not list(child.children):
                result.append(predicate(child.lemma_, [ref(token)]))
            result.extend(_get_components(child, negation, None, ref(token), seed))
        elif child.dep_ == "conj":
            conjunct = main_snepslog(child)
        elif child.dep_ == "cc":
            connective = child.text
            
    result = intentionalize(coordinate(result), negation)
    for quant in result.quantifiers:

        if isinstance(quant, ForAll):
            if not negation:
                quant.skolemize_arg(ref(token), quant.variables)
            else:
                if isinstance(quant.formula, expression) and quant.formula.operator == "=>":
                    quant.variables.append(ref(token))
                    if hasattr(quant.formula.operant_2, "negate"):
                        quant.formula.operant_2 = quant.formula.operant_2.negate()
    if conjunct:
        result = expression((result, connective, conjunct))
    return result 

## --- TESTING --- ###
# nlp = spacy.load("en_core_web_trf")
# doc = nlp("All boys like all dogs")
# root = get_root(doc)
# print(main_snepslog(root))