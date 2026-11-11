"""Media references actually rendered by the full app and story layouts."""
from __future__ import annotations


def references(data: dict, *, pairs: bool = True):
    for pr in [None, *data.get('prs', [])]:
        for beat in (data if pr is None else pr).get('story') or []:
            if not isinstance(beat, dict):
                continue
            if beat.get('kind') == 'media':
                yield beat, pr
            elif pairs and beat.get('kind') == 'before_after':
                for key in ('before', 'after'):
                    side = beat.get(key) or {}
                    # Match sideView: a diagram takes precedence over a media field.
                    if isinstance(side, dict) and side.get('media') and not side.get('mermaid'):
                        yield {**beat, 'kind': 'media', 'src': side['media'], 'type': side.get('type')}, pr
