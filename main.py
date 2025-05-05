import spacy
import hashlib
from Logica.logica import *

nlp = spacy.load("en_core_web_trf")

def has_dep(token, dep):
    """Checks if a token has a child with a specific dependency."""
    return any(child.dep_ == dep for child in token.children)

def is_many(token):
    return token.tag_ in ["NNS", "NNPS"] and is_regular(token)

def is_distinct(token):
    """Checks if a token is distinct, for example: Sam, Bob, Mary, etc."""
    return token.pos_ == "PROPN"

def is_regular(token):
    """Checks if a token is a regular token, for example: dog, cat, run, etc."""
    return token.pos_ in ["NOUN", "VERB", "PRON", "ADJ", "ADV"]
    # return token.pos_ in ["NOUN", "PRON"]

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
    if is_regular(token):
        return token.text[0] + create_var(token.text, seed, size-1)
    else:
        for child in token.children:
                res = ref(child)
                if res:
                    return res

def get_refs(token, seed=0, size=3):
    refs = []
    if is_regular(token):
        conjs = list(token.conjuncts)
        if conjs:
            for conj in conjs:
                refs.append(ref(conj, seed, size))
        refs.append(ref(token, seed, size))
    return refs


def ref_event(token):
    """Creates a variable that references an event."""
    return 'e' + ref(token)

# Helper function for get_modifiers
def _get_modifiers(token, reference):
    mods = []
    for child in token.children:
        if child.dep_ in ["amod", "advmod"]:
            other = _get_modifiers(child, reference)
            mods.append(predicate(child.text, [reference]))
            if other:
                mods.extend(other)
        elif child.dep_ == "conj":
            other = get_modifiers(child)
            if other:
                mods.extend(other)
    
    return mods

def get_modifiers(token, reference=None):
    """Returns a list of all the modifiers of the given token."""
    if token.pos_ == "VERB" or is_distinct(token):
        res = _get_modifiers(token, token)
        return res
    elif is_regular(token):
        res = _get_modifiers(token, ref(token))
        res.append(predicate(token.text, [ref(token)]))
        if token.tag_ in ["NNPS", "NNS"]:
            res.append(predicate("group", [ref(token)]))
        return res
    else:
        child = next((child for child in token.children), None)
        res = get_modifiers(child)
        if token.text.lower() not in ["than"]:
            if reference is not None:
                res.extend(follow(token, token, reference))
        return res

def follow(token, text, reference=None):
    """
    Give a sentences "like Sam gives a book to Mary" the dative of the root token is the token "to"
    we need to make sure that we follow every entity after that with that 'to' like this:
    to(e??, Mary) to specify that in that event the one given was Mary.

    The function follows these entities and returns a list of all the ones it has found.
    """
    found = []
    for child in token.children:
        if is_distinct(child):
            other = follow(child, text, reference)
            if reference is not None:
                found.append(predicate(text.text, [reference, child]))
            else:
                found.append(predicate(text.text, [child]))
            if other:
                found.extend(other)
        elif is_regular(child) and child.pos_ not in ["ADJ", "ADV"]:
            other = follow(child, text, reference)
            if reference is not None:
                found.append(predicate(text.text, [reference, ref(child)]))
            else:
                found.append(predicate(text.text, [ref(child)]))
            if other:
                found.extend(other)
    return found

#TODO: Find a better way to identify the if the sentence is an event or not.
def is_event(root):
    """Checks whether the root token is an event."""
    # return root.tag_ in ["VBP", "VBD", "VBG"]
    return root.tag_ in ["VBP", "VBD", "VBG", "VB", "VBZ"]

def group(token):
    """Groups all the entities logically together."""
    logic = next((child for child in token.children if child.dep_ == "cc"), None)
    conj = next((child for child in token.children if child.dep_ == "conj"), None)
    if is_distinct(token):
        if logic and conj:
            return f"({token} {logic} {group(conj)})"
        elif conj:
            return f"({token}, {group(conj)})"
        else:
            return token.text
    elif is_regular(token):
        if logic and conj:
            return f"({ref(token)} {logic} {group(conj)})"
        elif conj:
            return f"({ref(token)}, {group(conj)})"
        else:
            return ref(token)
    else:
        return group(next((child for child in token.children), None))

def group_set(token):
    """returns a set of all the entities grouped together."""
    res = []
    conjs = list(token.conjuncts)
    
    if conjs:
        
        if is_distinct(token):
            
            res.append(str(token))

        elif is_regular(token):

            res.append(ref(token))

        for conj in conjs:
            
            if is_distinct(conj):
            
                res.append(str(conj))
            
            elif is_regular(conj):
            
                res.append(ref(conj))

        return f"{{{', '.join(res)}}}"

    elif token.pos_ in ["ADP"]:
        
        child = next((child for child in token.children), None)
        return group_set(child)
    
    else: 
    
        if is_distinct(token):
            return token.text

        elif is_regular(token):
            return ref(token)

