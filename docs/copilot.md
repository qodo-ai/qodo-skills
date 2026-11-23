# GitHub Copilot

Qodo provides setup, codebase intelligence, and code review skills in the `qodo` plugin.
`qodo-standards` adds rules discovery and standards administration as an optional install.
Install the [Qodo CLI](../skills/qodo-setup/references/runtime.md) separately. The CLI owns authentication and tool execution. The plugins package skills and
their references. Copilot owns plugin installation, updates, and removal.

## Install from the Qodo marketplace

Use a [Qodo Skills release](https://github.com/qodo-ai/qodo-skills/releases) that contains
`.github/plugin/marketplace.json` and `copilot-plugins/`. To try an unreleased change, use
a disposable checkout, run `npm run adapters` there, and add that local marketplace instead.

### Copilot CLI

```sh
copilot plugin marketplace add qodo-ai/qodo-skills
copilot plugin install qodo@qodo-copilot
# Optional
copilot plugin install qodo-standards@qodo-copilot
```

Start a new session and open `/skills list` to confirm discovery. Run the `qodo-setup`
skill to connect and verify Qodo. To update or remove the core plugin, use
`copilot plugin update qodo@qodo-copilot` or `copilot plugin uninstall qodo@qodo-copilot`.
Use `qodo-standards@qodo-copilot` to manage Standards separately.
See [Copilot CLI plugin commands](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-finding-installing).

### VS Code

Enable agent plugins in Copilot, then add `qodo-ai/qodo-skills` to the agent plugin
marketplaces in Settings. To select a release, use `qodo-ai/qodo-skills#<release-tag>`.
In the Copilot harness, open the plugin marketplace and install **qodo**. Install
**qodo-standards** separately if needed. Enable the plugin if prompted, then open a new
Copilot session and invoke `/qodo:qodo-setup`. Use the same plugin manager to update
or uninstall. For a disposable local build, add its `file:///` marketplace URI or use
**Install Plugin from Source** and select `copilot-plugins/qodo`.
See [VS Code agent plugins](https://code.visualstudio.com/docs/agent-customization/agent-plugins)
and [marketplace source formats](https://code.visualstudio.com/docs/agents/reference/agent-plugin-reference#marketplace-source-formats).

## Submit to Awesome Copilot

After the protected Qodo Skills release publishes, use the
[Awesome Copilot external plugin form](https://github.com/github/awesome-copilot/issues/new/choose).
Submit `qodo` from `qodo-ai/qodo-skills`, path `copilot-plugins/qodo`. Use the public
release tag, its full commit SHA, and the version in that tag's `plugin.json`. Copy the
description, author, homepage, license, and keywords from the same manifest. The intake
runs manifest validation, Vally skill lint, and a Copilot CLI marketplace install before
maintainer review. See the [external plugin contribution guide](https://github.com/github/awesome-copilot/blob/main/CONTRIBUTING.md#adding-external-plugins).
