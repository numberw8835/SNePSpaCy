# 🚀 SNePS-Powered Natural Language to Logic Transcription Engine 🧠

This project provides a command-line interface and a Python API to interact with the SNePS (Semantic Network Processing System) knowledge base. It can transcribe natural language into SNePSLOG, assert information into SNePS, and query the knowledge base.

## 📜 Table of Contents

- [Description 📝](#description-)
- [Requirements ⚙️](#requirements-%EF%B8%8F)
- [Installation 🛠️](#installation-%EF%B8%8F)
- [Usage 🚀](#usage-)
  - [Command-Line Interface (CLI) ⌨️](#command-line-interface-cli-%EF%B8%8F)
  - [Direct Access with `PySNePS` 🐍](#direct-access-with-pysneps-)
- [Core Components 🔩](#core-components-)
- [Intellectual Property ©™️](#intellectual-property-%EF%B8%8F)

## Description 📝

This system leverages the SNePS knowledge representation and reasoning system to perform semantic parsing of natural language. The core functionality involves:

* **Natural Language Transcription**: Converting user input into SNePSLOG, a logical representation. This is handled by the `semantic_parser.core.snepslog` class, which utilizes `spaCy` for NLP tasks like root identification and dependency parsing (uploaded:project/nlp_utils/spaCy_helpers.py).
* **SNePS Interaction**: `PySNePS`, SNePS rewritten in Python, runs the knowledge base in-process (project/PySNePS/). It allows for initializing the SNePS environment, informing (asserting) new facts, querying the knowledge base, listing well-formed formulas (wffs), and clearing the knowledge base.
* **Logical Representation**: The `logic_utls.logica.py` module defines classes for representing logical predicates, expressions (atomic and binary), and quantifiers (ForAll, Exists). It includes methods for negation, normalization, and skolemization of logical formulas.
* **Command-Line Interface**: The `main.py` script provides a user-friendly console to interact with the system, offering different modes for API interaction (on/off) and specific commands for managing and querying the SNePS knowledge base.

## Requirements ⚙️

1.  **Python**: Version 3.11.11 🐍
2.  **pip**: Python package installer 📦
3.  **PySNePS**: Version 2.8.0 (Expected to be located in `project/PySNePS/`) 🧠
4.  **Spacy**: NLP library, along with the `en_core_web_trf` model ✨ (uploaded:project/semantic_parser/core.py)

## Installation 🛠️

1.  Ensure Python 3.11.11 and pip are installed on your system.
2.  Install the necessary Python packages using the following command:
    ```bash
    pip install click prompt_toolkit spacy referencing && python -m spacy download en_core_web_trf
    git submodule update --init && pip install -e PySNePS
    ```

## Usage 🚀

### Command-Line Interface (CLI) ⌨️

The primary way to interact with the system is through the `main.py` script.

* **Start the console**:
    ```bash
    python project/main.py [--api-mode on|off]
    ```
    * `--api-mode on` (default): Natural language input will be transcribed and then asserted into the SNePS knowledge base. SNePS commands like `ask`, `list-wffs`, and `clearkb` will interact with the SNePS engine.
    * `--api-mode off`: Natural language input will only be transcribed and displayed. SNePS commands will indicate they are skipped, and no interaction with the SNePS engine will occur.

* **Available Commands within the Console**:
    * `<Natural Language Input>`: Type any natural language sentence. It will be transcribed. If API mode is 'on', it will also be asserted into SNePS.
    * `ask <query>`: Submits a query to the SNePS knowledge base. This command requires API mode to be 'on'. The `<query>` should be in SNePSLOG syntax.
    * `list-wffs`: Lists all well-formed formulas (wffs) currently in the SNePS knowledge base. Requires API mode to be 'on'.
    * `clearkb`: Clears all information from the SNePS knowledge base. Requires API mode to be 'on'.
    * `exit` / `quit` / `Ctrl+C` / `Ctrl+D`: Terminates the console application.
    * `Ctrl+L`: Clears the console screen.

### Direct Access with `PySNePS` 🐍

For more programmatic control or integration into other Python projects, `PySNePS` can be used directly.

* **Import**:
    ```python
    from sneps import Network, SNePSError
    ```
* **Functionality**:
    * Each `Network` is an independent knowledge base, no external process needed.
    * Provides methods like `tell(text)`, `ask(query)`, `askwh(query)` and `node_text(node)`.
    * Raises `SNePSError` for errors signalled by SNePS.
    * See `PySNePS/README.md` for the full API.

## Core Components 🔩

* **`project/main.py`**: The main entry point for the CLI application. It uses the `click` library for command-line argument parsing and `prompt_toolkit` for an enhanced interactive console experience.
* **`project/PySNePS/`**: SNePS 2.8 rewritten in Python, as a git submodule. `main.py` uses its `Network` class to tell, ask, list and clear the knowledge base.
* **`project/semantic_parser/core.py`**: Contains the `snepslog` class responsible for transcribing natural language into SNePSLOG. It utilizes `spacy` for linguistic analysis.
* **`project/logic_utls/logica.py`**: Defines Python classes for representing logical constructs such as predicates (`predicate`), logical expressions (`expression` including binary and atomic forms), and quantifiers (`ForAll`, `Exists`). It provides methods for logical operations like negation and normalization, as well as a function for `intentionalize` to transform universal intentions.
* **`project/nlp_utils/spaCy_helpers.py`**: A suite of helper functions that use `spacy` to analyze tokens from a parsed sentence. Functions include identifying token types (e.g., `is_action`, `is_thing`), dependencies (`get_dependant`), and transforming them into logical components for SNePSLOG using the classes from `logic_utls.logica.py`.

## Intellectual Property ©™️

SNePS is a creation of the SNePS Research Group. All intellectual rights and copyrights pertaining to the SNePS system belong to the SNePS Research Group and the SNePS foundation. We extend our sincere gratitude to the SNePS foundation for their invaluable contribution to the field of knowledge representation and reasoning. (see project/PySNePS/COPYING)
