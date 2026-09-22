import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "cockpit" / "server.py"
TOKEN = "x" * 32

def free_port():
    sock=socket.socket(); sock.bind(("127.0.0.1",0)); port=sock.getsockname()[1]; sock.close(); return port

class CockpitServerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.port=free_port(); self.data=Path(self.temp.name)/"history.json"
        self.process=subprocess.Popen([sys.executable,"-u",str(SERVER),"--port",str(self.port),"--data",str(self.data),"--token",TOKEN],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        deadline=time.time()+10
        while time.time()<deadline:
            try: self.get("/api/state"); break
            except Exception: time.sleep(.05)
        else:
            self.process.terminate(); self.process.wait(timeout=2)
            raise RuntimeError(self.process.stderr.read())
    def tearDown(self):
        self.process.terminate(); self.process.wait(timeout=3); self.process.stdout.close(); self.process.stderr.close(); self.temp.cleanup()
    def url(self,path): return f"http://127.0.0.1:{self.port}{path}"
    def get(self,path):
        with urlopen(self.url(path),timeout=2) as response: return json.loads(response.read())
    def post(self, event, token=TOKEN):
        return self.post_raw(json.dumps(event).encode(), token)
    def post_raw(self, body, token=TOKEN):
        request=Request(self.url('/api/events'),data=body,method='POST',headers={'Content-Type':'application/json','Authorization':f'Bearer {token}'})
        with urlopen(request,timeout=2) as response: return response.status,json.loads(response.read())
    def event(self, **extra):
        base={'run_id':'run-1','worker_id':'worker-01','seq':1,'type':'worker_started','timestamp':'2026-09-22T18:00:00Z'};base.update(extra);return base
    def test_auth_and_validation(self):
        with self.assertRaises(HTTPError) as ctx:self.post(self.event(), token='bad')
        self.assertEqual(ctx.exception.code,401); ctx.exception.close()
        with self.assertRaises(HTTPError) as ctx:self.post(self.event(type='made_up'))
        self.assertEqual(ctx.exception.code,400); ctx.exception.close()
        with self.assertRaises(HTTPError) as ctx:self.post(self.event(seq=-1))
        self.assertEqual(ctx.exception.code,400); ctx.exception.close()
    def test_observed_count_distinguishes_zero_and_blocked_and_persists(self):
        self.assertEqual(self.post(self.event(company='Example',url='https://example.test'))[0],202)
        self.post(self.event(seq=2,type='observation',ads=7,detail={'message':'observed','fixture':True}))
        self.post(self.event(seq=3,type='worker_complete',ads=7))
        self.post(self.event(worker_id='worker-02',seq=1,type='worker_started',company='Blocked'))
        self.post(self.event(worker_id='worker-02',seq=2,type='source_blocked',company='Blocked'))
        self.post(self.event(worker_id='worker-03',seq=1,type='worker_started',company='Zero'))
        self.post(self.event(worker_id='worker-03',seq=2,type='zero_ads',company='Zero'))
        self.post(self.event(worker_id='worker-03',seq=3,type='worker_complete',company='Zero',ads=0))
        state=self.get('/api/state'); run=state['active_run']
        self.assertEqual(state['synthetic_totals']['observed_ads'],7)
        self.assertEqual(state['synthetic_totals']['blocked_workers'],1)
        self.assertEqual(state['totals'].get('observed_ads',0),0)
        self.assertEqual(state['synthetic_totals']['zero_ad_workers'],1)
        self.assertTrue(run['synthetic'])
        self.assertTrue(self.data.exists())
        duplicate=self.post(self.event(seq=3,type='worker_complete',ads=999))[1]
        self.assertFalse(duplicate['accepted']); self.assertEqual(self.get('/api/state')['synthetic_totals']['observed_ads'],7)

    def test_reused_ten_lanes_retain_each_company_and_secure_history(self):
        for number in range(1, 12):
            start=(number-1)*3+1
            self.post(self.event(seq=start,type='worker_started',company=f'Company {number}'))
            self.post(self.event(seq=start+1,type='observation',company=f'Company {number}',ads=number))
            self.post(self.event(seq=start+2,type='worker_complete',ads=number))
        state=self.get('/api/state')
        self.assertEqual(state['active_run']['summary']['workers'],11)
        self.assertEqual(state['totals']['observed_ads'],sum(range(1,12)))
        self.assertEqual(state['totals']['completed_workers'],11)
        self.assertEqual(os.stat(self.data).st_mode & 0o777,0o600)
        self.assertEqual(os.stat(self.data.parent).st_mode & 0o777,0o700)
        # A new Store instance reads the exact retained receipt without resetting it.
        sys.path.insert(0,str(ROOT)); from cockpit.server import Store
        restored=Store(self.data).state()
        self.assertEqual(restored['totals']['observed_ads'],sum(range(1,12)))


    def test_origin_csp_and_nonfinite_json_hardening(self):
        request=Request(self.url('/api/state'),headers={'Origin':'https://attacker.example'})
        with self.assertRaises(HTTPError) as ctx:urlopen(request,timeout=2)
        self.assertEqual(ctx.exception.code,403); ctx.exception.close()
        request=Request(self.url('/api/state'),headers={'Sec-Fetch-Site':'cross-site'})
        with self.assertRaises(HTTPError) as ctx:urlopen(request,timeout=2)
        self.assertEqual(ctx.exception.code,403); ctx.exception.close()
        with urlopen(self.url('/api/state'),timeout=2) as response:
            self.assertIn("default-src 'self'",response.headers['Content-Security-Policy'])
            self.assertEqual(response.headers['Referrer-Policy'],'no-referrer')
        raw=b'{"run_id":"r","worker_id":"w","seq":1,"type":"worker_started","timestamp":"2026-09-22T18:00:00Z","detail":{"bad":NaN}}'
        with self.assertRaises(HTTPError) as ctx:self.post_raw(raw)
        self.assertEqual(ctx.exception.code,400); ctx.exception.close()

    def test_loopback_host_rejected(self):
        req=Request(self.url('/api/state'),headers={'Host':'localhost:%d'%self.port})
        with self.assertRaises(HTTPError) as ctx:urlopen(req,timeout=2)
        self.assertEqual(ctx.exception.code,403); ctx.exception.close()

if __name__=='__main__':unittest.main()
