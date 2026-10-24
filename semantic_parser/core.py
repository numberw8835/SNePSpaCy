import spacy
from spacy.tokens import Span
from nlp_utils.spaCy_helpers import get_root, main_snepslog, memory

class snepslog:
    def __init__(self, model="en_core_web_trf"):
        self.model = model
        self.nlp = spacy.load(self.model)
    
    def transcribe(self, passage):
        doc = self.nlp(passage)
        formulas = [self._sneps(sentence) for sentence in doc.sents]
        return formulas[0] if len(formulas) == 1 else " and ".join(f"({formula})" for formula in formulas)

    def forget(self):
        """Forgets the referents mentioned so far, for a new knowledge base"""
        memory.forget()

    def _sneps(self, sentence: Span) -> str:
        memory.read(sentence)
        formula = str(main_snepslog(get_root(sentence)))
        people = [f"person({name})" for name in memory.introduced]
        return " and ".join([f"({formula})"] + people) if people else formula
