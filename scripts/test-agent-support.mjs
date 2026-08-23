/** Verify the observed-agent contract and project the direct bundle into isolated roots. */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const contract = JSON.parse(readFileSync(join(root, 'distribution', 'agent-support.json'), 'utf8'));
const catalog = JSON.parse(readFileSync(join(root, 'distribution', 'catalog.json'), 'utf8'));
const bundle = JSON.parse(readFileSync(join(root, 'distribution', 'qodo-skills-direct.json'), 'utf8'));
const expectedObservedIds = [
  'claude',
  'claude-code',
  'codex',
  'cursor-cli',
  'github-copilot-app',
  'github-copilot-vscode',
  'hermes',
  'kiro',
  'opencode',
  'replit',
];
const expectedAgentFields = [
  'artifact',
  'delivery',
  'displayName',
  'id',
  'nativeAcceptanceRequired',
  'observedHostAgentIds',
  'supportTier',
];

assert.equal(contract.schemaVersion, 1);
assert.equal(contract.evidence.event, 'tool_run_started');
assert.equal(contract.evidence.property, 'host_agent');
assert.match(contract.evidence.snapshotDate, /^\d{4}-\d{2}-\d{2}$/);

const agentIds = contract.agents.map((agent) => agent.id);
assert.equal(new Set(agentIds).size, agentIds.length, 'agent IDs must be unique');
const observedIds = contract.agents
  .flatMap((agent) => agent.observedHostAgentIds)
  .sort();
assert.deepEqual(observedIds, expectedObservedIds, 'observed production identities must be covered');
assert.equal(new Set(observedIds).size, observedIds.length, 'runtime identities must map once');

const catalogSkillNames = catalog.skills.map((skill) => skill.name).sort();
const bundleSkillNames = bundle.skills.map((skill) => skill.name).sort();
assert.deepEqual(bundleSkillNames, catalogSkillNames, 'direct bundle must contain every canonical skill');

for (const agent of contract.agents) {
  assert.deepEqual(Object.keys(agent).sort(), expectedAgentFields);
  assert.match(agent.id, /^[a-z0-9-]+$/);
  assert.ok(agent.displayName.trim());
  assert.ok(agent.observedHostAgentIds.length > 0);
  assert.ok(['marketplace', 'direct'].includes(agent.delivery));
  assert.ok(['package-ready', 'validated', 'listed'].includes(agent.supportTier));
  if (agent.supportTier === 'package-ready') assert.equal(agent.nativeAcceptanceRequired, true);
  assert.ok(existsSync(join(root, agent.artifact)), `${agent.displayName}: artifact is missing`);
}

for (const agent of contract.agents.filter((entry) => entry.delivery === 'direct')) {
  assert.equal(agent.artifact, 'distribution/qodo-skills-direct.json');
  const targetRoot = mkdtempSync(join(tmpdir(), `qodo-${agent.id}-`));
  try {
    for (const skill of bundle.skills) {
      for (const file of skill.files) {
        assert.ok(!file.path.includes('..') && !file.path.startsWith('/'));
        const target = join(targetRoot, skill.name, file.path);
        mkdirSync(dirname(target), { recursive: true });
        writeFileSync(target, file.content);
        assert.equal(
          createHash('sha256').update(readFileSync(target)).digest('hex'),
          file.sha256,
          `${agent.displayName}: ${skill.name}/${file.path} changed during projection`,
        );
      }
      const skillText = readFileSync(join(targetRoot, skill.name, 'SKILL.md'), 'utf8');
      assert.match(skillText, new RegExp(`^---[\\s\\S]*?^name: ${skill.name}$`, 'm'));
    }
  } finally {
    rmSync(targetRoot, { recursive: true, force: true });
  }
}

console.log(
  `Validated ${contract.agents.length} observed agents, including ${contract.agents.filter((agent) => agent.delivery === 'direct').length} direct-connect projections.`,
);
