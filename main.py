import spacy
import hashlib
from Logica.logica import *

nlp = spacy.load("en_core_web_trf")

def has_dep(token, dep):
    """Checks if a token has a child with a specific dependency."""
    return any(child.dep_ == dep for child in token.children)

def get_dep(token, dep):
    """Returns the first child with a specific dependency."""
    return next((child for child in token.children if child.dep_ == dep), None)

def get_root(doc):
    """Returns the root of the dependency tree."""
    return next((token for token in doc if token.dep_ == "ROOT"), None)

def is_group(token) -> bool:
    if is_regular(token):
        return is_many(token) and (has_dep(token, "det") and get_dep(token, "det").text.lower() == "the")
    else:
        return False

def is_not(token) -> bool:
    """Checks if a token is a negation."""
    return any(child.dep_ == "neg" for child in token.children)

def is_many(token):
    """Checks if a token is plural."""
    return token.tag_ in ["NNS", "NNPS"]

def is_distinct(token):
    """Checks if a token is distinct, for example: Sam, Bob, Mary, etc."""
    return token.pos_ in ["PROPN", "NUM"]

def is_pron(token):    
    """Checks if a token is a pronoun, for example: he, she, it, etc."""
    return token.pos_ in ["PRON"]

def is_regular(token):
    """Checks if a token is a regular token, for example: dog, cat, run, etc."""
    return token.pos_ in ["NOUN"]

def is_action(token):
    """Checks if a token is an action, for example: run, jump"""
    return token.pos_ in ["VERB"]

def is_modifier(token):
    """Checks if a token is a modifier, for example: tall, big, small, etc."""
    return token.pos_ in ["ADJ", "ADV"]

def create_var(input_string: str, seed = 0, x = 3):
    """
    Generates a hash of length x for a given string and seed.

    Uses SHA-256 hashing combined with the seed, and then truncates the
    hexadecimal output to the specified length x.

    Note: If x is greater than the length of the SHA-256 hexdigest (64),
    the function will return the full 64-character hexdigest.

    Args:
        input_string: The string to hash.
        seed: A seed number to incorporate into the hash.
        x: The desired length of the hash string.

    Returns:
        A string representing the hash of length x (or 64 if x > 64).
    """
    # Combine the input string and the seed
    combined_input = f"{input_string}-{seed}"

    # Encode the combined input to bytes (required by hashlib)
    encoded_input = combined_input.encode('utf-8')

    # Create a SHA-256 hash object
    hasher = hashlib.sha256()

    # Update the hash object with the encoded input
    hasher.update(encoded_input)

    # Get the hexadecimal representation of the hash
    hex_digest = hasher.hexdigest()

    # Truncate the hash to the desired length x
    # Ensure x does not exceed the maximum length of the hexdigest
    truncated_hash = hex_digest[:min(x, len(hex_digest))]

    return truncated_hash

#TODO: Make the reference more precise to avoid duplications.
def ref(token, seed = 0, size=3):
    """Creates the variables that references a token."""
    if token is None:
        return "?" + create_var("", seed, size)
    
    if is_regular(token):
        return token.text[0] + create_var(token.text, seed, size-1)
    
    elif is_distinct(token):
        return token.text
    
    elif is_pron(token):
        return ref(token.head.head)
    
    elif is_action(token):
        return 'e' + create_var(token.text, seed, size-1)
    
    elif is_modifier(token):
        return 'm' + create_var(token.text, seed, size-1)

    else:
        for child in token.children:
                res = ref(child)
                if res:
                    return res

def find_conjuncts(token, operation=None):
    if token is None:
        return []
    conjuncts = []
    if conjs := list(token.conjuncts):
        for conj in conjs:
            if operation:
                conjuncts.append(operation(conj))
            else:
                conjuncts.append(conj)
    return conjuncts

def get_refs(token, seed=0, size=3):
    refs = []
    if token is None:
        return refs
    if is_regular(token):
        refs.append(ref(token, seed, size))
        if conjs := find_conjuncts(token, ref):
            refs.extend(conjs)
    else:
        skip = next((child for child in token.children), None)
        res = get_refs(skip, seed, size)
        if res:
            refs.extend(res)
    return refs

