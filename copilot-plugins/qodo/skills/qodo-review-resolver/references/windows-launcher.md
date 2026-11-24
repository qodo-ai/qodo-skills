# Windows launcher recovery

Read only when no verified installed native invocation works.

1. Use explicit `QODO_HOME/bin`; otherwise inspect absolute process PATH, Windows user
   PATH (`[Environment]::GetEnvironmentVariable('Path','User')`), then `$HOME/.qodo/bin`.
   Expand variables as data; do not edit PATH or search the workspace.
2. Resolve filesystem links before probing. Require existing, verifiable installation,
   entry point and executable targets outside every repository/workspace directory.
3. Try native `qodo.exe`, then native `node.exe` with the same installed `qodo.mjs`.
   Find Node with `Get-Command node.exe -CommandType Application`, or read existing absolute
   `.exe` paths from that installation's `qodo.cmd` NODE assignments (including conditional
   fallbacks) as text. Never execute `.cmd`, `.bat` or `.ps1` launchers.
4. Run unadorned `--version`; skip rejected/broken choices and keep the first working
   invocation. Unusable explicit `QODO_HOME` or no trusted invocation is a blocker before
   auth/reinstall; a working old version follows the main skill's update gate.

Reuse that invocation, installation and authenticated deployment across commands/tool calls.
