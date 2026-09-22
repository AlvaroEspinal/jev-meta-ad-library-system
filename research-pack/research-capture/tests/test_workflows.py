import copy,json,sys,tempfile,unittest,uuid,wave,shutil
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'companion'))
from core import CaptureError,sha,now
from workflows import Workflows,approved_import,convert_mp3
from research import request_for,make_record,classify,TAXONOMY
import landing
from host import dispatch

def payload(source='https://www.facebook.com/ads/library/?id=123'):
 return {'schema_version':1,'capture_id':str(uuid.uuid4()),'captured_at':now(),'source_url':source,'project':'research','rights_basis':'licensed','fields':{'title':'Synthetic ad','identity':'Example workshop','source_id':'123','primary_text':'A written plan. Book a call.','headline':'Know the plan','subheadline':'No invented fields','cta':'Book a call','landing_url':'https://example.com/plan','active_status':'Active','advertiser_id':'456','format':'image'},'media_references':[],'consent':{'confirmed':True,'public_only':True,'isolated_logged_out':True},'method':'manual'}
class WorkflowsTest(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup);self.root=Path(self.t.name);self.config={'capture_root':str(self.root/'vault'),'downloads_root':str(self.root/'Downloads'),'receipt_key':'aa'*32,'media_enabled':False,'landing_enabled':False};self.w=Workflows(self.config)
  self.media=self.root/'fixture.wav'
  with wave.open(str(self.media),'wb') as f:f.setnchannels(1);f.setsampwidth(2);f.setframerate(16000);f.writeframes(b'\x00\x00'*1600)
 def message(self,mode='save_obsidian'):return {'command':'workflow','mode':mode,'payload':payload(),'title':'Clear / project: intro','convert':'original'}
 def test_download_does_not_create_vault_and_collision_safe(self):
  m=self.message('quick_download');a=self.w.run(m,imported=(self.media,'audio/wav'));b=self.w.run(m,imported=(self.media,'audio/wav'))
  self.assertFalse((self.root/'vault').exists());self.assertNotEqual(a['path'],b['path']);self.assertFalse(a['vault_written']);self.assertEqual(sha(Path(a['path']).read_bytes()),a['sha256']);self.assertIn('(2)',b['path'])
 def test_complete_record_asset_readback(self):
  r=self.w.run(self.message(),imported=(self.media,'audio/wav'));self.assertEqual(r['status'],'captured');folder=Path(r['path']);self.assertTrue(self.w.verify(folder));self.assertTrue((folder/'asset.wav').exists());self.assertTrue((folder/'index.html').exists());record=json.loads((folder/'record.json').read_text());self.assertEqual(record['subheadline'],'No invented fields');self.assertEqual(record['classification']['cost'],0)
 def test_partial_missing_field(self):
  m=self.message();del m['payload']['fields']['headline'];r=self.w.run(m);self.assertEqual(r['status'],'partial');self.assertIn('headline',r['gaps'])
 def test_landing_inaccessible(self):
  m=self.message();m['fetch_landing']=True;r=self.w.run(m);self.assertEqual(r['status'],'partial');self.assertIn('Landing page not checked',r['gaps'])
 def test_duplicate_and_changed_creative(self):
  m=self.message();a=self.w.run(m);b=self.w.run(m);self.assertEqual(b['status'],'duplicate');m['payload']['fields']['primary_text']='Changed creative';c=self.w.run(m);self.assertNotEqual(a['id'],c['id'])
 def test_model_failure_visible(self):
  r=self.w.run(self.message(),response={'error':'failure'});self.assertEqual(r['status'],'partial');d=json.loads((Path(r['path'])/'decision.json').read_text());self.assertEqual(d['status'],'failed');self.assertFalse(d['accepted']);self.assertIsNone(d['cost'])
 def test_off_zero_calls(self):
  with patch('media.PinnedHTTPS') as network:
   r=self.w.run(self.message());self.assertEqual(r['model_calls'],0);self.assertEqual(r['model_cost'],0);network.assert_not_called()
 def test_tampered_duplicate_rejected(self):
  m=self.message();r=self.w.run(m);(Path(r['path'])/'record.json').write_text('tampered')
  with self.assertRaises(CaptureError):self.w.run(m)
 def test_download_not_enabled(self):
  m=self.message('quick_download');m['asset_url']='https://example.com/clip.wav';r=self.w.run(m);self.assertFalse(r['ok']);self.assertFalse((self.root/'vault').exists());self.assertFalse(list((self.root/'Downloads').glob('*.wav')))
 def test_no_arbitrary_native_paths(self):
  m=self.message();m['output']='/tmp/not-allowed'
  with self.assertRaises(CaptureError):self.w.run(m)
 def test_native_workflow_origin(self):
  m=self.message();m['payload']['method']='visible-dom';m['payload']['source_url']='https://not-approved.example/'
  with self.assertRaises(CaptureError):dispatch(m,None,config=self.config)
 def test_instagram_requires_external_adapter_no_network(self):
  m=self.message('quick_download');m['payload']=payload('https://www.instagram.com/p/abc123/');m['payload']['fields']={'notes':'external intent'};m['payload']['method']='instagram-url-handoff';m['external_import']=True
  with patch('media.PinnedHTTPS') as net,patch('landing.PinnedHTTPS') as lp:
   with self.assertRaises(CaptureError):self.w.run(m)
   net.assert_not_called();lp.assert_not_called()
 def test_approved_external_instagram_import(self):
  receipt=self.root/'adapter.json';receipt.write_text(json.dumps({'transport':'canonical-nonbrowser','adapter':'canonical-apify','status':'captured','browser_used':False,'path':'fixture.wav','mime':'audio/wav','sha256':sha(self.media.read_bytes())}))
  asset=approved_import(receipt,self.root);m=self.message('quick_download');m['payload']=payload('https://www.instagram.com/p/abc123/');m['payload']['fields']={'notes':'External import'};m['payload']['method']='instagram-url-handoff';m['external_import']=True
  with patch('media.PinnedHTTPS') as network:
   r=self.w.run(m,imported=asset);self.assertTrue(r['ok']);network.assert_not_called()
 def test_failed_adapter_is_not_success(self):
  receipt=self.root/'adapter.json';receipt.write_text(json.dumps({'transport':'canonical-nonbrowser','status':'failed','browser_used':False}))
  with self.assertRaises(CaptureError):approved_import(receipt,self.root)
 def test_adapter_path_escape(self):
  receipt=self.root/'adapter.json';receipt.write_text(json.dumps({'transport':'canonical-nonbrowser','adapter':'canonical-apify','status':'captured','browser_used':False,'path':'../escape','mime':'audio/wav','sha256':'x'}))
  with self.assertRaises(CaptureError):approved_import(receipt,self.root)
 def test_request_all_dimensions_and_canonical(self):
  from core import validate
  e,_=validate(payload());q=request_for(make_record(e))['questions'];self.assertEqual(q['journey_stage']['criteria'],TAXONOMY['awareness']);self.assertEqual(set(q['primary_angle']['criteria']),set(TAXONOMY['angles']));self.assertTrue({'hook','offer','authority','proof','fear','benefit','comparison','format','company_category','ad_landing_match','funnel_stage'}<=q.keys())
 @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'local media tools absent')
 def test_real_local_mp3(self):
  out=self.root/'conversion';out.mkdir();p,mime=convert_mp3(self.media,out);self.assertEqual(mime,'audio/mpeg');self.assertGreater(p.stat().st_size,10)
