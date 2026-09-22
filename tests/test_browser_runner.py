import json
from pathlib import Path
import pytest
from browser_runner import runner
from browser_runner.events import CockpitClient
from browser_runner.policy import PolicyError, assert_allowed_url, meta_library_url
from browser_runner.cloud_observer import _visible_identity
from browser_runner import upstream_adapter

class Response:
    status = 200
    def __init__(self, body=b'{}'): self.body=body
    def read(self): return self.body
    def __enter__(self): return self
    def __exit__(self,*_): pass

def test_policy_blocks_instagram_and_restricts_to_meta_library():
    assert 'view_all_page_id=12' in meta_library_url('12')
    with pytest.raises(PolicyError): assert_allowed_url('https://instagram.com/example')
    with pytest.raises(PolicyError): assert_allowed_url('https://www.facebook.com/not-library')
    with pytest.raises(PolicyError): meta_library_url('not-a-page')

def test_cockpit_is_loopback_bearer_and_sequence_increases():
    sent=[]
    def opener(request, timeout):
        sent.append(request); return Response()
    client=CockpitClient(8766,'x'*24,opener=opener)
    client.emit('run','worker-01','worker_started',company='Fixture')
    client.emit('run','worker-01','worker_complete',ads=0)
    a,b=[json.loads(x.data) for x in sent]
    assert (a['seq'],b['seq']) == (1,2)
    assert sent[0].full_url == 'http://127.0.0.1:8766/api/events'
    assert sent[0].headers['Authorization'] == 'Bearer ' + 'x'*24

def test_plan_is_offline_and_validates_generic_input(tmp_path, capsys):
    path=tmp_path/'companies.json'; path.write_text(json.dumps({'companies':[{'name':'Fixture','page_id':'12'}]}))
    assert runner.main(['--companies',str(path)]) == 0
    plan=json.loads(capsys.readouterr().out)
    assert plan['mode']=='planned' and plan['worker_count']==10
    assert 'approval_required' in plan

def test_live_requires_approval_and_cockpit(tmp_path):
    path=tmp_path/'companies.json'; path.write_text(json.dumps([{'name':'Fixture','page_id':'12'}]))
    with pytest.raises(SystemExit): runner.main(['--companies',str(path),'--execute'])

def test_adapter_uses_bundled_cloud_observer(monkeypatch, tmp_path):
    calls=[]
    def fake_observe(url, **kwargs):
        calls.append((url,kwargs)); return {'outcome':'no_active_ads','ads':0,'detail':{}}
    monkeypatch.setattr(upstream_adapter,'observe',fake_observe)
    result=upstream_adapter.collect({'company':{'name':'Fixture','page_id':'12'},'url':meta_library_url('12'),'output':str(tmp_path/'out')})
    assert result['outcome']=='no_active_ads'
    assert calls[0][1] == {'company':'Fixture','page_id':'12'}

def test_runner_uses_fresh_process_per_company_job():
    import inspect
    source=inspect.getsource(runner.execute)
    assert "context.Process(target=_job_process" in source
    assert "New spawned process per company" in source
    assert "ProcessPoolExecutor" not in source


def test_identity_requires_exact_visible_line_not_copy_substring():
    assert not _visible_identity('A builder can save today\nSponsored', 'Builder')
    assert _visible_identity('Builder\nSponsored', 'Builder')

def test_client_rejection_is_not_silently_accepted():
    def opener(_request, timeout): return Response(b'{"accepted": false}')
    client=CockpitClient(8877,'x'*24,opener=opener)
    with pytest.raises(Exception): client.emit('run','worker-01','worker_started')

def test_scheduler_allocates_free_slots_and_per_job_sequence_bases():
    import inspect
    source=inspect.getsource(runner.execute)
    assert 'free_slots.pop(0)' in source
    assert 'seq_base=index*10' in source
    assert 'worker_timeout' in source

def test_parent_creates_worker_receipt_before_child_process():
    import inspect
    source=inspect.getsource(runner.execute)
    assert 'Parent creates the durable cockpit receipt before a child can crash' in source
    assert 'seq_base+1' in source

def test_vendored_browser_requires_existing_daemon_without_autospawn():
    source=Path('browser_runner/vendor/browser.py').read_text()
    assert 'require_existing_daemon' in source
    assert 'ensure_daemon' not in source
    assert 'BU_NAME' in source

def test_browser_uses_strict_existing_daemon_gate_without_spawn(monkeypatch):
    from browser_runner.vendor import browser
    calls=[]
    monkeypatch.setenv('BU_NAME','isolated-fixture')
    monkeypatch.setattr(browser, 'require_existing_daemon', lambda *, name: calls.append(('gate',name)))
    def fake_cdp(method, **kwargs):
        calls.append((method,kwargs))
        if method=='Target.createTarget': return {'targetId':'target'}
        if method=='Target.attachToTarget': return {'sessionId':'session'}
        if method=='Runtime.evaluate': return {'result':{'value':'complete'}}
        return {}
    monkeypatch.setattr(browser, 'cdp', fake_cdp)
    instance=browser.Browser('https://www.facebook.com/ads/library/?view_all_page_id=12')
    assert calls[0] == ('gate','isolated-fixture')
    assert not any('ensure_daemon' in str(call) for call in calls)
    instance.target=None