# Helper function for surround to grab any other child of child modifiers
def _surround(token):
    mods = []
    for child in token.children:
        if child.dep_ in ["amod", "advmod"]:
            other = _surround(child)
            mods.append(child)
            if other:
                mods.extend(other)
    return mods

def coordinate(input: list, operator="and", wrap=False) -> expression:
    result = expression(input[0], wrap)
    if len(input) == 1:
        return result
    else:
        for exper in input[1:]:
            result = expression((result, operator, exper), wrap)
    return result

def find_regular(token):
    if is_regular(token):
        return token
    else:
        for child in token.children:
            res = find_regular(child)
            if res:
                return res


def surround(wrap, obj):
    """Surrounds anything with it's modifiers"""
    mods = []
    res = predicate(wrap.text, [obj])
    for child in wrap.children:
        if child.dep_ in ["amod", "advmod"]:
            mods.append(child)
            other = _surround(child)
            if other:
                mods.extend(_surround(child))
    for mod in mods:
        res = predicate(mod.text, [res])
    return res

def is_logical(token):
    """Checks if a token is a logical conjunction."""
    return any(child.dep_ == "cc" for child in token.children)

def snepslog(token):
    """Returns the snepslog representation of a token of a sentence."""
    match token.pos_:
        case "VERB":
            ref = ref_event(token)
            ev_ref = predicate(ref, [create_var('thing')])
            result = []
            before = []
            after = []
            vars = []
            
            other = None
            cc = None

            neg = False
            nsubj_many = False
            dobj_many = False

            # Find which is the many and if there is a negation
            for child in token.children:
                if is_many(child) and child.dep_ in ["nsubj", "nsubjpass"]:
                    nsubj_many = True
                    ev_ref = predicate(ref, [create_var('thing')])
                elif is_many(child) and child.dep_ in ["dobj", "agent"]:
                    dobj_many = True
                    ev_ref = predicate(ref, [create_var('thing', seed=1)])
                if child.dep_ == "neg":
                    neg = True
            
            if nsubj_many and dobj_many:
                tmp = predicate([create_var('thing', seed=1), create_var('thing')])
                ev_ref = predicate(ref, [tmp])
            
            for child in token.children:
                match child.dep_:
                    case "nsubj" | "nsubjpass":
                    
                        if not nsubj_many and not dobj_many:

                            result.append(predicate("agent", [ref, group_set(child)]))
                    
                        else:
                            coo = []
                            if nsubj_many:
                                
                                before.append(predicate("member", [create_var('thing'), group_set(child)]))
                                vars.append(create_var('thing'))
                                
                                coo.append(predicate(child.lemma_, [create_var('thing')]))
                                if conjs := list(child.conjuncts):
                                    for conj in conjs:
                                        coo.append(predicate(conj.lemma_, [create_var('thing')]))
                            
                                after.append(coordinate(coo, "or", wrap=True))
                                after.append(predicate("agent", [ev_ref, create_var('thing')]))

                            else:
                                coo.append(predicate("agent", [ev_ref, child.text]))
                                if conjs := list(child.conjuncts):
                                    for conj in conjs:
                                        coo.append(predicate("agent", [ev_ref, conj.text]))
                                after.append(coordinate(coo, "and", wrap=True))

                        if mods := get_modifiers(child):
                            result.extend(mods)

                    case "dobj" | "agent":
                        
                        if not nsubj_many and not dobj_many:
                            
                            result.append(predicate("object", [ref, group_set(child)]))
                        
                        else:
                            coo = []
                            if dobj_many:
                                before.append(predicate("member", [create_var('thing', seed=1), group_set(child)]))
                                vars.append(create_var('thing', seed=1))

                                coo.append(predicate(child.lemma_, [create_var('thing', seed=1)]))
                                if conjs := list(child.conjuncts):
                                    for conj in conjs:
                                        coo.append(predicate(conj.lemma_, [create_var('thing', seed=1)]))

                                after.append(coordinate(coo, "or", wrap=True))
                                after.append(predicate("object", [ev_ref, create_var('thing', seed=1)]))

                            else:
                                coo.append(predicate("object", [ev_ref, child.text]))
                                if conjs := list(child.conjuncts):
                                    for conj in conjs:
                                        coo.append(predicate("object", [ev_ref, conj.text]))

                                after.append(coordinate(coo, "and", wrap=True))
                            
                        
                        if mods := get_modifiers(child):
                            result.extend(mods)

                    
                    case "prep":

                        if not nsubj_many and not dobj_many:
                            result.append(predicate(child.text, [ref, group_set(child)]))
                        else:
                            after.append(predicate(child.text, [predicate(ref, [create_var('thing')]), group_set(child)]))

                        if mods := get_modifiers(child):
                            result.extend(mods)

                    case "acomp":
                        
                        result.append(predicate("acomp", [ref, group_set(child)]))
                        
                        if mods := get_modifiers(child):
                            result.extend(mods)

                    case "amod" | "advmod":
                        
                        if not nsubj_many and not dobj_many:
                            result.append(predicate(child.text, [ref]))
                        else:
                            after.append(predicate(child.text, [ev_ref]))

                    case "dative":
                        result.append(predicate("dative", [ref, group_set(child)]))
                        
                        if mods := get_modifiers(child):
                            result.extend(mods)

                    case "xcomp" | "ccomp":
                        
                        if child.pos_ == "VERB":
                            result.append(predicate("cause", [ref, ref_event(child)]))
                            result.append(snepslog(child))

                        elif child.pos_ == "AUX":
                            result.append(predicate("cause", [ref, snepslog(child)]))
                    
                    case "conj":

                        other = snepslog(child)
                    
                    case "cc":

                        cc = child

            if nsubj_many or dobj_many:

                after.append(predicate(token.text, [ev_ref]))
                exper_1 = expression((coordinate(before), '=>', coordinate(after).negate() if neg else coordinate(after)))
                final = ForAll(vars, exper_1)
                tmp = coordinate(result)
                exper = expression((final, 'and' if not neg else 'or', tmp if not neg else tmp.negate()))

                if other:
                    exper = expression((exper, cc.text, other))

                return exper
            
            else:
            
                result = [predicate(token.text, [ref])] + result
                tmp = coordinate(result)

                res = (tmp.negate()) if neg else (tmp)

                if other:
                    res = expression((res, cc.text, other))

                return res

        # the case if the root node is an AUX
        case "AUX":
            result = []
            other = None
            cc = None
            neg = False
            subj = None
            for child in token.children:
                match child.dep_:
                    case "nsubj":

                        subj = group_set(child)

                        if mods := get_modifiers(child):
                            result.extend(mods)
                     
                    case "acomp" if child.tag_ == "JJ":

                        result.append(surround(child, subj))
                        
                    case "acomp" if child.tag_ == "JJR":

                        skip = next((child for child in child.children), None)
                        obj = group_set(skip)
                        result.append(predicate(child.text, [subj, obj]))

                        if mods := get_modifiers(skip):
                            result.extend(mods)

                    case "ccomp":

                        result.append(snepslog(child))

                    case "attr" if child.lemma_.lower() != "member":
                        
                        result.append(surround(child, subj))

                    case "attr" if child.lemma_.lower() == "member":
                        
                        result.append(predicate(child.text, [subj, 'c']))
                        result.append(predicate("class", ['c']))
                        
                        before = predicate("member", [create_var('thing'), 'c'])
                        skip = next((child for child in child.children if child.dep_ == "prep"), None)
                        obj = find_regular(skip)
                        after = predicate(obj.text, [create_var('thing')])
                        result.append(ForAll([create_var('thing')], expression((before, '=>', after))))
                    case "conj":
                        other = snepslog(child)
                    case "cc":
                        cc = child
                    case "neg":

                        neg = True
            
            result = coordinate(result)
            if other:
                result = expression((result, cc.text, other))
            return (result.negate()) if neg else (result)


    # Default case: General processing & fallthrough from cases above that didn't return
    children_to_process = [child for child in token.children if child.pos_ not in ["PUNCT", "SCONJ"]]
    if children_to_process:
        args = [snepslog(child) for child in children_to_process]
        return predicate(token.lemma_, args)
    else:
        return predicate([token.text])
            

