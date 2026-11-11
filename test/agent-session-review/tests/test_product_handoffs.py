"""Public refresh handoff and memory-transaction concurrency qualification."""
from contextlib import contextmanager
import json
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest
from unittest import mock

from cockpit import collect, memory, server, session_activity
from tests import test_product_access_activity as http_tests
from tests import test_product_enrich_refresh as enrich_tests


class ProductHandoffTests(unittest.TestCase):
    def test_refresh_request_retains_activity_until_worker_has_its_own_lease(self):
        helper=http_tests.ProductAccessActivityTests()
        real=session_activity.session_activity
        starting=threading.Event();allow=threading.Event();working=threading.Event();finish=threading.Event()
        @contextmanager
        def paused(sdir, **kwargs):
            inherited=session_activity._HELD.get()
            if inherited and all(owner[2] != threading.get_ident() for owner,_ in inherited):
                starting.set()
                if not allow.wait(3):raise RuntimeError('fixture handoff timeout')
            with real(sdir,**kwargs):yield
        def refresh(*args):
            working.set()
            if not finish.wait(4):raise RuntimeError('fixture refresh timeout')
            return {}
        with helper.local_server() as (root,httpd,cfg), mock.patch.object(server.Handler,'_refreshing',{}), \
             mock.patch.object(session_activity,'session_activity',side_effect=paused), mock.patch.object(collect,'refresh',side_effect=refresh):
            results=[]
            request=threading.Thread(target=lambda:results.append(helper.request(httpd,'/api/refresh',{})))
            request.start()
            def other_process_trash():
                script="""from pathlib import Path
import sys
from cockpit.session_activity import session_activity
from cockpit.session_writer import SessionBusy
try:
 with session_activity(Path(sys.argv[1]),exclusive=True):print('unexpected-free')
except SessionBusy:print('busy')
"""
                result=subprocess.run([sys.executable,'-B','-c',script,str(root/'sessions/a')],capture_output=True,text=True,timeout=3)
                self.assertEqual(result.returncode,0,result.stderr)
                self.assertEqual(result.stdout.strip(),'busy')
            try:
                self.assertTrue(starting.wait(3));self.assertFalse(results)
                other_process_trash()  # request lease protects the not-yet-admitted worker
                allow.set();self.assertTrue(working.wait(3));request.join(timeout=3)
                self.assertEqual(results[0][0],200);self.assertTrue(json.loads(results[0][1])['ok'])
                other_process_trash()  # the request ended, but the worker still protects the session
            finally:
                allow.set();finish.set();request.join(timeout=4)
                until=time.monotonic()+3
                while (server.Handler._refreshing.get('a') or {}).get('state')=='running' and time.monotonic()<until:time.sleep(.01)

    def test_distill_check_and_propose_share_the_direct_edit_transaction(self):
        helper=enrich_tests.ProductEnrichRefreshTests()
        with helper.session() as (root,sd,cfg,read):
            cfg['memory']={'enabled':True,'amr':str(root/'amr'),'okf':str(root/'okf'),'auto_commit':False}
            config=root/'cfg.json';config.write_text(json.dumps(cfg))
            checked=root/'checked';release=root/'release';attempt=root/'attempt';done=root/'done'
            (sd/'events.jsonl').write_text(json.dumps({'type':'note','decision':'accept','decision_text':'Decision title','pr':'org/repo#1','path':'a.py'})+'\n')
            distill_script="""import json,pathlib,sys,time
from cockpit.memory import OKF
from cockpit.distill import distill
root=pathlib.Path(sys.argv[1]);original=OKF.concepts;first=[True]
def pause(self):
 result=original(self)
 if first[0]:
  first[0]=False;(root/'checked').write_text('ready')
  until=time.monotonic()+6
  while not (root/'release').exists() and time.monotonic()<until:time.sleep(.01)
 return result
OKF.concepts=pause
distill(pathlib.Path(sys.argv[2]),json.loads((root/'cfg.json').read_text()))
"""
            edit_script="""import pathlib,sys
from cockpit.memory import OKF
root=pathlib.Path(sys.argv[1]);(root/'attempt').write_text('started')
okf=OKF(root/'okf');okf.propose(type_='Decision',title='A direct edit',body='Independent intent',paths=['a.py'],by='fixture',sources=[])
okf.write_index();(root/'done').write_text('finished')
"""
            first=subprocess.Popen([sys.executable,'-B','-c',distill_script,str(root),str(sd)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
            second=None
            def wait_for(path):
                until=time.monotonic()+4
                while not path.exists() and time.monotonic()<until:time.sleep(.01)
                self.assertTrue(path.exists(),str(path))
            try:
                wait_for(checked)
                second=subprocess.Popen([sys.executable,'-B','-c',edit_script,str(root)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
                wait_for(attempt)
                # Both processes are live: the direct edit must remain blocked inside the transaction.
                time.sleep(.15);self.assertFalse(done.exists())
                release.write_text('go')
                for child in (first,second):
                    _,error=child.communicate(timeout=8);self.assertEqual(child.returncode,0,error)
                self.assertEqual({c.meta['title'] for c in memory.OKF(root/'okf').concepts()},{'Decision title','A direct edit'})
                index=(root/'okf/index.md').read_text()
                for concept in memory.OKF(root/'okf').concepts():self.assertIn(concept.path,index)
            finally:
                release.write_text('go')
                for child in (first,second):
                    if child and child.poll() is None:child.communicate(timeout=8)
