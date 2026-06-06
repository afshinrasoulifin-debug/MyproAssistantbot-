

import subprocess
from pathlib import Path
from typing import List
from arki_project.exceptions import HandlerError

class VictorTools:
    """
    Singularity Toolset: From Python to Binary Level.
    """
    def __init__(self):
        self.base_dir = Path("/home/ubuntu/arki_v29_typed")

    async def compile_tool(self, code: str, tool_name: str) -> str:
        """Writes and compiles C code for high-performance tasks."""
        c_file = self.base_dir / f"{tool_name}.c"
        out_file = self.base_dir / tool_name
        
        c_file.write_text(code)
        try:
            subprocess.run(["gcc", str(c_file), "-o", str(out_file)], check=True)
            return f"Tool {tool_name} compiled successfully."
        except HandlerError as e:
            return f"Compilation failed: {e}"

    async def execute_binary(self, tool_name: str, args: List[str]) -> str:
        """Executes a compiled binary tool."""
        bin_path = self.base_dir / tool_name
        if not bin_path.exists(): return "Binary not found."
        
        try:
            result = subprocess.check_output([str(bin_path)] + args).decode()
            return result
        except HandlerError as e:
            return str(e)
            
    async def system_resources(self):
        import psutil
        return psutil.cpu_percent()


