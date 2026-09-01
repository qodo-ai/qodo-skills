/** Render the current immutable release record as GitHub release notes. */
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const catalog = JSON.parse(readFileSync(join(root, 'distribution', 'catalog.json'), 'utf8'));
const version = catalog.package.version;
const release = JSON.parse(readFileSync(join(root, 'releases', `v${version}.json`), 'utf8'));
const lines = [release.summary, '', '## Skills', ''];

if (release.skills.length) {
  for (const skill of release.skills) {
    lines.push(`- \`${skill.name}\` ${skill.version} (${skill.change})`);
  }
} else {
  lines.push('- Marketplace packaging updated; canonical skill bodies are unchanged.');
}

lines.push(
  '',
  '## Runtime compatibility',
  '',
  `Requires Qodo CLI ${release.minimumCliVersion} or newer (runtime protocol ${release.runtimeProtocolVersion}).`,
  'The Qodo CLI is distributed and updated independently from this plugin release.',
  '',
);

const output = `${lines.join('\n')}\n`;
if (process.argv[2]) writeFileSync(process.argv[2], output);
else process.stdout.write(output);
