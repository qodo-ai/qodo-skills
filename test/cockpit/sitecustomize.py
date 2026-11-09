"""Test-process guards only; this directory is never part of an installed Cockpit skill."""
import os
import sys

if os.environ.get('COCKPIT_TEST_ISOLATED') == '1':
    import pathlib
    import shutil

    def _audit(event, args):
        if event in ('socket.connect', 'socket.bind', 'socket.getaddrinfo'):
            if os.environ.get('COCKPIT_TEST_OFFLINE') == '1':
                raise RuntimeError('Cockpit suite offline mode blocks socket operations; parent full run required')
            address = args[0] if event == 'socket.getaddrinfo' else args[1]
            host = address[0] if isinstance(address, tuple) else address
            if host not in ('localhost', '127.0.0.1', '::1'):
                raise RuntimeError('Cockpit suite blocks non-loopback network operations')
        if event != 'subprocess.Popen':
            return
        command = str(args[0])
        name = pathlib.Path(command).name.lower().removesuffix('.exe').removesuffix('.cmd')
        if name == 'git' and os.environ.get('COCKPIT_TEST_OFFLINE') == '1':
            raise RuntimeError('Cockpit suite offline mode blocks real Git operations; parent full run required')
        if name in ('gh', 'qodo'):
            selected = shutil.which(command) or command
            allowed = pathlib.Path(os.environ['COCKPIT_TEST_FIXTURE_BIN']).resolve()
            if pathlib.Path(selected).resolve().parent != allowed:
                raise RuntimeError('Cockpit suite blocks real provider CLI operations; use a fixture')

    sys.addaudithook(_audit)
