import click
import os 
# Assuming semantic_parser.core.snepslog is in a location Python can find
from semantic_parser.core import snepslog 

# Assuming sneps_wrapper.sneps_api refers to the sneps_api.py file
from sneps_wrapper.sneps_api import sneps_api, SnepsApiError, SnepsSyntaxError

# For advanced terminal features
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding import KeyBindings
# We'll use the application's renderer directly for clearing.

@click.command()
def console():
    """
    A command-line interface to interact with a SNePS knowledge base.
    You can input natural language, which will be transcribed and asserted.
    Alternatively, use specific commands:
    - ask <query>: Query the knowledge base. E.g., ask member(Fido, Dog)
    - list-wffs: List all well-formed formulas.
    - clearkb: Clears the SNePS knowledge base.
    - exit / quit / Ctrl+C / Ctrl+D: Terminate the console.
    Use Up/Down arrows for command history. Ctrl+L to clear screen.
    """
    engine = None
    try:
        engine = snepslog() # Initialize the semantic parser engine
    except Exception as e:
        click.echo(f"[!!] Failed to initialize semantic parser engine: {e}")
        return 

    api = sneps_api(enable_logging=False) 
    
    # Setup for advanced prompt
    history = InMemoryHistory()
    bindings = KeyBindings()

    @bindings.add('c-l', eager=True) # eager=True helps process the binding quickly
    def _(event):
        """
        Handle Ctrl+L to clear the screen and redraw the prompt.
        """
        # Clear the screen using prompt_toolkit's renderer
        event.app.renderer.clear() 
        
        # Reset the command line interface (this should help redraw the prompt)
        if hasattr(event.app, 'cli') and event.app.cli is not None:
            event.app.cli.reset()
        
        # Invalidate the screen to schedule a redraw
        event.app.invalidate()

    session = PromptSession(history=history, key_bindings=bindings)

    try:
        api.init()
        click.echo("""
╻  ┏━┓┏━╸╻┏━╸┏━┓
┃  ┃ ┃┃╺┓┃┃  ┣━┫
┗━╸┗━┛┗━┛╹┗━╸╹ ╹
        """)
        click.echo("SNePS console initialized. Type 'exit' or 'quit' to leave.")
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
                try:
                    if api.clear_kb():
                        click.echo(f"\n\t<C> Knowledge base cleared.\n") 
                    else:
                        click.echo(f"\n\t<!> Failed to clear knowledge base (API returned false).\n")
                except SnepsApiError as e:
                    click.echo(f"\n\t<!> API Error during 'clearkb': {e}\n")
                except Exception as e:
                    click.echo(f"\n\t<!> Unexpected error during 'clearkb': {e}\n")

            elif user_input_lower.startswith("ask "):
                query = user_input_trimmed[4:].strip() 
                if query:
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
                    except Exception as e: 
                        click.echo(f"\n\t<!> Unexpected error during 'ask': {e}\n")
                else:
                    click.echo(f"\n\t<!> 'ask' command requires a query. Example: ask member(Fido, Dog)\n")

            elif user_input_lower == "list-wffs" or user_input_lower == "list wffs":
                try:
                    wffs = api.list_wffs()
                    if wffs:
                        for wff in wffs:
                            click.echo(f"\n\t<L> {wff}\n") 
                    else:
                        click.echo(f"\n\t<L> No wffs found in the knowledge base.\n") 
                except SnepsApiError as e:
                    click.echo(f"\n\t<!> API Error during 'list-wffs': {e}\n")
                except Exception as e:
                    click.echo(f"\n\t<!> Unexpected error during 'list-wffs': {e}\n")
            
            elif not user_input_trimmed: 
                continue

            else: # Default to inform (SNePS expressions directly)
                try:
                    #TODO: Change it to use engine again
                    results_str = user_input_trimmed 
                    
                    if not results_str: 
                        click.echo("<?> Input is empty.") 
                        continue
                    
                    try:
                        api.inform(results_str)
                        click.echo(f"\n\t<I> {results_str}\n") 
                    except SnepsSyntaxError as e:
                        click.echo(f"\n\t<!> Syntax Error informing '{results_str}': {e}\n")
                    except SnepsApiError as e:
                        click.echo(f"\n\t<!> API Error informing '{results_str}': {e}\n")
                    except Exception as e: 
                        click.echo(f"\n\t<!> Unexpected error informing '{results_str}': {e}\n")

                except Exception as e: 
                    click.echo(f"\t<!> Error processing input: {e}") 

    except SnepsApiError as e: 
        click.echo(f"[!!] A critical SNePS API error occurred: {e}")
    except Exception as e: 
        click.echo(f"[!!] An unexpected critical error occurred: {e}")
    finally:
        if hasattr(api, 'process') and api.process and api.process.isalive():
            api.terminate()
            click.echo("SNePS API terminated.")
        elif hasattr(api, 'process'): 
             click.echo("SNePS API was not running or already terminated.")

if __name__ == '__main__':
    console()
