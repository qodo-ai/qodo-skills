"""HTTP session switching keeps product boundaries local or explicitly server-wide."""
import json
import os
import tempfile
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from cockpit import product, server, util


class ProductSessionHTTPTests(unittest.TestCase):
    def test_multi_session_notes_and_publish_preserve_explicit_server_boundary(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {'REVIEW_COCKPIT_PRODUCT':'0'}):
            root=Path(tmp)
            cfg=util.load_config();cfg['memory']['enabled']=False
            for name in ('legacy','managed'):
                sd=root/name;sd.mkdir()
                data={'session':name,'product':name=='managed','prs':[{'key':'org/repo#1','repo':'org/repo','number':1,'title':'Change'}]}
                (sd/'review-data.json').write_text(json.dumps(data));(sd/'events.jsonl').write_text('')
            with mock.patch.object(server,'SESSIONS',root), mock.patch.object(server.Handler,'sdir',root/'legacy',create=True), mock.patch.object(server.Handler,'cfg',cfg,create=True):
                for explicit in (False,True):
                    with self.subTest(explicit_product_server=explicit):
                        httpd=ThreadingHTTPServer(('127.0.0.1',0),server.Handler);httpd.product=explicit
                        thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
                        url='http://127.0.0.1:'+str(httpd.server_address[1])
                        def request(path,name,body=None):
                            headers={'X-Cockpit-Session':name}
                            if body is not None:headers['Content-Type']='application/json'
                            req=urllib.request.Request(url+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)
                            with urllib.request.urlopen(req) as response:return json.loads(response.read())
                        try:
                            self.assertEqual(bool(request('/api/data','legacy').get('product')),explicit)
                            self.assertTrue(request('/api/data','managed')['product'])
                            with mock.patch.object(server.threads,'fetch',return_value=[]) as preflight, mock.patch.object(server,'build_review',return_value=({},['note'],[])) as preview:
                                for dry in (True,False):
                                    self.assertFalse(request('/api/publish','managed',{'pr':'org/repo#1','dry_run':dry})['provider_writes'])
                                preflight.assert_not_called();preview.assert_not_called()
                                self.assertEqual(bool(request('/api/data','legacy').get('product')),explicit)
                                result=request('/api/publish','legacy',{'pr':'org/repo#1','dry_run':True})
                                if explicit:
                                    self.assertFalse(result['provider_writes']);preflight.assert_not_called();preview.assert_not_called()
                                else:
                                    self.assertTrue(result['dry_run']);self.assertEqual(preflight.call_count,1);self.assertEqual(preview.call_count,1)
                            for name in ('managed','legacy'):
                                request('/api/event',name,{'type':'note','pr':'org/repo#1','note_id':'n','post':True,'text':'reader'})
                                event=json.loads((root/name/'events.jsonl').read_text().splitlines()[-1])
                                self.assertEqual(event['post'],not (explicit or name=='managed'))
                            self.assertEqual(os.environ['REVIEW_COCKPIT_PRODUCT'],'0');self.assertFalse(product.enabled())
                        finally:
                            httpd.shutdown();httpd.server_close();thread.join(timeout=2)

    def test_product_get_origin_guard_precedes_payload_and_resource_routes(self):
        from cockpit.adapters.managed import Client
        with tempfile.TemporaryDirectory() as tmp,mock.patch.dict(os.environ,{'REVIEW_COCKPIT_PRODUCT':'0'}):
            root=Path(tmp);cfg=util.load_config();cfg['memory']['enabled']=False
            for name in ('legacy','managed'):
                sd=root/name;sd.mkdir();(sd/'review-data.json').write_text(json.dumps({'session':name,'product':name=='managed','prs':[]}));(sd/'events.jsonl').write_text('')
            with mock.patch.object(server,'SESSIONS',root),mock.patch.object(server.Handler,'sdir',root/'legacy',create=True),mock.patch.object(server.Handler,'cfg',cfg,create=True):
                for explicit in (True,False):
                    httpd=ThreadingHTTPServer(('127.0.0.1',0),server.Handler);httpd.product=explicit
                    thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start();port=httpd.server_address[1]
                    def request(route,name,host,origin=None):
                        import http.client
                        connection=http.client.HTTPConnection('127.0.0.1',port)
                        headers={'Host':host,'X-Cockpit-Session':name}
                        if origin:headers['Origin']=origin
                        try:
                            connection.request('GET',route,headers=headers);response=connection.getresponse();body=response.read();return response.status,body
                        finally:connection.close()
                    try:
                        for name in ('managed','legacy') if explicit else ('managed',):
                            for host,origin in [('foreign.test:'+str(port),None),('127.0.0.1:'+str(port),'http://foreign.test:'+str(port))]:
                                for route in ('/api/data','/api/events','/api/memory','/api/app-state','/media/private.png','/app.js'):
                                    with mock.patch.object(server.Handler,'_data',side_effect=AssertionError('payload read before rejection')) as data,mock.patch.object(server.Handler,'_get_selected',side_effect=AssertionError('route ran before rejection')) as selected,mock.patch.object(Client,'read') as provider:
                                        status,_=request(route,name,host,origin);self.assertEqual(status,403);data.assert_not_called();selected.assert_not_called();provider.assert_not_called()
                        for host in ('127.0.0.1','localhost'):
                            host+=':'+str(port);status,body=request('/api/data','managed',host,'http://'+host);self.assertEqual(status,200);self.assertTrue(json.loads(body)['product'])
                        if not explicit:
                            status,body=request('/api/data','legacy','foreign.test:'+str(port));self.assertEqual(status,200);self.assertFalse(json.loads(body).get('product'))
                    finally:
                        httpd.shutdown();httpd.server_close();thread.join(timeout=2)
