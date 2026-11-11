"""Ephemeral browser admission for the local product server; never persisted or logged."""
from http.cookies import CookieError, SimpleCookie
import secrets


BOOTSTRAP = '''<!doctype html><meta charset="utf-8"><title>Open Cockpit</title>
<p id="status">Opening your local review…</p><script>
(async () => {
  const key = new URLSearchParams(location.hash.slice(1)).get('key');
  history.replaceState(null, '', '/_access');
  if (!key) { document.querySelector('#status').textContent = 'Reopen Cockpit from its launcher.'; return; }
  const response = await fetch('/api/access', {method:'POST', headers:{
    'Content-Type':'application/json', 'Authorization':'Bearer '+key}, body:'{}'});
  if (response.ok) location.replace('/');
  else document.querySelector('#status').textContent = 'Access expired. Reopen Cockpit from its launcher.';
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