# Helper function for get_modifiers
def _get_modifiers(token, reference):
    mods = []
    for child in token.children:
        if child.dep_ in ["amod", "advmod", "compound"]:
            mods.append(predicate(child.text, [reference]))
            mods.extend(_nested(child, reference, child.lemma_))
        elif child.dep_ in ["acl"]:
            other = _get_modifiers(child, reference)
            mods.append(predicate("content", [reference, child.lemma_]))
            if other:
                mods.extend(other)
        elif child.dep_ in ["relcl"]:
            other = _snepslog(child)
            mods.append(predicate("concerns", [reference, child.lemma_]))
            if other:
                mods.append(other)
    return mods

def check_quantifier(token) -> bool:
    """ Checks if the subtree has regular quantifiers"""
    if token is None:
        return False
    if is_regular(token) or token.tag_ in ["NNS", "NNPS"]:
        if (det := get_dep(token, "det")) and (det.text.lower() in ["all", "every", "forall", "any"]):
            return True
    else:
        skip = next((child for child in token.children), None)
        if skip:
            return check_quantifier(skip)
        else:
            return False

# handles nested advmods
def _nested(token, ref, mod_text):
     m = []
     for child in token.children:
         if child.dep_ in ["amod","advmod"]:
             m.append(predicate(child.text, [ref, mod_text]))
             m.extend(_nested(child, ref, child.lemma_))
         else:
             m.extend(_get_modifiers(child, ref))
     return m

def get_modifiers(token, reference=None, rel=True):
    """Returns a list of all the modifiers of the given token."""
    res = []
    if token is None:
        return res
    elif is_distinct(token):
        res.extend(_get_modifiers(token, ref(token)))
        return res
    elif is_regular(token):
        if rel:
            res.append(predicate(token.lemma_, [ref(token)]))
        res.extend(_get_modifiers(token, ref(token)))
        return res
    elif is_action(token):
        res.extend(_get_modifiers(token, ref(token)))
        return res
    elif is_modifier(token):
        if reference:
            res.append(predicate("content", [reference, ref(token)]))
        res.append(predicate(token.lemma_, [ref(token)]))
        res.extend(_nested(token, ref(token), token.lemma_))
        return res
    else:
        skip = next((child for child in token.children), None)
        res.extend(get_modifiers(skip))
        if token.text.lower() not in ["than"]:
            if reference:
                res = [predicate(token.lemma_, [reference, predicate(group_set(skip))])] + res
        return res

def group_set(token):
    """returns a set of all the entities grouped together."""
    res = []
    if token is None:
        return res
    if token.conjuncts:
        res.extend(find_conjuncts(token, ref))
    elif token.pos_ == "ADP":
        skip = skip = next((child for child in token.children), None)
        if skip:
            return group_set(skip)
    res.append(ref(token))
    return res

def coordinate(input: list, operator="and", wrap=False) -> expression:
    if not input:
        return None
    elif len(input) == 1:
        return expression(input[0])
    else:
        res = input[0]
        for pred in input[1:]:
            res = expression((res, operator, pred), wrap=wrap)
        return res

def get_quantifiers(token):
    quants = []
    if token is None:
        return quants
    if (token.dep_ in ["det", "predet"]) and (token.text.lower() in ["all", "every", "forall", "any"]):
        quants.append(token.head)
    elif is_many(token) and not is_group(token) and token.dep_ not in  ["attr", "acomp"]:
        quants.append(token)
    for child in token.children:
        quants.extend(get_quantifiers(child))
    return quants

def get_groups(token):
    groups = []
    if token is None:
        return groups
    if is_group(token):
        groups.append(token)
    for child in token.children:
        groups.extend(get_groups(child))
    return groups

def get_singles(token):
    singles = []
    if token is None:
        return singles
    if (not is_group(token)) and (is_regular(token) or is_distinct(token)) and token.dep_ != "compound":
        singles.append(token)
    for child in token.children:
        singles.extend(get_singles(child))
    return singles

def surroundV2(wrap, obj):
    res = []
    res.append(predicate(wrap.lemma_, [obj]))
    res.extend(_nested(wrap, obj, wrap.lemma_))
    return res

def is_logical(token):
    """Checks if a token is a logical conjunction."""
    return has_dep(token, "cc")

