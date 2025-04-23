import spacy

nlp = spacy.load("en_core_web_trf")

def has_dep(token, dep):
    """Checks if a token has a child with a specific dependency."""
    return any(child.dep_ == dep for child in token.children)

def is_distinct(token):
    """Checks if a token is distinct, for example: Sam, Bob, Mary, etc."""
    return token.pos_ == "PROPN"

def is_regular(token):
    """Checks if a token is a regular token, for example: dog, cat, run, etc."""
    return token.pos_ in ["NOUN", "VERB", "PRON", "ADJ", "ADV"]

#TODO: Make the reference more precise to avoid duplications.
def ref(token):
    """Creates the variables that references a token."""
    if is_regular(token):
        return token.text[0] + f"{len(token.text)}"
    else:
        for child in token.children:
                res = ref(child)
                if res:
                    return res
        return None

def ref_event(token):
    return 'e' + token.text[0] + f"{len(list(token.children))}"

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

    if token.pos_ == "VERB" or is_distinct(token):
        res = _get_modifiers(token, token)
        if token.tag_ in ["NNPS", "NNS"]:
            res.append(f"group({token})")
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

def is_event(root):
    # return root.tag_ in ["VBP", "VBD", "VBG"]
    return root.tag_ in ["VBP", "VBD", "VBG", "VB", "VBZ"]

def group(token):
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
    return any(child.dep_ == "cc" for child in token.children)

def snepslog(token):
    match token.pos_:
        # the case if the root node is a VERB, but a simple verb like believe, taller than, and so on
        case "VERB" if not is_event(token):
            args = []
            mods = []
            other = ""
            res = f"{token.lemma_}"
            verb_mods = []
            neg = False
            for child in token.children:
                match child.dep_:
                    case "neg":
                        neg = True
                    case "nsubj" | "dobj" | "prep" | "dative" | "nsubjpass" | "agent" | "acomp":
                        args.append(group_set(child))
                        mods.extend(get_modifiers(child))
                    case "amod" | "advmod":
                        verb_mods.append(child)
                    case "ccomp" | "xcomp":

                        child_repr = snepslog(child)
                        # detach any extra conjuncts that belong to the complement
                        if " & " in child_repr:          # e.g. like(Bob, Mary) & tall(Mary)
                            core, rest = child_repr.split(" & ", 1)
                            args.append(f"{core}")     # <- only the core stays an argument
                            mods.append(rest)            # <- extras are lifted to this level
                        else:
                            args.append(f"({child_repr})")

            if any(child.dep_ in ["cc", "conj"] for child in token.children):
                cc = next((child for child in token.children if child.dep_ == "cc"), None)
                conj = next((child for child in token.children if child.dep_ == "conj"), None)
                other = f" {cc} {snepslog(conj)}"

            
            res = f"{res}({', '.join(args)})"
            
            if verb_mods:
                for verb_mod in verb_mods:
                    res = surround(verb_mod, res)
            
            if mods:
                res = f"{res} & {' & '.join(mods)}"
            if other:
                res = res + other

            if neg:
                res = f"~{res}"

            return res
        
        case "VERB" if is_event(token):
            
            ref = ref_event(token)
            res = f"{token.lemma_}({ref})"
            other = f""
            neg = False

            for child in token.children:
                match child.dep_:
                    case "nsubj" | "nsubjpass":
                        res = f"{res} & agent({ref}, {group_set(child)})"
                        if get_modifiers(child):
                                res = f"{res} & {' & '.join(get_modifiers(child))}"
                    case "dobj" | "agent":
                        res = f"{res} & object({ref}, {group_set(child)})"
                        if get_modifiers(child):
                                res = f"{res} & {' & '.join(get_modifiers(child))}"
                    case "prep":
                        if get_modifiers(child):
                                res = f"{res} & {' & '.join(get_modifiers(child, ref))}"
                    case "amod" | "advmod":
                        res = f"{res} & {child}({ref})"
                    case "dative":
                        res = f"{res} & dative({ref}, {group_set(child)})"
                        if get_modifiers(child):
                                res = f"{res} & {' & '.join(get_modifiers(child))}"
                    case "xcomp" | "ccomp":
                        res = f"{res} & {snepslog(child)}"
                    case "neg":
                        neg = True

            if any(child.dep_ in ["cc", "conj"] for child in token.children):
                cc = next((child for child in token.children if child.dep_ == "cc"), None)
                conj = next((child for child in token.children if child.dep_ == "conj"), None)
                other = f" {cc} {snepslog(conj)}"

            if neg:
                res = f"~{res}"
            if other:
                res = res + other
            return res
        # the case if the root node is an AUX
        case "AUX":

            res = f""
            other = f""
            neg=False

            for child in token.children:
                match child.dep_:
                    case "nsubj":
                        res = f"{group_set(child)}"
                        if get_modifiers(child):
                            other = f"{' & '.join(get_modifiers(child))}"
                    case "acomp" if child.tag_ == "JJ":
                        res = f"{surround(child, res)}"
                    case "acomp" if child.tag_ == "JJR":
                        skip = next((child for child in child.children))
                        res = f"{child}({res}, {group_set(skip)})"
                        if get_modifiers(skip):
                            other = f"{' & '.join(get_modifiers(skip))}"
                    case "ccomp":
                        pass
                    case "attr":
                        res = f"{surround(child, res)}"
                    case "neg":
                        neg = True
            if neg:
                res = f"~{res}"
            if other:
                res = f"{res} & {other}"
            return res

            

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
    # "Singers perform songs",
    # "dancers move gracefully",
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
    # "Fido belongs to the class dog.",
]

# Main part that runs the list of tests
for test in tests:
    doc = nlp(test)
    root = [token for token in doc if token.dep_ == "ROOT"][0]
    print(test, " ≡ ", snepslog(root))