import spacy
import spacy
import hashlib

nlp = spacy.load("en_core_web_trf")

def has_dep(token, dep):
    """Checks if a token has a child with a specific dependency."""
    return any(child.dep_ == dep for child in token.children)

def is_many(token):
    return token.tag_ in ["NNS", "NNPS"]

def is_distinct(token):
    """Checks if a token is distinct, for example: Sam, Bob, Mary, etc."""
    return token.pos_ == "PROPN"

def is_regular(token):
    """Checks if a token is a regular token, for example: dog, cat, run, etc."""
    return token.pos_ in ["NOUN", "VERB", "PRON", "ADJ", "ADV"]

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
        return create_var(token.text, seed, size)
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
            mods.append(f"{child}({reference})")
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
        res.append(f"{token}({ref(token)})")
        if token.tag_ in ["NNPS", "NNS"]:
            res.append(f"group({ref(token)})")
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
                found.append(f"{text}({reference}, {child})")
            else:
                found.append(f"{text}({child})")
            if other:
                found.extend(other)
        elif is_regular(child) and child.pos_ not in ["ADJ", "ADV"]:
            other = follow(child, text, reference)
            if reference is not None:
                found.append(f"{text}({reference}, {ref(child)})")
            else:
                found.append(f"{text}({ref(child)})")
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
    elif token.pos_ == "ADP":
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

def surround(wrap, obj):
    """Surrounds anything with it's modifiers"""
    res = obj
    mods = []
    mods.append(wrap)
    for child in wrap.children:
        if child.dep_ in ["amod", "advmod"]:
            mods.append(child)
            other = _surround(child)
            if other:
                mods.extend(_surround(child))
    for mod in mods:
        res = f"{mod}({res})"
    
    return res

def is_logical(token):
    """Checks if a token is a logical conjunction."""
    return any(child.dep_ == "cc" for child in token.children)

def snepslog(token):
    """Returns the snepslog representation of a token of a sentence."""
    match token.pos_:
        
        case "VERB":
            
            ref = ref_event(token)
            res = []

            after = []
            before = []
            mods = []
            vars = []
            
            other = []
            neg = False
            many = False 

            for child in token.children:
                match child.dep_:
                    
                    case "nsubj" | "nsubjpass":
                        
                        if not is_many(child):
                            res.append(f"agent({ref}, {group_set(child)})")
                            if get_modifiers(child):
                                    res.extend(get_modifiers(child))
                        else:
                            many = True
                            before.append(f"member({create_var('something')}, {group_set(child)})")
                            tmp = []
                            tmp.append(f"{child.lemma_}({create_var('something')})")
                            if conjs := list(child.conjuncts):
                                for conj in conjs:
                                    tmp.append(f"{conj.lemma_}({create_var('something')})")
                            after.append(f"({' or '.join(tmp)})")
                            vars.append(create_var('something'))
                            if get_modifiers(child):
                                    mods.extend(get_modifiers(child))

                    case "dobj" | "agent":

                        res.append(f"object({ref}, {group_set(child)})")
                        if get_modifiers(child):
                                res.extend(get_modifiers(child))

                    case "prep":
                        if not is_many(child):

                            #TODO: Find a way to deal with multi - preps
                            # res = f"{res} & {child.text}({ref}, {group_set(child)})"

                            if get_modifiers(child):
                                    res.extend(get_modifiers(child, ref))
                        else:
                            many = True
                            tmp = f"{ref}({create_var('something')})"
                            after.append(f"{get_modifiers(child, tmp)}")

                    case "acomp":
                        
                        res.append(f"acomp({ref}, {group_set(child)})")
                        if get_modifiers(child):
                                res.extend(get_modifiers(child, ref))

                    case "amod" | "advmod":
                        
                        res.append(f"{child}({ref})")
                    
                    case "dative":
                    
                        res.append(f"{child.text}({ref}, {group_set(child)})")
                        if get_modifiers(child):
                                res.extend(get_modifiers(child))
                    
                    case "xcomp" | "ccomp":
                    
                        res.append(snepslog(child))
                    
                    case "neg":
                        neg = True

            if not many:
                res = [f"{token.text}({ref_event(token)})"] + res
                return (' and '.join(res)) if not neg else negate(res)
            else:
                mods.extend(res)
                ev = f"{ref}({create_var('something')})"
                ver = f"{token.text}({ev})"
                ag = f"agent({ev}, {create_var('something')})"
                after.extend([ev, ver, ag])
                result = f"all({', '.join(vars)})({' and '.join(before)} => ({' and '.join(after)})) and {' and '.join(mods)}"
                return result if not neg else negate(result)

            
        # the case if the root node is an AUX
        case "AUX":

            res = []
            other = []
            neg=False
            subj = None

            for child in token.children:
                match child.dep_:
                    case "nsubj":
                        subj = group_set(child)
                        if get_modifiers(child):
                            other.extend(get_modifiers(child))
                    case "acomp" if child.tag_ == "JJ":
                        res.append(surround(child, subj))
                    case "acomp" if child.tag_ == "JJR":
                        skip = next((child for child in child.children))
                        res.append(f"{child}({subj}, {group_set(skip)})")
                        if get_modifiers(skip):
                            other.extend(get_modifiers(skip))
                    case "ccomp":
                        pass
                    case "attr":
                        res = f"{surround(child, subj)}"
                    case "neg":
                        neg = True
            if neg:
                pass
            if other:
                res.extend(other)
            return ' and '.join(res)
            

    # Default case: General processing & fallthrough from cases above that didn't return
    children_to_process = [child for child in token.children if child.pos_ not in ["PUNCT", "SCONJ"]]
    if children_to_process:
        args = ", ".join([snepslog(child) for child in children_to_process])
        return f"{token.lemma_}({args})"
    else:
        return token.lemma_


# Test sentences including linking constructions
tests = [

    # --- SUBJECT-VERB-OBJECT EXAMPLES --- #
    
    # "Flowers bloom in the garden",
    # "Sam surpasses Bob in height",
    # "Sam feels that Bob likes tall Mary",
    # "Sam feels happy and confident",
    # "Sam likes Mary",
    # "dancers feel happy",
    # "Singers perform songs",
    # "dancers and singers move gracefully",
    # "A big dog barked",
    # "the tall boy and a small girl does not like a coffee",
    # "John and Sam gave a book and a toy to a tall girl and tall Mary",
    # "the boy broke a window with a hammer at school",
    # "The cat sleeps",
    # "Sam believes that Bob likes a girl",
    # "Sam built a small house",
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
    # "John and Bob are happy",
    # "Bob and Sam are human",
    # "Sam and Jerry and Bob are friends",
    # "Sam and Jerry and Bob are good friends",
    # "the tall girl is cute",
    # "a tall girl is cute",
    # "the boy and the girl are tall",
    # "Sam is taller than Bob and Jake",
    # "Sam is taller than a small boy",
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
    # "Fido belongs to the class_dog.",
]

# Main part that runs the list of tests
for test in tests:
    doc = nlp(test)
    root = [token for token in doc if token.dep_ == "ROOT"][0]
    print(test, " ➡ ", snepslog(root)+'.', "\n")