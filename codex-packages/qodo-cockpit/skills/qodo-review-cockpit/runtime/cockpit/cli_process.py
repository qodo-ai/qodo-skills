"""Invoke the installed CLI without a shell or batch-file argument re-parsing."""
from pathlib import Path
import re
import shutil
import sys


def argv(command):
    command = shutil.which(command) or command
    if sys.platform == 'win32' and Path(command).suffix.lower() in ('.cmd', '.bat'):
        native = Path(command).with_name('qodo.exe')
        if native.is_file():
            return [str(native)]
        # The official script launcher delegates to this adjacent CLI entrypoint.
        # Executing Node directly preserves JSON-file paths containing &, %, spaces or Unicode.
        script = Path(command).with_name('qodo.mjs')
        # Preserve the official launcher's baked Node selection on a minimal-PATH host.
        text = Path(command).read_text(encoding='utf-8', errors='replace')
        candidates = re.findall(r'\bset\s+"NODE=([^"\r\n]+)"', text, re.I)
        candidates = [re.sub(r'%~dp0', lambda _: str(Path(command).parent) + '/', p, flags=re.I)
                      for p in candidates if p.lower() != 'node']
        node = next((p for p in candidates if Path(p).is_file() and Path(p).suffix.lower() not in ('.cmd', '.bat')), None)
        node = node or shutil.which('node')
        if not script.is_file() or not node or Path(node).suffix.lower() in ('.cmd', '.bat'):
            raise FileNotFoundError('Safe Windows CLI invocation needs qodo.exe, or the installed qodo.mjs with its configured Node executable.')
        return [node, str(script)]
    return [str(command)]