# Test sentences including linking constructions
tests = [

    # --- SUBJECT-VERB-OBJECT EXAMPLES --- #
    
    # "Flowers bloom in the garden",
    # "boys hate apples",
    # "Sam surpasses Bob in height",
    # "Sam feels that Bob doesn't like tall Mary",
    # "Sam feels happy and confident",
    # "Sam likes Mary",
    # "dancers feel happy",
    # "Singers perform songs",
    # "dancers and singers do not move gracefully",
    # "dancers and singers move gracefully",
    # "A big dog barked",
    # "the tall boy and a small girl does not like a coffee",
    # "John and Sam gave a book and a toy to a tall girl and tall Mary",
    # "the boy broke a window with a hammer at school",
    # "The cat sleeps",
    # "Sam believes that Bob likes a girl",
    # "Sam built a small house",
    # "Bob doesn't like cats",
    # "the tall sweet girl and nice Mary killed a small man",
    # "a man was killed by a police_member",
    # "a boy does not strongly believes a dog",
    # "Sam played with a boy",
    # "Sam loves a lovely girl",
    # "Sam gives a book to Mary",
    # "the fat man died",
    # "the boy loves to pet a dog",
    # "Sam laughed and Sara slept",
    
    # --- AUX EXAMPLES --- #

    # "John is happy",
    # "John is not happy",
    # "John and Bob are happy",
    # "Bob and Sam are human",
    # "Sam and Jerry and Bob are friends",
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

    # "Sam is equal to Bob"
    # "Sam has the ability to run",
    # "Sam, Bob, and Jerry like a dog", # SpaCy decided to die on this one.
    # "Fido is a member of the class dog",
    # "Fido and Joy are members of the class dog",
    # "Fido belongs to the class_dog.",
]

# Main part that runs the list of tests
for test in tests:
    doc = nlp(test)
    root = [token for token in doc if token.dep_ == "ROOT"][0]
    print(test, " ➡ ", str(snepslog(root)) + '.', "\n")