def _snepslog(token):
    """Returns the _snepslog representation of a token of a sentence."""
    match token.pos_:
        case "VERB":

            info = {
                "event": None,
                "result": [],
                "vars": [],
                "antecedent": [],
                "consequent": [],
                "event_content": []
            }

            logic = {
                "conj": None,
                "cc": None,
            }

            flags = {
                "neg": False,
                "all": False,
                "group": False,
                "past": False,
                "future": False,
            }

            all_flags = {
                "nsubj": False,
                "dobj": False,
                "nsubjpass": False,
                "agent": False,
                "prep": False,
                "dative": False,
            }
            group_flags = {
                "nsubj": False,
                "dobj": False,
                "nsubjpass": False,
                "agent": False,
                "prep": False,
                "dative": False,
            }
            
            if is_not(token):
                flags["neg"] = True
                info["vars"].append(ref(token))

            if quants := get_quantifiers(token):
                flags["all"] = True
                info["vars"].extend([ref(quant) for quant in set(quants)])
                for child in token.children:
                    match child.dep_:
                        case "nsubj" | "nsubjpass":
                            if get_quantifiers(child):
                                all_flags["nsubj"] = True
                                all_flags["nsubjpass"] = True
                        
                        case "dobj" | "agent":

                            if get_quantifiers(child):
                                all_flags["dobj"] = True
                                all_flags["agent"] = True

                        case "dative":

                            if get_quantifiers(child):
                                all_flags["dative"] = True

                        case "prep":

                            if get_quantifiers(child):
                                all_flags["prep"] = True
                            
            if get_groups(token):
                flags["group"] = True
                for child in token.children:
                    match child.dep_:
                        case "nsubj" | "nsubjpass":
                            if get_groups(child):

                                group_flags["nsubj"] = True
                                group_flags["nsubjpass"] = True
                            
                                info["event_content"].append(create_var("thing"))
                        
                        case "dobj" | "agent":
                            if get_groups(child):

                                group_flags["dobj"] = True
                                group_flags["agent"] = True

                                info["event_content"].append(create_var("thing", 1))
                        case "dative":
                            if get_groups(child):

                                group_flags["dative"] = True

                                info["event_content"].append(create_var("thing", 2))
                        case "prep":
                            if get_groups(child):

                                group_flags["prep"] = True

                                info["event_content"].append(create_var("thing", 3))

            if flags["group"] and not flags["neg"]:
                info["event"] = predicate(ref(token), [predicate(info["event_content"])])
            else:
                info["event"] = predicate([ref(token)])

            for child in token.children:
                match child.dep_:

                    ######################### NSUBJ ######################### 
                    case "nsubj":
                        
                        if all_flags["nsubj"]: ###   ALL   ###
                            
                            mods = []
                            for quant in set(get_quantifiers(child)):
                                info["antecedent"].append(predicate(quant.lemma_, [ref(quant)]))
                                mods.extend(get_modifiers(quant, info["event"], False))
                            
                            info["consequent"].append(predicate("agent", [info["event"], predicate(group_set(child))]))
                            info["consequent"].extend(mods)
                        
                        elif flags["all"]:
                            
                            info["antecedent"].extend([predicate(single.lemma_, [ref(single)]) for single in get_singles(child)])
                            info["consequent"].append(predicate("agent", [info["event"], predicate(group_set(child))]))
                            if mods := get_modifiers(child, info["event"], False):
                                info["consequent"].extend(mods)

                        elif group_flags["nsubj"]: ###   GROUP   ###

                            tmp = []
                            tmp_2 = []
                            mods = []
                            
                            for group in get_groups(child):
                                tmp.append(ref(group))
                                tmp_2.append(predicate(group.lemma_, [create_var("thing")]))
                                mods.extend(get_modifiers(group, info["event"], False))
                            
                            info["vars"].append(create_var('thing'))

                            info["antecedent"].append(
                                predicate(
                                    "member",
                                    [create_var("thing"), predicate(tmp)]
                                )
                            )

                            info["consequent"].append(coordinate(tmp_2, "or", True))
                            info["consequent"].append(predicate("agent", [
                                info["event"],
                                create_var("thing")
                            ]))

                            info["result"].extend(mods)

                        elif flags["group"]:

                            info["consequent"].append(predicate("agent", [info["event"], predicate(group_set(child))]))
                            if mods := get_modifiers(child, info["event"]):
                                info["consequent"].extend(mods)
                            
                        else: ###   NORMAL   ###

                            info["result"].append(predicate("agent", [info["event"], predicate(group_set(child))]))
                            if mods := get_modifiers(child, info["event"]):
                                info["result"].extend(mods)


                    ######################### DOBJ ######################### 
                    case "dobj":

                        if all_flags["dobj"]: ###   ALL   ###
                            
                            mods = []
                            for quant in set(get_quantifiers(child)):
                                info["antecedent"].append(predicate(quant.lemma_, [ref(quant)]))
                                mods.extend(get_modifiers(quant, info["event"], False))
                            
                            info["consequent"].append(predicate("object", [info["event"], predicate(group_set(child))]))
                            info["consequent"].extend(mods)
                        
                        elif flags["all"]:

                            info["antecedent"].extend([predicate(single.lemma_, [ref(single)]) for single in get_singles(child)])
                            info["consequent"].append(predicate("object", [info["event"], predicate(group_set(child))]))
                            if mods := get_modifiers(child, info["event"], False):
                                info["consequent"].extend(mods)

                        elif group_flags["dobj"]:

                            tmp = []
                            tmp_2 = []
                            mods = []
                            
                            for group in get_groups(child):
                                tmp.append(ref(group))
                                tmp_2.append(predicate(group.lemma_, [create_var("thing", 1)]))
                                mods.extend(get_modifiers(group, info["event"], False))
                            
                            info["vars"].append(create_var('thing', 1))

                            info["antecedent"].append(
                                predicate(
                                    "member",
                                    [create_var("thing", 1), predicate(tmp)]
                                )
                            )

                            info["consequent"].append(coordinate(tmp_2, "or", True))
                            info["consequent"].append(predicate("object", [
                                info["event"],
                                create_var("thing", 1)
                            ]))

                            info["result"].extend(mods)

                        elif flags["group"]:

                            info["consequent"].append(predicate("object", [info["event"], predicate(group_set(child))]))
                            if mods := get_modifiers(child, info["event"]):
                                info["consequent"].extend(mods)

                        else:
                            info["result"].append(predicate("object", [info["event"], predicate(group_set(child))]))
                            if mods := get_modifiers(child, info["event"]):
                                info["result"].extend(mods)
                    
                    ######################### NSUBJPASS ######################### 
                    case "nsubjpass":

                        flags["past"] = True
                        if all_flags["nsubjpass"]: ###   ALL   ###
                            
                            mods = []
                            for quant in set(get_quantifiers(child)):
                                info["antecedent"].append(predicate(quant.lemma_, [ref(quant)]))
                                mods.extend(get_modifiers(quant, info["event"], False))
                            
                            info["consequent"].append(predicate("agent_pass", [info["event"], predicate(group_set(child))]))
                            info["consequent"].extend(mods)
                        
                        elif flags["all"]:
                                
                            info["antecedent"].extend([predicate(single.lemma_, [ref(single)]) for single in get_singles(child)])
                            info["consequent"].append(predicate("agent_pass", [info["event"], predicate(group_set(child))]))
                            if mods := get_modifiers(child, info["event"], False):
                                info["consequent"].extend(mods)
                        
                        elif group_flags["nsubjpass"]:

                            tmp = []
                            tmp_2 = []
                            mods = []
                            
                            for group in get_groups(child):
                                tmp.append(ref(group))
                                tmp_2.append(predicate(group.lemma_, [create_var("thing")]))
                                mods.extend(get_modifiers(group, info["event"], False))
                            
                            info["vars"].append(create_var('thing'))

                            info["antecedent"].append(
                                predicate(
                                    "member",
                                    [create_var("thing"), predicate(tmp)]
                                )
                            )

                            info["consequent"].append(coordinate(tmp_2, "or", True))
                            info["consequent"].append(predicate("object", [
                                info["event"],
                                create_var("thing")
                            ]))

                            info["result"].extend(mods)

                        elif flags["group"]:

                            info["consequent"].append(predicate("object", [info["event"], predicate(group_set(child))]))
                            if mods := get_modifiers(child, info["event"]):
                                info["consequent"].extend(mods)

                        else:

                            info["result"].append(predicate("object", [info["event"], predicate(group_set(child))]))
                            if mods := get_modifiers(child, info["event"]):
                                info["result"].extend(mods)
                    
                    ######################### AGENT ######################### 
                    case "agent":
                        
                        flags["past"] = True
                        if all_flags["agent"]: ###   ALL   ###
                            
                            mods = []
                            for quant in set(get_quantifiers(child)):
                                info["antecedent"].append(predicate(quant.lemma_, [ref(quant)]))
                                mods.extend(get_modifiers(quant, info["event"], False))
                            
                            info["consequent"].append(predicate("object_pass", [info["event"], predicate(group_set(child))]))
                            info["consequent"].extend(mods)
                        
                        elif flags["all"]:
                                
                            info["antecedent"].extend([predicate(single.lemma_, [ref(single)]) for single in get_singles(child)])
                            info["consequent"].append(predicate("object_pass", [info["event"], predicate(group_set(child))]))
                            if mods := get_modifiers(child, info["event"], False):
                                info["consequent"].extend(mods)
                        
                        elif group_flags["agent"]:

                            tmp = []
                            tmp_2 = []
                            mods = []
                            
                            for group in get_groups(child):
                                tmp.append(ref(group))
                                tmp_2.append(predicate(group.lemma_, [create_var("thing", 1)]))
                                mods.extend(get_modifiers(group, info["event"], False))
                            
                            info["vars"].append(create_var('thing', 1))

                            info["antecedent"].append(
                                predicate(
                                    "member",
                                    [create_var("thing", 1), predicate(tmp)]
                                )
                            )

                            info["consequent"].append(coordinate(tmp_2, "or", True))
                            info["consequent"].append(predicate("agent", [
                                info["event"],
                                create_var("thing", 1)
                            ]))

                            info["result"].extend(mods)
                        
                        elif flags["group"]:

                            info["consequent"].append(predicate("agent", [info["event"], predicate(group_set(child))]))
                            if mods := get_modifiers(child, info["event"]):
                                info["consequent"].extend(mods)

                        else:
                            
                            info["result"].append(predicate("agent", [info["event"], predicate(group_set(child))]))
                            if mods := get_modifiers(child, info["event"]):
                                info["result"].extend(mods)

                    ######################### DATIVE ######################### 
                    case "dative":

                        if all_flags["dative"]: ###   ALL   ###
                            
                            mods = []
                            for quant in set(get_quantifiers(child)):
                                info["antecedent"].append(predicate(quant.lemma_, [ref(quant)]))
                                mods.extend(get_modifiers(quant, info["event"], False))
                            
                            info["consequent"].append(predicate("recipient", [info["event"], predicate(group_set(child))]))
                            info["consequent"].extend(mods)
                        
                        elif flags["all"]:
                                
                            info["antecedent"].extend([predicate(single.lemma_, [ref(single)]) for single in get_singles(child)])
                            info["consequent"].append(predicate("recipient", [info["event"], predicate(group_set(child))]))
                            if mods := get_modifiers(child, info["event"], False):
                                info["consequent"].extend(mods)
                        
                        elif group_flags["dative"]:

                            tmp = []
                            tmp_2 = []
                            mods = []
                            
                            for group in get_groups(child):
                                tmp.append(ref(group))
                                tmp_2.append(predicate(group.lemma_, [create_var("thing", 2)]))
                                mods.extend(get_modifiers(group, info["event"], False))
                            
                            info["vars"].append(create_var('thing', 2))

                            info["antecedent"].append(
                                predicate(
                                    "member",
                                    [create_var("thing", 2), predicate(tmp)]
                                )
                            )

                            info["consequent"].append(coordinate(tmp_2, "or", True))
                            info["consequent"].append(predicate("recipient", [
                                info["event"],
                                create_var("thing", 2)
                            ]))

                            info["result"].extend(mods)

                        elif flags["group"]:

                            info["consequent"].append(predicate("recipient", [info["event"], predicate(group_set(child))]))
                            if mods := get_modifiers(child, info["event"]):
                                info["consequent"].extend(mods)

                        else:

                            info["result"].append(predicate("recipient", [info["event"], predicate(group_set(child))]))
                            if mods := get_modifiers(child, info["event"]):
                                info["result"].extend(mods)

                    ######################### PREP ######################### 
                    case "prep":

                        if all_flags["prep"]: ###   ALL   ###
                            
                            mods = []
                            for quant in set(get_quantifiers(child)):
                                info["antecedent"].append(predicate(quant.lemma_, [ref(quant)]))
                                mods.extend(get_modifiers(quant, info["event"], False))
                            
                            info["consequent"].append(predicate(child.text, [info["event"], predicate(group_set(child))]))
                            info["consequent"].extend(mods)
                        
                        elif flags["all"]:
                                
                            info["antecedent"].extend([predicate(single.lemma_, [ref(single)]) for single in get_singles(child)])
                            info["consequent"].append(predicate(child.text, [info["event"], predicate(group_set(child))]))
                            if mods := get_modifiers(child, info["event"], False):
                                info["consequent"].extend(mods)

                        elif group_flags["prep"]:

                            tmp = []
                            tmp_2 = []
                            mods = []
                            
                            for group in get_groups(child):
                                tmp.append(ref(group))
                                tmp_2.append(predicate(group.lemma_, [create_var("thing", 3)]))
                                mods.extend(get_modifiers(group, info["event"], False))
                            
                            info["vars"].append(create_var('thing', 3))

                            info["antecedent"].append(
                                predicate(
                                    "member",
                                    [create_var("thing", 3), predicate(tmp)]
                                )
                            )

                            info["consequent"].append(coordinate(tmp_2, "or", True))
                            info["consequent"].append(predicate(child.text, [
                                info["event"],
                                create_var("thing", 3)
                            ]))

                            info["result"].extend(mods)

                        elif flags["group"]:

                            if mods := get_modifiers(child, info["event"]):
                                info["consequent"].extend(mods)
                            
                        else:
                            if mods := get_modifiers(child, info["event"]):
                                info["result"].extend(mods)

                    ######################### CCOMP ######################### 
                    case "ccomp":

                        if flags["all"] or flags["group"]:

                            main = _snepslog(child)
                            info["consequent"].append(predicate('concerns', [info["event"], main]))

                        else:
                            main = _snepslog(child)
                            info["result"].append(predicate('concerns', [info["event"], main]))

                    ######################### ACOMP ######################### 
                    case "acomp":

                        if flags["all"] or flags["group"]:

                            if mods := get_modifiers(child, info["event"]):
                                info["consequent"].extend(mods)

                        else:
                            if mods := get_modifiers(child, info["event"]):
                                info["result"].extend(mods)

                    ######################### XCOMP ######################### 
                    case "xcomp":

                        if flags["all"] or flags["group"]:

                            main = _snepslog(child)
                            info["consequent"].extend(predicate('concerns', [info["event"], main]))

                        else:
                            main = _snepslog(child)
                            info["result"].extend(predicate('concerns', [info["event"], main]))

                    ######################### AMOD ######################### 
                    case "amod":

                        if flags["all"] or flags["group"]:
                            info["consequent"].extend(get_modifiers(token))
                        else:
                            info["result"].extend(get_modifiers(token))

                    ######################### ADVMOD ######################### 
                    case "advmod":

                        if flags["all"] or flags["group"]:
                            info["consequent"].extend(get_modifiers(token))
                        else:
                            info["result"].extend(get_modifiers(token))

                    ######################### AUX ######################### 
                    case "aux":
                        if child.text.lower() == "will":
                            flags["future"] = True

                    ######################### ADVCL ######################### 
                    case "advcl":

                        if flags["all"] or flags["group"]:
                            main = _snepslog(child)
                            info["consequent"].append(predicate('cause', [info["event"], main]))
                        else:
                            main = _snepslog(child)
                            info["result"].append(predicate('cause', [info["event"], main]))
                    
                    ######################### CONJ ######################### 
                    case "conj":

                        logic["conj"] = child

                    ######################### CC ######################### 
                    case "cc":

                        logic["cc"] = child.text

            if flags["all"]:
                        
                info["consequent"].insert(0, predicate(token.lemma_, [info["event"]]))
                exper = expression((coordinate(info["antecedent"]), "=>", coordinate(info["consequent"]) if not flags["neg"] else coordinate(info["consequent"]).negate()), True)
                exper = ForAll(info["vars"], exper)
                if logic["conj"] and logic["cc"]:
                    exper = expression( (exper, logic["cc"], _snepslog(logic["conj"])), True)
                return exper

                        
            elif flags["group"]:

                info["consequent"].insert(0, predicate(token.lemma_, [info["event"]]))
                exper = expression((coordinate(info["antecedent"]), "=>", coordinate(info["consequent"]) if not flags["neg"] else coordinate(info["consequent"]).negate()), True)
                exper = ForAll(info["vars"], exper)
                exper = expression((exper, 'and', coordinate(info["result"])))
                if logic["conj"] and logic["cc"]:
                    exper = expression( (exper, logic["cc"], _snepslog(logic["conj"])), True)
                return exper
                
            else:
                # add the main verb event to the beginning of the expression
                info["result"].insert(0, predicate(token.lemma_, [ref(token)]))

                # add the past cul if it was in the past
                if flags["past"]:
                    info["result"].append(predicate("cul", [info["event"], "past"]))
                if flags["future"]:
                    info["result"].append(predicate("cul", [info["event"], "future"]))
                
                # coordinate the result with `and` and if there is a neg negate the existential to all and negate th expression
                result = coordinate(info["result"]) if not flags["neg"] else ForAll(info["vars"], coordinate(info["result"]).negate()) 

                # if there was a conj with the verb add it
                if logic["conj"] and logic["cc"]:
                    result = expression( (result, logic["cc"], _snepslog(logic["conj"])) )
                return result

        case "AUX":
            info = {
                "main": None,
                "result": [],
                "vars": [],
                "antecedent": [],
                "consequent": [],
                "all": False,
                "neg": False,
            }

            logic = {
                "conj": None,
                "cc": None
            }
            

            if quants := get_quantifiers(token):
                info["all"] = True
                info["vars"].extend([ref(quant) for quant in set(quants)])

            for child in token.children:
                match child.dep_:
                    case "nsubj":
                        if info["all"]:
                            info["main"] = predicate(group_set(child))
                            info["antecedent"].extend(get_modifiers(child, info["main"]))
                        else:
                            info["main"] = predicate(group_set(child))
                            info["result"].extend(get_modifiers(child, info["main"]))

                    case "prep":
                        if info["all"]:
                            info["consequent"].extend(get_modifiers(child, info["main"]))
                        else:
                            info["result"].extend(get_modifiers(child, info["main"]))
                    
                    case "acomp" if child.tag_ == "JJ":

                        if info["all"]:
                            info["consequent"].extend(surroundV2(child, info["main"]))
                        else:
                            info["result"].extend(surroundV2(child, info["main"]))

                    case "acomp" if child.tag_ == "JJR":

                        if info["all"]:
                        
                            mod = child
                            skip = next((child for child in mod.children), None)
                            info["consequent"].extend(get_modifiers(skip))
                            obj = predicate(group_set(skip))
                            info["consequent"].append(predicate(mod.text, [info["main"], obj]))
                        
                        else:

                            mod = child
                            skip = next((child for child in mod.children), None)
                            info["result"].extend(get_modifiers(skip))
                            obj = predicate(group_set(skip))
                            info["result"].append(predicate(mod.text, [info["main"], obj]))

                    case "attr" if child.lemma_.lower() != "member":

                        if info["all"]:
                            info["consequent"].extend(surroundV2(child, info["main"]))
                        else:
                            info["result"].extend(surroundV2(child, info["main"]))

                    case "attr" if child.lemma_.lower() == "member":
                        
                        info["result"].append(predicate(child.text, [info["main"], 'c']))
                        info["result"].append(predicate("class", ['c']))
                        
                        info["consequent"] = predicate("member", [create_var('thing'), 'c'])
                        skip = next((child for child in child.children if child.dep_ == "prep"), None)
                        obj = predicate(group_set(skip))
                        info["result"].extend(get_modifiers(skip))
                        info["antecedent"] = predicate(obj, [create_var('thing')])
                        info["result"].append(ForAll([create_var('thing')], expression((info["consequent"], '=>', info["antecedent"]))))

                    case "conj":
                        logic["conj"] = child
                    case "cc":
                        logic["cc"] = child.text
                    case "neg":
                        info["neg"] = True

            if info["all"]:
                exper = expression((coordinate(info["antecedent"]), "=>", coordinate(info["consequent"])), True)
                exper = ForAll(info["vars"], exper if not info["neg"] else exper.negate())
                if logic["conj"] and logic["cc"]:
                    exper = expression( (exper, info["cc"], _snepslog(logic["conj"])), True)
                return exper
            else:
                exper = coordinate(info["result"])
                if info["neg"]:
                    exper = exper.negate()
                if logic["conj"] and logic["cc"]:
                    exper = expression( (exper, logic["cc"], _snepslog(logic["conj"])), True)
                return exper


    # Default case: General processing & fallthrough from cases above that didn't return
    children_to_process = [child for child in token.children if child.pos_ not in ["PUNCT", "SCONJ"]]
    if children_to_process:
        args = [_snepslog(child) for child in children_to_process]
        return predicate(token.lemma_, args)
    else:
        return predicate([token.lemma_])

