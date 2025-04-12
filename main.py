import spacy

nlp = spacy.load("en_core_web_trf")

def ref(token):
    if token and token.pos_ in ["NOUN", "PROPN"]:
        return token.lemma_[0]
    for child in token.children:
        result = ref(child)
        if result:
            return result
    return ""

def handle_modifiers(token, reference):
    modifiers = []
    for child in token.children:
        if child.pos_ == "ADJ":
            modifiers.append(f"{child.lemma_}({reference})")
        elif child.pos_ == "ADV" and token.pos_ not in ["NOUN", "PROPN"]:
            modifiers.append(f"{child.lemma_}({reference})")
    return modifiers

def get_subjects_and_modifiers(token):
    current_mods = []

    is_propn_or_definite_noun = token.pos_ == "PROPN" or \
                               (token.pos_ == "NOUN" and \
                                any(child.dep_ == "det" and child.text.lower() == "the"
                                    for child in token.children))

    cc = next((child for child in token.children if child.dep_ == "cc"), None)
    conj = next((child for child in token.children if child.dep_ == "conj"), None)

    if is_propn_or_definite_noun:
        current_mods.extend(handle_modifiers(token, token))
        if cc and conj:
            conj_subject, conj_mods = get_subjects_and_modifiers(conj)
            subject_string = f"({token.text} {cc.text} {conj_subject})"
            all_mods = current_mods + conj_mods
            return subject_string, all_mods
        else:
            subject_string = token.text
            return subject_string, current_mods
    elif token.pos_ in ["ADP"]:
        child = next((child for child in token.children), None)
        if child:
            current_mods.append(f"{token.text}({ref(child)}, {child})")
            return ref(child), current_mods
    else:
        token_ref = ref(token)
        current_mods.append(f"{token.text}({token_ref})")
        current_mods.extend(handle_modifiers(token, token_ref))

        if cc and conj:
            conj_subject, conj_mods = get_subjects_and_modifiers(conj)
            subject_string = f"({token_ref} {cc.text} {conj_subject})"
            all_mods = current_mods + conj_mods
            return subject_string, all_mods
        else:
            subject_string = token_ref
            return subject_string, current_mods

def sneps(token):

    match token.pos_:
        case "VERB":
            subj = next((child for child in token.children if child.dep_ in ["nsubj", "nsubjpass"]), None)
            obj = next((child for child in token.children if child.dep_ in ["dobj", "agent"]), None)
            others = [child for child in token.children if child.dep_ not in ["dobj", "nsubj", "aux", "neg", "auxpass", "nsubjpass", "agent"]]
            neg = [child for child in token.children if child.dep_ in ["neg"]]
            args = []
            bef = []

            if subj:
                subj_string, subj_mods = get_subjects_and_modifiers(subj)
                args.append(subj_string)
                bef.extend(subj_mods)

            if obj:
                obj_string, obj_mods = get_subjects_and_modifiers(obj)
                args.append(obj_string)
                bef.extend(obj_mods)

            if others:
                for other in others:
                    other_string, other_mods = get_subjects_and_modifiers(other)
                    args.append(other_string)
                    bef.extend(other_mods)
            
            args_true = ", ".join([arg for arg in args if arg])
            bef_true = " & ".join(bef)
            verb_representation = f"{token.text}({args_true})" if args_true else token.text
            res = f"{verb_representation} & {bef_true}" if bef_true else verb_representation

            if neg:
                return "~"+res
            else:
                return res

        case "ADJ":
            return token.lemma_

        case "ADV":
            return token.lemma_

        case "ADP" if token.tag_ == "IN":
            child = next((child for child in token.children), None)
            if child:  # Ensure child exists before returning
                return f"{token.text}({ref(child)}, {child})"

    # Default case: General processing & fallthrough from cases above that didn't return
    children_to_process = [child for child in token.children if child.pos_ not in ["PUNCT", "DET"]]
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
    "John gives a book to Mary",
    "a boy broke a window with a hammer at school",
    "A cat sleeps",
    "Sam built a small house",
    "the tall sweet girl killed a small man",
    "a man was killed by a police_member",
    "a boy believes a dog"
    
    # --- AUX EXAMPLES --- #

    # "John is happy",
    # "Sam and Jerry or Bob are friends",
    # "the tall girl is cute",
    # "a tall girl is cute",
    # "the boy and the girl are tall"
]

for test in tests:
    doc = nlp(test)
    root = [token for token in doc if token.dep_ == "ROOT"][0]
    processed_result = sneps(root)
    # Ensure the result is stringifiable before calling lower()
    if not isinstance(processed_result, str):
        processed_result = processed_result.lemma_
    print(f"{test} -> {processed_result.lower()+'.'}")
