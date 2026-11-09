"""Invoke the installed CLI without a shell or batch-file argument re-parsing."""
from pathlib import Path
import shutil
import sys


def argv(command):
    command = shutil.which(command) or command
    if sys.platform == 'win32' and Path(command).suffix.lower() in ('.cmd', '.bat'):
        # The official script launcher delegates to this adjacent CLI entrypoint.
        # Executing Node directly preserves JSON-file paths containing &, %, spaces or Unicode.
        script = Path(command).with_name('qodo.mjs')
        node = shutil.which('node')
        if not script.is_file() or not node or Path(node).suffix.lower() in ('.cmd', '.bat'):
            raise FileNotFoundError('Safe Windows CLI invocation needs qodo.exe, or the installed qodo.mjs with Node on PATH.')
        return [node, str(script)]
    return [str(command)]
