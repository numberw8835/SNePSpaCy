import click
import os
import traceback
# Assuming semantic_parser.core.snepslog is in a location Python can find
from semantic_parser.core import snepslog

from sneps import Network, SNePSError

# For advanced terminal features
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
# We'll use the application's renderer directly for clearing.

@click.command()
@click.option('--api-mode', type=click.Choice(['on', 'off']), default='on', help="API mode: 'on' to interact with SNePS, 'off' to only transcribe/show and skip API calls.")
def console(api_mode):
    """
    A command-line interface to interact with a SNePS knowledge base.
    You can input natural language, which will be transcribed and asserted (if API mode is 'on').
    Questions (ending in '?') are transcribed and asked instead.
    Alternatively, use specific commands (behavior depends on API mode):
    - ask <query>: Query the knowledge base.
    - list-wffs: List all well-formed formulas.
    - clearkb: Clears the SNePS knowledge base.
    - exit / quit / Ctrl+C / Ctrl+D: Terminate the console.
    Use Up/Down arrows for command history. Ctrl+L to clear screen.
    """
    engine = None
    try:
        engine = snepslog() # Initialize the semantic parser engine
    except Exception:
        click.echo(f"[!!] Failed to initialize semantic parser engine:")
        traceback.print_exc()
        return

    net = None

    # Setup for advanced prompt
    history = InMemoryHistory()
    bindings = KeyBindings()

    @bindings.add('c-l', eager=True)
    def _(event):
        event.app.renderer.clear()
        if hasattr(event.app, 'cli') and event.app.cli is not None:
            event.app.cli.reset()
        event.app.invalidate()

    session = PromptSession(history=history, key_bindings=bindings)

    try:
        if api_mode == 'on':
            net = Network(output=False) # Initialize SNePS only if mode is 'on'
            click.echo("SNePS API initialized.")
        else:
            click.echo("SNePS API mode is OFF. API will not be initialized or called.")

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

            user_input_trimmed = user_input.strip()
            user_input_lower = user_input_trimmed.lower()

            if user_input_lower in ['exit', 'quit']:
                click.echo("Exiting SNePS console...")
                break

            elif user_input_lower == "clearkb":
                if api_mode == 'on':
                    try:
                        net.tell("clearkb")
                        engine.forget()
                        click.echo(f"\n\t<C> Knowledge base cleared.\n")
                    except SNePSError as e:
                        click.echo(f"\n\t<!> SNePS Error during 'clearkb': {e}\n")
                    except Exception:
                        click.echo(f"\n\t<!> An unexpected error occurred during 'clearkb':\n")
                        traceback.print_exc()
                else:
                    click.echo(f"\n\t<API OFF> 'clearkb' command skipped.\n")

            # Fixed section for 'ask' command
            elif user_input_lower == "ask": # Handles 'ask' typed alone
                click.echo(f"\n\t<!> 'ask' command requires a query. Example: ask member(Fido, Dog)\n")

            elif user_input_lower.startswith("ask "): # Handles 'ask ' followed by a query or nothing
                query = user_input_trimmed[4:].strip()
                if query:
                    if api_mode == 'on':
                        try:
                            answers = [net.node_text(node) for node in net.ask(query)]
                            if answers:
                                for ans in answers:
                                    click.echo(f"\n\t<A> {ans}\n")
                            else:
                                click.echo(f"\n\t<A> No answer found or query did not produce assertional wffs.\n")
                        except SNePSError as e:
                            click.echo(f"\n\t<!> SNePS Error: {e}\n")
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
                        wffs = [net.node_text(node) for node in net.all_nodes() if node.asupport]
                        if wffs:
                            for wff in wffs:
                                click.echo(f"\n\t<L> {wff}\n")
                        else:
                            click.echo(f"\n\t<L> No wffs found in the knowledge base.\n")
                    except SNePSError as e:
                        click.echo(f"\n\t<!> SNePS Error during 'list-wffs': {e}\n")
                    except Exception:
                        click.echo(f"\n\t<!> An unexpected error occurred during 'list-wffs':\n")
                        traceback.print_exc()
                else:
                    click.echo(f"\n\t<API OFF> 'list-wffs' command skipped.\n")

            elif not user_input_trimmed:
                continue

            else: # Default to transcribe, and inform if API mode is 'on'
                try:
                    results_str = engine.transcribe(user_input_trimmed) # Transcription always happens

                    if not results_str:
                        click.echo("\n\t<?> Input is empty or transcription failed.\n")
                        continue
                    
                    click.echo(f"\n\t<T> Transcribed/Parsed: {results_str}\n") # Always show transcribed/parsed

                    if api_mode == 'on':
                        try:
                            if user_input_trimmed.endswith("?"):
                                answers = [net.node_text(node) for node in net.ask(results_str)]
                                if answers:
                                    for ans in answers:
                                        click.echo(f"\n\t<A> {ans}\n")
                                else:
                                    click.echo(f"\n\t<A> No answer found.\n")
                            else:
                                net.tell(f"{results_str}!") # '!' also infers forward, so rules use facts told after a question
                                click.echo(f"\n\t<I> Informed SNePS with: {results_str}\n")
                        except SNePSError as e:
                            click.echo(f"\n\t<!> SNePS Error informing '{results_str}': {e}\n")
                        except Exception:
                            click.echo(f"\n\t<!> An unexpected error occurred while informing SNePS:\n")
                            traceback.print_exc()
                    else:
                        click.echo(f"\t<API OFF> SNePS not informed.\n")

                except Exception:
                    click.echo(f"\t<!> An error occurred processing the input:\n")
                    traceback.print_exc()

    except SNePSError as e:
        if api_mode == 'on': # Only relevant if we tried to use the API
            click.echo(f"[!!] A critical SNePS error occurred: {e}")
            traceback.print_exc()
    except Exception:
        click.echo(f"[!!] An unexpected critical error occurred:")
        traceback.print_exc()

if __name__ == '__main__':
    console()