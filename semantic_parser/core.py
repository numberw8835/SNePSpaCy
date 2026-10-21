import spacy
from spacy.tokens import Token
from nlp_utils.spaCy_helpers import get_root, main_snepslog, sentence_scope

class snepslog:
    def __init__(self, model="en_core_web_trf"):
        self.model = model
        self.nlp = spacy.load(self.model)
        self.sentences = 0

    def transcribe(self, passage):
        doc = self.nlp(passage)
        # Each call gets its own constants: two sentences never share a state, event or thing.
        self.sentences += 1
        with sentence_scope(self.sentences):
            return self._sneps(get_root(doc))

    def _sneps(self, token: Token) -> str:
        return str(main_snepslog(token))
