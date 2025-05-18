import hashlib
from spacy.tokens import Token
from logic_utls.logica import predicate, expression, ForAll

def get_root(sentence: list) -> Token:
    """Returns the root token"""
    return next((token for token in sentence if token.dep_ == "ROOT"), None)

def get_dependant(token, dependency: str) -> Token:
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
    return (token.tag_ in ["NNS", "NNPS"] and any(child.lemma_.lower() in ["all", "forall", "every", "each"] for child in token.children))

def is_group(token: Token) -> bool:
    """Checks whether the token is a group of items"""
    return (token.tag_ in ["NNS", "NNPS"] and any(child.lemma_.lower() in ["some", "many", "few", "the"] for child in token.children))

def create_var(string: str, seed: int = 0, length: int = 3) -> str:
    """Creates a SHA-HASH of the given string with the given seed and length"""
    string = string + str(seed)
    hash_object = hashlib.sha256(string.encode())
    hex_dig = hash_object.hexdigest()
    return hex_dig[:length]

def ref(token: Token, seed: int = 0, length: int = 3) -> str:
    """Returns a reference var to the given token"""
    if is_distinct(token):
        return token.text
    elif is_action(token):
        return "e" + create_var(token.text, seed, length-1)
    elif is_thing(token):
        return token.text[0] + create_var(token.text, seed, length-1)
    elif is_modifier(token):
        return "m" + create_var(token.text, seed, length-1)
    elif is_num(token):
        return token.text
    elif is_pron(token):
        return ref(token.head.head)
    elif is_particle(token):
        raise Exception(f"({token}) Not direct reference")
    else:
        raise Exception(f"({token}) Is an unknown token type")

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

def _get_components(token: Token, role: str=None, negation: bool=False, reference: str=None, var: str=None, level: int=0) -> list:
    _components = []
    if token is None:
        return _components
    for child in token.children:
        if child.dep_ == "amod":
            _components.append(predicate(child.lemma_, [ref(token)]))
        elif child.dep_ == "advmod":
            _components.append(predicate(child.lemma_, [ref(token), token.lemma_]))
            other = _get_components(child, role, negation, reference, var, level)
            if other:
                _components.extend(other)
        elif child.dep_ == "conj":
            _components.extend(get_components(child, role, negation, reference, var, level))
        elif child.dep_ == "acl":
            other = main_snepslog(child)
            if other:
                _components.append(predicate("concerns", [ref(token), other]))
        elif child.dep_ == "relcl":
            if other:
                _components.append(predicate("concerns", [ref(token), other]))
        elif child.dep_ == "compound":
            _components.append(predicate(child.lemma_, [ref(token)]))
        elif child.dep_ == "det":
            pass
        else:
            print(f"Warning: {child.dep_} not implemented")
        return _components

def get_components(token: Token, role: str=None, negation: bool=False, reference: str=None, var: str=None, level: int=0) -> list:
    """Returns a list of modifiers of the given token"""
    components = []

    if token is None:
        return components
    
    elif is_distinct(token):
    
        components.append(predicate(role, [reference, ref(token)]))
        components.extend(_get_components(token, role, negation, reference, var, level))
        return components
    
    elif is_thing(token):

        var_entity = var if var else ref(token)
        components.append(predicate(role, [reference, var_entity]))
        components.append(predicate(token.text, [var_entity])) # Add the token it self: boy(b) or cat(c)
        components.extend(_get_components(token, role, negation, reference, var_entity, level))
        return components

    elif is_action(token):

        components.append(predicate(role, [reference, ref(token)]))
        components.append(predicate(token.lemma_, [ref(token)])) 
        components.extend(main_snepslog(token))
        return components

    elif is_modifier(token):

        components.append(predicate(role, [reference, ref(token)]))
        components.append(predicate(token.text, [ref(token)]))
        components.extend(_get_components(token, role, negation, reference, var, level))
        return components

    elif is_particle(token):

        skip = next((child for child in token.children), True)
        if skip:
            components.extend(get_components(token, token.text, negation, reference, var, level))
        return components
    
    else:
        raise Exception(f"({token}, {token.pos_}) Is an unknown token type, please account for it")

#TODO: Handle the children, nsubj, dobj, and so on...
def main_snepslog(token: Token) -> expression:

    if token is None:
        raise Exception("No token provided")
    
    main = {
    }

    match token.pos_:
        case "VERB":
            for child in token.children:
                pass

        case "AUX":
            for child in token.children:
                pass