import logging
import os
import re

import pexpect

logger = logging.getLogger(__name__)

# The bundled SNePS build, found relative to this file so the wrapper works from any directory.
DEFAULT_DIRECTORY = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Sneps-Linux-Exe-2.7.0")

# What SNePS 2.7 prints, as observed with the bundled Linux build:
_DONE = r"CPU time : [\d.]+"           # after every SNePSLOG command
_PROMPT = r"\r\n: "                     # the SNePSLOG prompt that follows it
_RESTARTS = r"Restart actions"          # Allegro's restart menu, shown after a rejected command
_DEBUG_PROMPT = r"\] snepslog\(\d+\): "  # the debugger prompt that follows the menu
_CONTINUE = re.compile(r"(\d+): Continue with SNePSLOG")
_WFF = re.compile(r"^\s*wff\d+!:\s*(.*?)\s*$", re.IGNORECASE)


class SnepsApiError(Exception):
    """Custom exception class for SNePS API errors."""
    pass

class SnepsProcessError(SnepsApiError):
    """Raised when there's an error interacting with the SNePS process."""
    pass

class SnepsSyntaxError(SnepsApiError):
    """Raised for SNePS syntax errors."""
    pass

class SnepsInitializationError(SnepsApiError):
    """Raised when SNePS initialization fails."""
    pass


def _balanced(text):
    depth = {"(": 0, "{": 0}
    for ch in text:
        if ch in "({":
            depth[ch] += 1
        elif ch in ")}":
            depth["(" if ch == ")" else "{"] -= 1
            if min(depth.values()) < 0:
                return False
    return not any(depth.values())


def _error_text(output):
    """The message SNePS printed after 'Error:', on one line."""
    match = re.search(r"error:?\s*(.*)", output, re.IGNORECASE | re.DOTALL)
    return " ".join((match.group(1) if match else output).split())


def _wffs(output):
    """The formulas in SNePS output lines such as 'wff3!:  a(b)' (either case)."""
    return [m.group(1) for m in map(_WFF.match, output.splitlines()) if m]


class sneps_api:
    def __init__(self, directory=DEFAULT_DIRECTORY, enable_logging=True, timeout=30):
        """`directory` is the SNePS folder containing Sneps-2.7.0.sh. `timeout` is how many seconds
        each SNePS command may take; inference over a large knowledge base can need more than 30."""
        self.sneps_directory = os.path.abspath(directory)
        self.process = None
        self.logging_enabled = enable_logging
        self.timeout = timeout

        if not os.path.isdir(self.sneps_directory):
            raise SnepsInitializationError(f"SNePS directory not found: {self.sneps_directory}")
        if not os.path.isfile(os.path.join(self.sneps_directory, "Sneps-2.7.0.sh")):
            raise SnepsInitializationError(f"Sneps-2.7.0.sh not found in {self.sneps_directory}")

    def _log(self, level, message):
        # Logging goes to this module's logger; configuring handlers is up to the application.
        if self.logging_enabled:
            logger.log(level, message)

    def __enter__(self):
        if self.process is None or not self.process.isalive():
            self.init()
        return self

    def __exit__(self, *exc):
        self.terminate()

    def init(self):
        try:
            self.process = pexpect.spawn("sh Sneps-2.7.0.sh", cwd=self.sneps_directory, timeout=self.timeout,
                                         encoding="utf-8", codec_errors="replace")
            self.process.expect("Type")
            self.process.sendline("(snepslog)")
            self.process.expect("Welcome")
            self.process.expect(_PROMPT)
            self._log(logging.INFO, "SNePSLOG started.")
            self.clear_kb()
        except (pexpect.exceptions.TIMEOUT, pexpect.exceptions.EOF, OSError, SnepsApiError) as e:
            output = self.process.before if self.process is not None and isinstance(self.process.before, str) else ""
            self._safe_terminate_process()
            raise SnepsInitializationError(f"SNePS did not start: {e}. Output: {output[-500:]}") from e

    def _ensure_process_is_alive(self):
        """Checks if the SNePS process is alive."""
        if self.process is None or not self.process.isalive():
            raise SnepsProcessError("SNePS process is not running. Please call init() first.")

    def _command(self, line):
        """Send one SNePSLOG command and return what it printed.

        If SNePS rejects the command, SNePS is returned to the SNePSLOG prompt and SnepsSyntaxError
        carries SNePS's own message. If SNePS does not answer in time or exits, the process is shut
        down (its output would no longer line up with the commands) and SnepsProcessError is raised.
        """
        self._ensure_process_is_alive()
        try:
            self.process.sendline(line)
            if self.process.expect([_DONE, _RESTARTS]) == 0:
                output = self.process.before
                self.process.expect(_PROMPT)
                return output
            message = _error_text(self.process.before)
            self.process.expect(_DEBUG_PROMPT)
            restart = _CONTINUE.search(self.process.before)
            if restart is None:
                raise SnepsProcessError(f"SNePS failed on {line!r} and cannot continue: {message}")
            self.process.sendline(f":continue {restart.group(1)}")
            self.process.expect(_DONE)
            self.process.expect(_PROMPT)
            self._log(logging.WARNING, f"SNePS rejected {line!r}: {message}")
            raise SnepsSyntaxError(f"SNePS Error: {message} (input: {line})")
        except pexpect.exceptions.TIMEOUT as e:
            self._safe_terminate_process()
            raise SnepsProcessError(f"SNePS did not answer {line!r} within {self.timeout} s; "
                                    f"the process was stopped, call init() to start again") from e
        except pexpect.exceptions.EOF as e:
            self._safe_terminate_process()
            raise SnepsProcessError(f"SNePS exited while running {line!r}") from e

    def clear_kb(self):
        """Sends the 'clearkb' command to SNePS."""
        self._command("clearkb")
        self._log(logging.INFO, "Knowledge base cleared.")
        return True

    def inform(self, message):
        """Assert one SNePSLOG statement. A final '.' (or '!') is added if missing."""
        statement = message.strip() if isinstance(message, str) else ""
        if not statement:
            raise ValueError("Inform message cannot be empty.")
        if "\n" in statement or "\r" in statement:
            raise SnepsSyntaxError(f"A statement must be on one line: {statement!r}")
        if not _balanced(statement):
            # SNePS would wait for the rest of the statement and swallow the next command.
            raise SnepsSyntaxError(f"Unbalanced brackets, not sent to SNePS: {statement!r}")
        if not statement.endswith((".", "!")):
            statement += "."
        self._command(statement)
        self._log(logging.INFO, f"Informed: {statement}")
        return True

    def list_wffs(self):
        result = _wffs(self._command("list-wffs"))
        self._log(logging.INFO, f"list_wffs returned {len(result)} items.")
        return result

    def ask(self, message):
        query = message.strip().rstrip(".?").strip() if isinstance(message, str) else ""
        if not query:
            return []
        if not _balanced(query):
            raise SnepsSyntaxError(f"Unbalanced brackets, not sent to SNePS: {query!r}")
        result = _wffs(self._command(f"ask({query})."))
        self._log(logging.INFO, f"ask({query}) returned {len(result)} items.")
        return result

    def _safe_terminate_process(self):
        """Safely terminates the SNePS process if it's running."""
        if self.process is not None and self.process.isalive():
            try:
                self.process.terminate(force=True)
            except Exception as e:
                self._log(logging.WARNING, f"Error while terminating SNePS process: {e}")
        self.process = None

    def terminate(self):
        self._log(logging.INFO, "Terminating SNePS API session.")
        self._safe_terminate_process()