def snepslog(sentence):
    doc = nlp(sentence)
    return _snepslog(get_root(doc))


# Test sentences including linking constructions
tests = [

    # --- SUBJECT-VERB-OBJECT EXAMPLES --- #
    
    # "Flowers bloom in the garden",
    # "The tall flowers don't bloom in the gardens",
    # "the flowers and the plants grow in the garden",
    # "the flowers and the plants grow in the gardens",
    # "boys hate apples",
    # "Sam surpasses Bob in height",
    
    # "the boy have been given a book by the girl",

    # "The boy is under the girl",
    # "the bus is inside the building",
    # "the dog is on the building",

    # "Sam feels that Bob likes tall Mary",
    # "boys give books to girls",
    # "the boy feel happy",
    # "Sam feels happy and confident",
    # "Sam likes Mary",
    # "dancers feel happy",
    # "the singers perform the songs",
    # "dancers and singers do not move gracefully",
    # "the dancers and the singers move gracefully",
    # "A big dog barked",
    # "sam killed a man for mary",
    # "sam will kill bob",
    # "the tall boy and a small girl does not like a coffee",
    # "John and Sam gave a book and a toy to a tall girl and tall Mary",
    # "the boy broke a window with a hammer at school",
    # "The cat sleeps",
    # "Sam believes that Bob likes a girl",
    # "Sam built a small house",
    # "Bob and Sara don't like the cats",
    # "Bob doesn't like the cats",
    # "the boss feels angry",
    # "the tall sweet girl and nice Mary killed a small man",
    # "a man was killed by the police",
    # "the rooms broke on the right",
    # "a boy does not strongly believes a dog",
    # "Sam played with a boy",
    # "Sam loves a lovely girl",
    # "the boy and the girl ate a cookie",
    # "Sam gives a book to Mary",
    # "the room is on the right",
    # "Caesar was stabbed by Brutus"
    # "the fat man died",
    # "John believes that Lucy is rich",
    # "The golfer who scored a 61, won the tournament.",
    # "the boy loves to pet a dog",
    # "Sam laughed and Sara slept",
    
    # --- AUX EXAMPLES --- #

    # "John is happy",
    # "John is not happy",
    # "John and Bob are happy",
    # "Bob and Sam are human",
    "Sam and Jerry and Bob are friends",
    # "Sam and Jerry and Bob are not good friends",
    # "the tall girl is cute",
    # "the tall girl is not cute",
    # "men are mortal",
    # "Sam is mortal",
    # "a tall girl is cute",
    # "the boy and the girl are tall",
    # "Sam is taller than Bob and Jake",
    # "Sam is taller than a small boy",
    # "long Sam is not taller than Bob",
    # "long Sam is not tall",

    # --- Given Examples --- #

    # "the dancers jumped",
    # "The bear viciously attacked the camper",
    # "Sam believes that Bob is taller than John",


    # -- Odd Examples -- #

    # "Sam is equal to Bob",
    # "Sam has the ability to run",
    # "Sam can run",
    # "Sam is able to run",
    # "Sam, Bob, and Jerry like a dog", # SpaCy decided to die on this one.
    # "Fido is a member of the class dog",
    # "Fido and Joy are members of the class dog",
    # "Fido belongs to the class_dog.",

    # --- Quantifier Examples --- #
    # "Every boy loves a dog",
    # "Every adventurous young boy deeply cherishes a loyal companion dog.",
    # "every man become old",
    # "all men become old",
    # "all men are mortal",

    
    # --- Testing --- #
    # "the very extremely tall man kicked the dog",
    # "sam feels scorched happy",
    # "the door is on the right",
    # "the door is very tall",

]

# Main part that runs the list of tests
for test in tests:
    print(test, " ➡ ", str(snepslog(test)) + '.', "\n")