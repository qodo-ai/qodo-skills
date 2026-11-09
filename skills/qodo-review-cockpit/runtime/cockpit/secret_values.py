"""Redact known scanner secret values before persistence or presentation, not general DLP."""
import re

TEXT_FIELDS = {'body', 'text', 'content', 'patch', 'summary', 'description', 'risk', 'hunks', 'message'}


def known_values(value):
    from .adapters.scanners import _tables, _strip
    values = set()
    def visit(node):
        if isinstance(node, dict):
            if node.get('source') == 'upwind' and (node.get('scanner') or {}).get('kind') == 'secret':
                match = re.search(r'^Upwind flags a value of type .+? \((.*)\)\. A pushed secret', node.get('body') or '')
                if match:
                    values.add(match[1])  # older saved finding bodies
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)
        elif isinstance(node, str) and re.search(r'Upwind Secrets ?Scan', node[:600]):
            for _, rows in _tables(node):
                for row in rows:
                    raw = row.get('Value') or ''
                    values.update([raw, _strip(raw)])
    visit(value)
    return {x for x in values if x and x not in ('masked', '[redacted]', '—')}


def redact(value, values=None):
    values = known_values(value) if values is None else values
    if not values:
        return value
    ordered = sorted(values, key=len, reverse=True)
    def scrub(node, text=False):
        if isinstance(node, dict):
            return {key: scrub(child, text or key in TEXT_FIELDS) for key, child in node.items()}
        if isinstance(node, list):
            return [scrub(child, text) for child in node]
        if isinstance(node, str) and text:
            for secret in ordered:
                node = node.replace(secret, '[redacted]')
        return node
    result = scrub(value)
    if isinstance(result, dict):
        result['source_redactions'] = {'scanner_secret_values': True}
    return result