class LandingTest(unittest.TestCase):
 def test_static_no_script_no_inferred_claims(self):
  r=landing.extract('<h1>Example plan</h1><script>secret()</script><form><p>Private form</p></form><p>Evidence paragraph</p><a href="/apply">Apply</a>','https://example.com/')
  self.assertEqual(r['fields']['headline'],'Example plan');self.assertIsNone(r['fields']['proof']);self.assertNotIn('secret',json.dumps(r));self.assertNotIn('Private form',json.dumps(r))
 def test_private_denied_before_network(self):
  with patch('landing.PinnedHTTPS') as n:
   with self.assertRaises(CaptureError):landing.fetch('https://127.0.0.1/',['127.0.0.1'])
   n.assert_not_called()
 def test_instagram_denied_before_network(self):
  with patch('landing.PinnedHTTPS') as n:
   with self.assertRaises(CaptureError):landing.fetch('https://www.instagram.com/p/test/',['www.instagram.com'])
   n.assert_not_called()

class ExtraGuards(unittest.TestCase):
 setUp=WorkflowsTest.setUp
 message=WorkflowsTest.message
 def test_valid_shadow_import_keeps_review(self):
  from core import validate
  e,_=validate(payload());record=make_record(e);q=request_for(record)['questions'];answers={}
  for k,v in q.items():answers[k]={'type':'choice','choice':'review','confidence':1,'probabilities':{name:float(name=='review') for name in v['criteria']}}
  r=self.w.run(self.message(),response={'model':'synthetic/fixture','answers':answers});d=json.loads((Path(r['path'])/'decision.json').read_text());self.assertEqual(d['status'],'structurally_validated');self.assertFalse(d['accepted']);self.assertIsNone(d['cost'])
 def test_rate_limit(self):
  for i in range(20):self.w.run(self.message())
  with self.assertRaises(CaptureError):self.w.run(self.message())
 def test_symlink_download_root(self):
  target=self.root/'elsewhere';target.mkdir();(self.root/'Downloads').symlink_to(target)
  with self.assertRaises(CaptureError):self.w.run(self.message('quick_download'),imported=(self.media,'audio/wav'))
