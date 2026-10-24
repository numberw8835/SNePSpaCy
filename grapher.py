import tempfile
import click
import graphviz
import spacy

# SVG color names: graphviz reads them as is, LaTeX needs xcolor with [svgnames]
COLORS = {"VERB": "LightGreen", "ADJ": "LightPink", "DET": "PeachPuff", "PROPN": "Plum", "NOUN": "Plum"}
LATEX_ESCAPES = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
                 "~": r"\textasciitilde{}", "^": r"\textasciicircum{}", "\\": r"\textbackslash{}"}

def color(token) -> str:
    """Picks the fill color of a token: ROOT and attr first, then by part of speech."""
    if token.dep_ == "ROOT":
        return "LightCoral"
    if token.dep_ == "attr":
        return "LimeGreen"
    return COLORS.get(token.pos_, "LightBlue")

def escape(text: str) -> str:
    return "".join(LATEX_ESCAPES.get(char, char) for char in text)

def words(token) -> list:
    """The children of the token, without punctuation."""
    return [child for child in token.children if child.pos_ != "PUNCT"]

def to_graph(doc) -> graphviz.Digraph:
    graph = graphviz.Digraph(graph_attr={"label": f"Statement: {doc.text}", "labelloc": "t", "ordering": "out"},
                             node_attr={"shape": "box", "style": "rounded,filled", "fontname": "Helvetica"},
                             edge_attr={"fontname": "Helvetica", "fontsize": "10"})
    for token in doc:
        if token.pos_ == "PUNCT":
            continue
        graph.node(str(token.i), f"{token.text}\n{token.pos_} · {token.tag_}", fillcolor=color(token))
        if token.dep_ != "ROOT":
            graph.edge(str(token.head.i), str(token.i), label=token.dep_)
    return graph

def to_forest(token) -> str:
    """The subtree of the token in the bracket notation of the forest package."""
    edge = "" if token.dep_ == "ROOT" else f", edge label={{node[midway, fill=white, inner sep=1pt, font=\\scriptsize]{{{token.dep_}}}}}"
    children = "".join(f" {to_forest(child)}" for child in words(token))
    return f"[{{\\textbf{{{escape(token.text)}}}\\\\{token.pos_}\\\\{escape(token.tag_)}}}, fill={color(token)}{edge}{children}]"

def to_latex(doc) -> str:
    """One forest per sentence; needs \\usepackage{forest} and \\usepackage[svgnames]{xcolor}."""
    return "\n".join(f"\\begin{{forest}}\n  for tree={{draw, rounded corners, align=center, font=\\small, l sep=3em, s sep=3em}}\n  {to_forest(sentence.root)}\n\\end{{forest}}"
                     for sentence in doc.sents)

@click.command()
@click.option('--model', default="en_core_web_trf", help="The spaCy model that parses the statements.")
def grapher(model):
    """
    Draws the dependency tree of each statement from top to bottom, and prints it as LaTeX to copy.
    An empty statement exits.
    """
    nlp = spacy.load(model)
    while statement := click.prompt("Enter your statement", default="", show_default=False).strip():
        doc = nlp(statement)
        to_graph(doc).render("graph", directory=tempfile.gettempdir(), format="svg", view=True, cleanup=True)
        click.echo(f"\n{to_latex(doc)}\n")

if __name__ == '__main__':
    grapher()
