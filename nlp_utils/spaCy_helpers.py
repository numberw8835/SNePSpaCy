import hashlib
from collections import defaultdict
from spacy.tokens import Token
from logic_utls.logica import predicate, expression, ForAll, intentionalize

def get_root(sentence: list) -> Token:
    """Returns the root token"""
    return next((token for token in sentence if token.dep_ == "ROOT"), None)

def get_dependant(token: Token, dependency: str) -> Token:
    """Returns the dependant of a token with the given dependency"""
    return next((child for child in token.children if child.dep_ == dependency), None)

def has_dependant(token: Token, dependency: str) -> bool:
    """Checks if a token has a dependant with the given dependency"""
    return any(child.dep_ == dependency for child in token.children)

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

def is_generic(token: Token) -> bool:
    """Checks whether the sentence speaks of things in general (Dogs bark), not of an event (Dogs barked)"""
    return token.sent.root.tag_ in ["VBZ", "VBP"]

def is_many(token: Token) -> bool:
    """Checks whether the token is a plural quantifier"""
    return (
        (token.tag_ in ["NNS", "NNPS"] and token.dep_ != "attr" and is_generic(token)) or
        (any(child.lemma_.lower() in ["all", "forall", "every", "each"] for child in token.children))
    ) and not (any(child.lemma_.lower() in ["some", "many", "few", "the"] or child.dep_ == "nummod" for child in token.children))

def is_group(token: Token) -> bool:
    """Checks whether the token is a group of items"""
    return (
        token.tag_ in ["NNS", "NNPS"] and any(child.lemma_.lower() in ["some", "many", "few", "the"] for child in token.children))

def is_definite(token: Token) -> bool:
    """Checks whether the token refers to something already known: the dog, John's dog"""
    return any(child.lemma_.lower() == "the" or child.dep_ == "poss" for child in token.children)

def is_condition(token: Token) -> bool:
    """Checks whether the token is the head of an if clause"""
    return token.dep_ == "advcl" and any(child.dep_ == "mark" and child.lemma_.lower() == "if" for child in token.children)

def is_not(token: Token) -> bool:
    """Checks whether the token or its children indicate negation."""
    if token.dep_ == "neg" or token.lemma_.lower() in ["not", "no", "never"]:
        return True
    return any(is_not(child) for child in token.children if child.dep_ not in ["acl", "relcl", "ccomp", "xcomp", "advcl", "conj"])

def tense(token: Token) -> str:
    """Returns when the event of the token happens, or None for the present"""
    auxiliaries = [child for child in token.children if child.dep_ in ["aux", "auxpass"]]
    if any(aux.lemma_.lower() == "will" for aux in auxiliaries):
        return "FUTURE"
    elif token.tag_ == "VBD" or any(aux.tag_ == "VBD" for aux in auxiliaries):
        return "PAST"
    elif token.tag_ == "VBG":
        return "PRESENT"
    return None

def create_var(string: str, seed: int = 0, length: int = 5) -> str:
    """Creates a SHA-HASH of the given string with the given seed and length"""
    string = string + str(seed)
    hash_object = hashlib.sha256(string.encode())
    hex_dig = hash_object.hexdigest()
    return hex_dig[:length]

class discourse:
    """Remembers the referents mentioned so far, so that later mentions refer to the same ones"""
    def __init__(self):
        self.forget()

    def forget(self):
        self.used = set()
        self.mentions = []
        self.read(None)

    def read(self, sentence):
        """Starts a new sentence; a question gets variables instead of new referents"""
        self.refs = {}
        self.existentials = []
        self.asking = sentence is not None and sentence.text.strip().endswith("?")

    def new(self, token: Token, prefix: str, existential: bool = True) -> str:
        """Returns a reference that no other referent has"""
        seed = 0
        while prefix + create_var(token.text, seed, 4) in self.used:
            seed += 1
        new_ref = prefix + create_var(token.text, seed, 4)
        self.used.add(new_ref)
        if self.asking:
            return "?" + new_ref
        if existential:
            self.existentials.append(new_ref)
        return new_ref

    def mention(self, token: Token, token_ref: str) -> str:
        """Remembers that the token refers to token_ref"""
        if not self.asking:
            self.mentions.append((token.pos_, token.lemma_, token_ref))
        return token_ref

    def last(self, pos: str, lemma: str = None) -> str:
        """Returns the most recently mentioned referent with the given part of speech and lemma"""
        return next((r for p, l, r in reversed(self.mentions) if p == pos and lemma in [None, l]), None)

