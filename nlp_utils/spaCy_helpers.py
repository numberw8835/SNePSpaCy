import hashlib
from spacy.tokens import Token

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
        return "?" + create_var(token.text, seed, length-1)
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

#TODO: Complete the get_modifier function
def _get_modifiers(token: Token, reference: str) -> list:
    pass

def get_modifiers(token: Token, reference: str) -> list:
    """Returns a list of modifiers of the given token"""
    modifiers = []
    if token is None:
        return modifiers
    elif is_distinct(token):
        pass
