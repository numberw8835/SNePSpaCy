import spacy

nlp = spacy.load("en_core_web_trf")

def has_dep(token, dep):
    return any(child.dep_ == dep for child in token.children)

def is_distinct(token):
    return token.pos_ == "PROPN" or (token.pos_ == "NOUN" and any(child.dep_ == "det" and child.text.lower == "the" for child in token.children))

def is_regular(token):
    return token.pos_ in ["NOUN", "VERB", "PRON", "ADJ"]

def ref(token):
    if is_regular(token):
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

#TODO: Add a method to deal with plural

def get_modifiers(token):

    if token.pos_ == "VERB" or is_distinct(token):
        return _get_modifiers(token, token)
    elif is_regular(token):
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
            other = ""
            neg = False
            for child in token.children:
                match child.dep_:
                    case "neg":
                        neg = True
                    case "nsubj" | "dobj" | "prep" | "dative" | "nsubjpass" | "agent" | "acomp": #TODO: Handle verb modifiers example: aux and adjectives
                        args.append(group(child))
                        mods.extend(get_modifiers(child))
                    case "ccomp":
                        args.append(f"({sneps(child)})")

            if any(child.dep_ in ["cc", "conj"] for child in token.children):
                cc = next((child for child in token.children if child.dep_ == "cc"), None)
                conj = next((child for child in token.children if child.dep_ == "conj"), None)
                other = f" {cc} {sneps(conj)}"

            if neg:
                res = f"~{token.lemma_}({', '.join(args)})"
            else:
                res = f"{token.lemma_}({', '.join(args)})"
            
            if mods:
                res = f"{res} and {' and '.join(mods)}"
            if other:
                res = res + other

            return res
        case "AUX":
            for child in token.children:
                match child.dep_:
                    case "acomp":
                        pass
                    case "ccomp":
                        pass
                    case "attr":
                        pass
            pass
            

    # Default case: General processing & fallthrough from cases above that didn't return
    children_to_process = [child for child in token.children if child.pos_ not in ["PUNCT", "SCONJ"]]
    if children_to_process:
        args = ", ".join([sneps(child) for child in children_to_process])
        return f"{token.lemma_}({args})"
    else:
        return token.lemma_


# Test sentences including linking constructions
tests = [

    # --- SUBJECT-VERB-OBJECT EXAMPLES --- #
    
    # "Flowers bloom in the garden",
    # "Sam surpasses Bob in height",
    "Sam feels that (Bob likes tall Mary) and Jerry like Sam",
    # "Sam feels happy and confident",
    # "Sam likes Mary",
    # "Singers perform songs",
    # "dancers move gracefully",
    # "A big dog barked",
    # "the tall boy and a small girl does not like a coffee",
    # "John and Sam gave a book and a toy to a tall girl and tall Mary",
    # "a boy broke a window with a hammer at school",
    # "A cat sleeps",
    # "Sam built a small house",
    # "the tall sweet girl and nice Mary killed a small man",
    # "a man was killed by a police_member",
    # "a boy does not strongly believes a dog",
    # "Sam played with a boy",
    # "Sam laughed and Sara slept",
    
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
    print(test, " ≡ ", sneps(root))