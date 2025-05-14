import pexpect
import os

class sneps_api:
    
    def __init__(self, directory="Sneps-Linux-Exe-2.7.0"):
        self.current_directory = os.getcwd()
        self.sneps_directory = directory
        self.process = None
    
    def init(self):
        os.chdir(self.sneps_directory)
        self.process = pexpect.spawn("rlwrap sh Sneps-2.7.0.sh")
        self.process.expect("Type")
        self.process.sendline("(snepslog)")
        self.process.expect("Welcome")
        self.process.sendline("clearkb")
        self.process.expect("CPU")

    def inform(self, message):
        self.process.sendline(f"{message}.")
        self.process.expect("CPU")

    def ask(self, message):
        self.process.sendline(f"ask({message}).")
        self.process.expect("CPU")
        answers = self.process.before.decode("utf-8").splitlines()
        result = []
        for ans in answers:
            if "wff" in ans:
                result.append(ans.strip())
        return result
    
    def terminate(self):
        self.process.terminate()
        os.chdir(self.current_directory)