memory = discourse()

def ref(token: Token) -> str:
    """Returns a reference var to the given token, the same for every mention of the same referent"""
    if token.i not in memory.refs:
        memory.refs[token.i] = _ref(token)
    return memory.refs[token.i]

def _ref(token: Token) -> str:
    if is_distinct(token):
        return memory.mention(token, token.text)
    elif is_action(token):
        return memory.new(token, "e")
    elif is_state(token):
        return memory.new(token, "s")
    elif is_thing(token):
        if is_many(token):
            return memory.new(token, token.text[0], existential=False)
        definite = is_definite(token)
        known = memory.last("NOUN", token.lemma_) if definite else None
        return memory.mention(token, known or memory.new(token, token.text[0], existential=not (definite or is_group(token))))
    elif is_modifier(token):
        return memory.new(token, "m")
    elif is_num(token):
        return token.text
    elif is_pron(token):
        if token.tag_ in ["WP", "WDT"] and token.head.head.pos_ in ["NOUN", "PROPN"]:
            return ref(token.head.head)
        elif token.tag_ in ["WP", "WDT"] and memory.asking:
            return memory.new(token, "w")
        elif token.lemma_.lower() in ["he", "she", "his", "her"]:
            known = memory.last("PROPN")
        elif token.lemma_.lower() in ["it", "its", "they", "their"]:
            known = memory.last("NOUN")
        else:
            known = None
        return known or token.lemma_.lower()[0] + create_var(token.lemma_.lower(), 0, 4)
    elif is_particle(token):
        return memory.new(token, "p")
    else:
        raise Exception(f"({token}, {token.pos_}) Is an unknown token type")

def existentials(formula) -> list:
    """Returns the references in the formula that only say something exists: events, states and things introduced by a/an"""
    args = {arg for pred in formula._get_all_predicates() for arg in pred.args}
    return [arg for arg in memory.existentials if arg in args]

def predication(components: list) -> list:
    """What a state means: whatever is true of its attribute or content is true of what it refers to"""
    preds = [pred for component in components for pred in component._get_all_predicates()]
    subjects = [pred.args[1] for pred in preds if pred.predicate_name == "reference"]
    values = [pred.args[1] for pred in preds if pred.predicate_name in ["attribute", "content"]]
    stated = []
    for pred in preds:
        if len(pred.args) == 1 and pred.args[0] in values:
            for subject in subjects:
                same = predicate(pred.predicate_name, [subject])
                stated.append(same.negate() if pred.neg else same)
    return stated

def conditional(condition, consequence) -> ForAll:
    """Returns the rule: whenever the condition happens, the consequence happens too"""
    rule = expression((condition, "=>", consequence), wrap=True)
    variables = existentials(condition)
    if not variables:
        return rule
    rule = ForAll(variables, rule)
    for arg in existentials(consequence):
        if arg not in variables:
            rule.skolemize_arg(arg, variables)
    return rule

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

