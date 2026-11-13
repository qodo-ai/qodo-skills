"""Ephemeral browser admission for the local product server; never persisted or logged."""
from http.cookies import CookieError, SimpleCookie
import secrets
import threading
import time

INVITE_TTL = 600   # a copied access link works once, within ten minutes


BOOTSTRAP = '''<!doctype html><meta charset="utf-8"><title>Open Agent Session Review</title>
<p id="status">Opening your local review…</p><script>
(async () => {
  const key = new URLSearchParams(location.hash.slice(1)).get('key');
  history.replaceState(null, '', '/_access');
  if (!key) { document.querySelector('#status').textContent = 'Reopen Agent Session Review from its launcher.'; return; }
  const response = await fetch('/api/access', {method:'POST', headers:{
    'Content-Type':'application/json', 'Authorization':'Bearer '+key}, body:'{}'});
  if (response.ok) location.replace('/');
  else document.querySelector('#status').textContent = 'Access expired. Reopen Agent Session Review from its launcher.';
})().catch(() => { document.querySelector('#status').textContent = 'Could not open this local review.'; });
</script>'''


def cookie_name(handler):
    return 'ck_access_' + str(handler.server.server_address[1])


def authorized(handler):
    expected = getattr(handler.server, 'access_key', None)
    if not isinstance(expected, str) or not expected:
        return False
    header = handler.headers.get('Authorization', '')
    supplied = header[7:] if header.startswith('Bearer ') else ''
    if not supplied:
        try:
            cookie = SimpleCookie(handler.headers.get('Cookie') or '').get(cookie_name(handler))
            supplied = cookie.value if cookie else ''
        except CookieError:
            supplied = ''
    return secrets.compare_digest(supplied.encode(), expected.encode())


def mint_invite(server):
    """A one-time key for another browser on this machine; the page never sees the server's own key."""
    key = secrets.token_urlsafe(32)
    with _lock(server):
        invites = getattr(server, 'access_invites', None)
        if invites is None:
            invites = server.access_invites = {}
        now = time.monotonic()
        for k in [k for k, t in invites.items() if t <= now]:
            del invites[k]
        invites[key] = now + INVITE_TTL
    return key


def redeem_invite(handler):
    """Consume a bearer invite: true once, for an unexpired key minted by mint_invite."""
    header = handler.headers.get('Authorization', '')
    supplied = header[7:] if header.startswith('Bearer ') else ''
    if not supplied:
        return False
    with _lock(handler.server):
        invites = getattr(handler.server, 'access_invites', None) or {}
        expires = invites.pop(supplied, None)
    return expires is not None and expires > time.monotonic()


def _lock(server):
    lock = getattr(server, 'access_invites_lock', None)
    if lock is None:
        lock = server.access_invites_lock = threading.Lock()
    return lock
