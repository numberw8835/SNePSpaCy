## Installation and Usage - SNePS Goes Brrr! 🚀

### Requirements

1.  Python 3.11.11 - Gotta have that specific flavor! 🐍
2.  pip - Your trusty package installer. 📦
3.  SNePS 2.7.0 - The OG knowledge base, living in `Sneps-Linux-Exe-2.7.0`. 🧠
4.  Spacy + en\_core\_web\_trf - For that sweet NLP magic. ✨

### Installation

1.  Python + pip, the dynamic duo, pre-installed. 🦸‍♂️
2.  One-line package party:

    ```bash
    pip install click prompt_toolkit spacy && python -m spacy download en_core_web_trf
    ```

### Usage

1.  CLI time! ⌨️

    * Fire up SNePS:

        ```bash
        python main.py [--api-mode on|off]
        ```

        * `api-mode on`: SNePS gets interactive! 🗣️
        * `api-mode off`: Just watch the words flow. 📝
    * Talk to SNePS (or watch it think):

        * `ask <query>`: SNePS, spill the beans! (API mode on) ❓
        * `list-wffs`: Show me the knowledge! (API mode on) 📜
        * `clearkb`: Fresh start! (API mode on) 🧹
        * `exit` / `quit` / `Ctrl+C` / `Ctrl+D`: Peace out. ✌️
        * Arrows for history, Ctrl+L for clean screen. 🧙‍♂️

2.  **`sneps_api.py` Direct Access!** 🐍

    * For low-level SNePS control, import and use `sneps_api.py` in your Python scripts.
    * It handles SNePS process spawning and communication via `pexpect`.
    * Perfect for automation or custom integrations! 🤖

### Intellectual Property

SNePS is a creation of the SNePS Research Group. All intellectual rights and copyrights pertaining to the SNePS system belong to the SNePS Research Group and the SNePS foundation. We extend our sincere gratitude to the SNePS foundation for their invaluable contribution to the field of knowledge representation and reasoning.
