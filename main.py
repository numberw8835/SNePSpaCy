import sys
import traceback
import warnings

import click
from semantic_parser.core import snepslog
from sneps_wrapper.sneps_api import sneps_api, SnepsApiError, SnepsSyntaxError, DEFAULT_DIRECTORY
from nlp_utils.spaCy_helpers import TranscriptionWarning


def handle(user_input, engine, api, api_mode):
    """Run one console command or sentence. Returns False when the user asked to exit."""
    user_input_trimmed = user_input.strip()
    user_input_lower = user_input_trimmed.lower()

    if user_input_lower in ['exit', 'quit']:
        click.echo("Exiting SNePS console...")
        return False

    elif user_input_lower == "clearkb":
        if api_mode == 'on':
            try:
                if api.clear_kb():
                    click.echo(f"\n\t<C> Knowledge base cleared.\n")
                else:
                    click.echo(f"\n\t<!> Failed to clear knowledge base (API returned false).\n")
            except SnepsApiError as e:
                click.echo(f"\n\t<!> API Error during 'clearkb': {e}\n")
            except Exception:
                click.echo(f"\n\t<!> An unexpected error occurred during 'clearkb':\n")
                traceback.print_exc()
        else:
            click.echo(f"\n\t<API OFF> 'clearkb' command skipped.\n")

    elif user_input_lower == "ask": # Handles 'ask' typed alone
        click.echo(f"\n\t<!> 'ask' command requires a query. Example: ask member(Fido, Dog)\n")

    elif user_input_lower.startswith("ask "): # Handles 'ask ' followed by a query or nothing
        query = user_input_trimmed[4:].strip()
        if query:
            if api_mode == 'on':
                try:
                    answers = api.ask(query)
                    if answers:
                        for ans in answers:
                            click.echo(f"\n\t<A> {ans}\n")
                    else:
                        click.echo(f"\n\t<A> No answer found or query did not produce assertional wffs.\n")
                except SnepsSyntaxError as e:
                    click.echo(f"\n\t<!> Syntax Error: {e}\n")
                except SnepsApiError as e:
                    click.echo(f"\n\t<!> API Error: {e}\n")
                except Exception:
                    click.echo(f"\n\t<!> An unexpected error occurred during 'ask':\n")
                    traceback.print_exc()
            else:
                click.echo(f"\n\t<API OFF> 'ask {query}' command skipped. Parsed query would be: {query}\n")
        else: # Handles 'ask ' followed by only spaces
            click.echo(f"\n\t<!> 'ask' command requires a query. Example: ask member(Fido, Dog)\n")

    elif user_input_lower == "list-wffs" or user_input_lower == "list wffs":
        if api_mode == 'on':
            try:
                wffs = api.list_wffs()
                if wffs:
                    for wff in wffs:
                        click.echo(f"\n\t<L> {wff}\n")
                else:
                    click.echo(f"\n\t<L> No wffs found in the knowledge base.\n")
            except SnepsApiError as e:
                click.echo(f"\n\t<!> API Error during 'list-wffs': {e}\n")
            except Exception:
                click.echo(f"\n\t<!> An unexpected error occurred during 'list-wffs':\n")
                traceback.print_exc()
        else:
            click.echo(f"\n\t<API OFF> 'list-wffs' command skipped.\n")

    elif not user_input_trimmed:
        pass

    else: # Default to transcribe, and inform if API mode is 'on'
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", TranscriptionWarning)
                results_str = engine.transcribe(user_input_trimmed) # Transcription always happens
            for warning in caught:
                if issubclass(warning.category, TranscriptionWarning):
                    click.echo(f"\t<W> {warning.message}")
                else:
                    warnings.warn_explicit(warning.message, warning.category, warning.filename, warning.lineno)

            if not results_str:
                click.echo("\n\t<?> Input is empty or transcription failed.\n")
                return True

            click.echo(f"\n\t<T> Transcribed/Parsed: {results_str}\n") # Always show transcribed/parsed

            if api_mode == 'on':
                try:
                    api.inform(results_str)
                    click.echo(f"\n\t<I> Informed SNePS with: {results_str}\n")
                except SnepsSyntaxError as e:
                    click.echo(f"\n\t<!> Syntax Error informing '{results_str}': {e}\n")
                except SnepsApiError as e:
                    click.echo(f"\n\t<!> API Error informing '{results_str}': {e}\n")
                except Exception:
                    click.echo(f"\n\t<!> An unexpected error occurred while informing SNePS:\n")
                    traceback.print_exc()
            else:
                click.echo(f"\t<API OFF> SNePS not informed.\n")

        except Exception:
            click.echo(f"\t<!> An error occurred processing the input:\n")
            traceback.print_exc()

    return True


