import spacy
from spacy.tokens import Token
from nlp_utils.spaCy_helpers import get_root, main_snepslog

class snepslog:
    def __init__(self, model="en_core_web_trf"):
        self.model = model
        self.nlp = spacy.load(self.model)
    
    def transcribe(self, passage):
        doc = self.nlp(passage)
        sentences = [sent for sent in doc.sents]
        transcribed = []
        for sent in sentences:
            transcribed.append(self._sneps(get_root(sent)))
        return transcribed

    def _sneps(self, token: Token) -> str:
        return str(main_snepslog(token))