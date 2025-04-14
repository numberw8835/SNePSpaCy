import spacy

nlp = spacy.load("en_core_web_trf")

def has_dep(token, dep):
    return any(child.dep_ == dep for child in token.children)

def is_distinct(token):
    return token.pos_ == "PROPN" or (token.pos_ == "NOUN" and any(child.dep_ == "det" and child.text.lower == "the" for child in token.children))

def is_regular(token):
    return token.pos_ == "NOUN" or token.pos_ == "VERB"

def ref(token):
    if token.pos_ in ["NOUN"]:
        return str(token)[0]
    else:
        for child in token.children:
                res = ref(child)
                if res:
                    return res
        return None

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

def get_modifiers(token):

    if token.pos_ == "VERB" or is_distinct(token):
        return _get_modifiers(token, token)
    elif token.pos_ in ["NOUN", "VERB"]:
        res = _get_modifiers(token, ref(token))
        res.append(f"{token}({ref(token)})")
        return res
    else:
        child = next((child for child in token.children), None)
        res = get_modifiers(child)
        res.extend(follow(token, token))
        return res

def follow(token, text):
    found = []
    for child in token.children:
        if is_distinct(child):
            other = follow(child, text)
            found.append(f"{text}({child})")
            if other:
                found.extend(other)
        elif is_regular(child):
            other = follow(child, text)
            found.append(f"{text}({ref(child)})")
            if other:
                found.extend(other)
    return found

def group(token):
    logic = next((child for child in token.children if child.dep_ == "cc"), None)
    conj = next((child for child in token.children if child.dep_ == "conj"), None)
    if is_distinct(token):
        if logic and conj:
            return f"({token} {logic} {group(conj)})"
        else:
            return token.text
    elif is_regular(token):
        if logic and conj:
            return f"({ref(token)} {logic} {group(conj)})"
        else:
            return ref(token)
    else:
        return group(next((child for child in token.children), None))

def sneps(token):
    match token.pos_:
        case "VERB":
            args = []
            mods = []
            neg = False
            for child in token.children:
                if child.dep_ == "neg":
                    neg = True
                if child.dep_ not in ["neg", "aux", "auxpass", "advmod", "amod"]:
                    args.append(group(child))
                    mods.extend(get_modifiers(child))
            if neg:
                res = f"~{token.lemma_}({', '.join(args)}) & {' & '.join(mods)}"
            else:
                res = f"{token.lemma_}({', '.join(args)}) & {' & '.join(mods)}"
            return res
        case "AUX":
            pass
            

    # Default case: General processing & fallthrough from cases above that didn't return
    children_to_process = [child for child in token.children if child.pos_ not in ["PUNCT"]]
    if children_to_process:
        args = ", ".join([sneps(child) for child in children_to_process])
        return f"{token.lemma_}({args})"
    else:
        return token.lemma_


# Test sentences including linking constructions
tests = [
    # --- SUBJECT-VERB-OBJECT EXAMPLES --- #
    
    "A big dog barked",
    "the tall boy and a small girl does not like a coffee",
    "John and Sam gave a book and a toy to a tall girl and tall Mary",
    "a boy broke a window with a hammer at school",
    "A cat sleeps",
    "Sam built a small house",
    "the tall sweet girl and nice Mary killed a small man",
    "a man was killed by a police_member",
    "a boy does not strongly believes a dog"
    
    # --- AUX EXAMPLES --- #

    # "John is happy",
    # "Sam and Jerry or Bob are friends",
    # "the tall girl is cute",
    # "a tall girl is cute",
    # "the boy and the girl are tall"
    # "Sam is taller than Bob",
    # "Sam is taller than a boy",
]

for test in tests:
    doc = nlp(test)
    root = [token for token in doc if token.dep_ == "ROOT"][0]
    print(sneps(root))