def combine(input_expr: expression, negation: bool = False) -> expression:
  
    if not isinstance(input_expr, expression) or not hasattr(input_expr, 'predicates'):
        return None

    # Extract all predicate objects from the input expression
    predicate_list = list(input_expr.predicates)

    if not predicate_list:
        return None

    # Group predicates by their name (e.g., 'agent', 'like')
    groups = defaultdict(list)
    for pred in predicate_list:
        if isinstance(pred, predicate):
            groups[pred.predicate_name].append(pred)

    if not groups:
        return None

    # Determine the operators based on the negation flag
    inner_op = 'and' if negation else 'or'
    outer_op = 'or' if negation else 'and'

    processed_groups = []
    for name, preds in groups.items():
        if negation:
            # Negate each predicate in the group for the negation case
            processed_preds = [p.negate() for p in preds]
        else:
            processed_preds = preds
        
        # Combine predicates within the group using the inner operator
        group_expr = coordinate(processed_preds, operator=inner_op, wrap=(len(processed_preds) > 1))
        if group_expr:
            processed_groups.append(group_expr)

    if not processed_groups:
        return None

    # Combine the processed groups using the outer operator
    return coordinate(processed_groups, operator=outer_op, wrap=False)

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

def _get_components(token: Token, reference: str=None, var: str=None, level: int=0) -> list:
    _components = []
    if token is None:
        return _components
    true_ref = var if var else ref(token)

    for child in token.children:
        if child.dep_ == "amod":
            mod = predicate(child.lemma_, [true_ref])
            mod = mod.negate() if has_dependant(child, "neg") else mod
            _components.append(mod)
            other = _get_components(child, reference, var, level)
            if other:
                _components.extend(other)
        elif child.dep_ == "advmod":
            mod = predicate(child.lemma_, [true_ref, token.lemma_])
            mod = mod.negate() if has_dependant(child, "neg") else mod
            _components.append(mod)
            other = _get_components(child, reference, var, level)
            if other:
                _components.extend(other)
        elif child.dep_ == "acl":
            other = main_snepslog(child)
            if other:
                _components.append(predicate("concerns", [true_ref, f"({other})"]))
        elif child.dep_ == "relcl":
            other = main_snepslog(child)
            if other:
                _components.append(predicate("concerns", [true_ref, f"({other})"]))
        elif child.dep_ == "xcomp":
            other = main_snepslog(child)
            if other:
                _components.append(predicate("concerns", [true_ref, f"({other})"]))
        elif child.dep_ == "ccomp":
            other = main_snepslog(child)
            if other:
                _components.append(predicate("concerns", [true_ref, f"({other})"]))
        elif child.dep_ == "prep":
            _components.extend(get_components(child, child.text, true_ref, var, level))
        elif child.dep_ == "poss":
            _components.extend(get_components(child, "possessor", true_ref, None, level))
        elif child.dep_ == "compound":
            _components.append(predicate(child.lemma_, [true_ref]))
            other = _get_components(child, reference, true_ref, level)
            if other:
                _components.extend(other)
        elif child.dep_ == "det": # Potential for change
            continue
            # _components.append(predicate(child.lemma_, [true_ref]))
        elif child.dep_ == "nummod":
            _components.append(predicate("quantity", [child.lemma_, true_ref]))
        elif child.dep_ == "conj":
            continue
        elif child.dep_ == "cc":
            continue
        elif child.dep_ == "mark":
            continue
        elif child.dep_ == "case":
            continue
        elif child.dep_ == "punct":
            continue
        else:
            print(f"Warning: {child.dep_} not implemented BASE_2")
    return _components