def interactive(engine, api, api_mode):
    # For advanced terminal features (only needed in an interactive terminal)
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.key_binding import KeyBindings

    history = InMemoryHistory()
    bindings = KeyBindings()

    @bindings.add('c-l', eager=True)
    def _(event):
        event.app.renderer.clear()
        if hasattr(event.app, 'cli') and event.app.cli is not None:
            event.app.cli.reset()
        event.app.invalidate()

    session = PromptSession(history=history, key_bindings=bindings)

    click.echo("""
┏━┓┏┓╻┏━╸┏━┓┏━┓┏━┓┏━┓┏━╸╻ ╻
┗━┓┃┗┫┣╸ ┣━┛┗━┓┣━┛┣━┫┃  ┗┳┛
┗━┛╹ ╹┗━╸╹  ┗━┛╹  ╹ ╹┗━╸ ╹
    """)
    click.echo(f"SNePS console started. API Mode: {api_mode.upper()}. Type 'exit' or 'quit' to leave.")
    click.echo("Commands: ask <query>, list-wffs, clearkb, or (Natural Language).")
    click.echo("Use Up/Down for history, Ctrl+L to clear screen.\n")

    while True:
        try:
            user_input = session.prompt("//: ")
        except KeyboardInterrupt:
            click.echo("\nExiting SNePS console (Ctrl+C)...")
            break
        except EOFError:
            click.echo("Exiting SNePS console (Ctrl+D)...")
            break
        if not handle(user_input, engine, api, api_mode):
            break


def batch(lines, engine, api, api_mode):
    """Run one command or sentence per line; blank lines and lines starting with '#' are skipped."""
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        click.echo(f"//: {line}")
        if not handle(line, engine, api, api_mode):
            break


@click.command()
@click.option('--api-mode', type=click.Choice(['on', 'off']), default='on', help="API mode: 'on' to interact with SNePS, 'off' to only transcribe/show and skip API calls.")
@click.option('--file', 'input_file', type=click.File('r', encoding='utf-8'), default=None,
              help="Read commands and sentences from this file (one per line) instead of the prompt.")
@click.option('--sneps-dir', type=click.Path(exists=True, file_okay=False), default=DEFAULT_DIRECTORY,
              show_default=True, help="Folder containing Sneps-2.7.0.sh.")
@click.option('--timeout', type=int, default=30, show_default=True, help="Seconds each SNePS command may take.")
def console(api_mode, input_file, sneps_dir, timeout):
    """
    A command-line interface to interact with a SNePS knowledge base.
    You can input natural language, which will be transcribed and asserted (if API mode is 'on').
    Alternatively, use specific commands (behavior depends on API mode):
    - ask <query>: Query the knowledge base.
    - list-wffs: List all well-formed formulas.
    - clearkb: Clears the SNePS knowledge base.
    - exit / quit / Ctrl+C / Ctrl+D: Terminate the console.
    Use Up/Down arrows for command history. Ctrl+L to clear screen.
    With --file, or when input is piped or redirected, lines are read without the prompt.
    """
    engine = None
    try:
        engine = snepslog() # Initialize the semantic parser engine
    except Exception:
        click.echo(f"[!!] Failed to initialize semantic parser engine:")
        traceback.print_exc()
        return

    api = None
    try:
        if api_mode == 'on':
            api = sneps_api(directory=sneps_dir, enable_logging=False, timeout=timeout)
            api.init() # Initialize SNePS API only if mode is 'on'
            click.echo("SNePS API initialized.")
        else:
            click.echo("SNePS API mode is OFF. API will not be initialized or called.")

        if input_file is not None:
            batch(input_file, engine, api, api_mode)
        elif not sys.stdin.isatty():
            batch(sys.stdin, engine, api, api_mode)
        else:
            interactive(engine, api, api_mode)

    except SnepsApiError as e:
        click.echo(f"[!!] A critical SNePS API error occurred: {e}")
        traceback.print_exc()
    except Exception:
        click.echo(f"[!!] An unexpected critical error occurred:")
        traceback.print_exc()
    finally:
        if api is not None and api.process is not None and api.process.isalive():
            api.terminate()
            click.echo("SNePS API terminated.")

if __name__ == '__main__':
    console()