def get_components(token: Token, role: str=None, reference: str=None, var: str=None, level: int=0) -> list:
    """Returns a list of modifiers of the given token"""
    components = []
    if token is None:
        return components
    
    elif is_distinct(token) or is_pron(token) or is_num(token):
    
        components.append(predicate(role, [reference, ref(token)]))
        components.extend(_get_components(token, reference, var, level))
    
    elif is_thing(token):

        if is_many(token):
            
            components.append(
                ForAll(
                    [ref(token)],
                    expression((
                        predicate(token.lemma_, [ref(token)]),
                        "=>",
                        expression((
                            coordinate(_get_components(token, reference, ref(token), level)),
                            "and", 
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
                            coordinate(_get_components(token, reference, create_var("thing", level), level)),
                            "and",
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
            components.append(predicate(token.lemma_, [ref(token)])) # Add the token it self: boy(b) or cat(c)
            components.extend(_get_components(token, reference, var, level))

    elif is_action(token) or is_state(token):

        components.append(predicate(role, [reference, ref(token)]))
        components.append(main_snepslog(token))

    elif is_modifier(token):

        if token.tag_ == "JJR":
            pred = token.text
            cont = next(next(token.children, None).children, None)
            pred = pred + "_" + next(token.children, None).text
            components.append(predicate(role, [reference, ref(token)]))
            components.extend(get_components(cont, pred, ref(token), var, level))
        else:
            components.append(predicate(role, [reference, ref(token)]))
            components.append(predicate(token.text, [ref(token)]))
            components.extend(_get_components(token, reference, var, level))

    elif is_particle(token):

        skip = next((child for child in token.children), True)
        if skip:
            components.extend(get_components(skip, role, reference, var, level))

    elif token.pos_ in ["SCONJ"]:
        skip = next((child for child in token.children), True)
        if skip:
            components.extend(get_components(skip, token.text, reference, var, level))
    else:
        # raise Exception(f"({token}, {token.pos_}) Is an unknown token type, please account for it")
        print(f"Warning: ({token}, {token.pos_}) Is an unknown BASE_1 token type, please account for it")
    
    conjs = [child for child in token.children if child.dep_ == "conj"]

    if conjs:
        others = [get_components(conj, role, reference, var, level+1) for conj in conjs]
        connectives = [child.lemma_.lower() for head in [token] + conjs for child in head.children if child.dep_ == "cc"]
        if "or" in connectives:
            components = [coordinate([coordinate(option, wrap=True) for option in [components] + others], operator="or", wrap=True)]
        else:
            for other in others:
                components.extend(other)

    return components

def main_snepslog(token: Token) -> expression:

    if token is None:
        raise Exception("No token provided")
    seed = 0
    name = token.lemma_ if not is_state(token) else "state"
    negation = is_not(token)
    result = [predicate(name, [ref(token)])]
    conjunct = None
    connective = None
    condition = None

    for child in token.children:
        
        roles = {
            "nsubj": "reference" if is_state(token) else "agent",
            "dobj": "object",
            "nsubjpass": "object",
            "agent": "agent",
            "dative": "recipient",
            "prep": child.text,
            "xcomp": "concerns",
            "npadvmod": "time",
            "ccomp": "concerns",
            "dep": "dependant",
            "advcl": "cause",
            "acomp": "content",
            "attr": "attribute",
            "pobj": "object",
        }

        if is_condition(child):
            condition = main_snepslog(child)

        elif child.dep_ in roles:
            result.extend(get_components(child, roles[child.dep_], ref(token), None, seed))
            seed += len(result)

        elif child.dep_ in ["amod", "advmod"]:
            if not list(child.children):
                result.append(predicate(child.lemma_, [ref(token)]))
            result.extend(_get_components(child, None, ref(token), seed))

        elif child.dep_ == "conj":
            conjunct = main_snepslog(child)

        elif child.dep_ == "cc":
            connective = child.text

    if is_state(token) and not negation:
        result.extend(predication(result))
    when = tense(token)
    if when:
        result.append(predicate("culminate", [ref(token), when]))
    result = intentionalize(coordinate(result))

    if list(result.quantifiers):
        for quant in result.quantifiers:

            if isinstance(quant, ForAll):
                if not negation:
                    for arg in existentials(quant.formula):
                        if arg not in quant.variables:
                            quant.skolemize_arg(arg, list(dict.fromkeys(quant.variables)))
                else:
                    if isinstance(quant.formula, expression) and quant.formula.operator == "=>":
                        quant.variables.extend(arg for arg in existentials(quant.formula) if arg not in quant.variables)
                        if hasattr(quant.formula.operant_2, "negate") and isinstance(quant.formula.operant_2, expression):
                            quant.formula.operant_2 = combine(quant.formula.operant_2, negation)
    else:
        if negation:
            result = combine(result, negation)
            result = ForAll(existentials(result) or [ref(token)], result)
    if condition:
        result = conditional(condition, result)
    if conjunct:
        result = expression((result, connective, conjunct))
    return result