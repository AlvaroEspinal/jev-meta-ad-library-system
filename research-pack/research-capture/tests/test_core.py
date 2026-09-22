import base64,copy,json,os,subprocess,sys,tempfile,unittest,uuid,struct,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'companion'));sys.path.insert(0,str(ROOT/'scripts'))
from core import Store,CaptureError,validate,url,now,MAX_MESSAGE
from host import dispatch
from install import plan,install
from media import public_addresses,download
from unittest.mock import patch

def png():
 def chunk(k,d):return struct.pack('>I',len(d))+k+d+struct.pack('>I',zlib.crc32(k+d)&0xffffffff)
 return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00\xff\xff\xff'))+chunk(b'IEND',b'')

def payload(source='https://example.com/article'):
 return {'schema_version':1,'capture_id':str(uuid.uuid4()),'captured_at':now(),'source_url':source,'project':'research','rights_basis':'reference-only','fields':{'title':'A public page','primary_text':'Evidence'},'media_references':[],'consent':{'confirmed':True,'public_only':True},'method':'manual'}
class CaptureTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.store=Store(self.root/'captures',b'k'*32)
 def test_store_and_verify(self):
  r=self.store.save(payload());self.assertTrue(self.store.verify(r['id'])['ok']);self.assertTrue(Path(r['note']).is_file());self.assertEqual(r['status'],'partial')
 def test_dedupe(self):
  a=self.store.save(payload());b=self.store.save(payload());self.assertEqual(a['id'],b['id']);self.assertEqual(b['status'],'duplicate')
 def test_tamper(self):
  r=self.store.save(payload());(Path(r['note']).parent/'evidence.json').write_text('bad')
  with self.assertRaises(CaptureError):self.store.verify(r['id'])
 def test_note_tamper(self):
  r=self.store.save(payload());Path(r['note']).write_text('bad')
  with self.assertRaises(CaptureError):self.store.verify(r['id'])
 def test_secret_redaction(self):
  p=payload('https://example.com/a?token=secret&utm_source=foo#password');p['fields']['notes']='api_key=abcdefghij'
  r=self.store.save(p);s=Path(r['note']).read_text();self.assertNotIn('abcdefghij',s);self.assertNotIn('?token',s)
 def test_url_private(self):
  for s in ['http://127.0.0.1/a','http://10.0.0.1','http://[::1]','http://localhost','http://a.local','https://user:pass@host/a','file:///a','javascript:x','https://x.com:9999']:
   with self.subTest(s=s),self.assertRaises(CaptureError):url(s)
 def test_path_traversal(self):
  p=payload();p['project']='../../x'
  with self.assertRaises(CaptureError):self.store.save(p)
 def test_symlink(self):
  (self.store.root/'receipts.jsonl').symlink_to(self.root/'outside')
  with self.assertRaises(CaptureError):self.store.save(payload())
 def test_fields_reject(self):
  p=payload();p['fields']['cookies']='secret'
  with self.assertRaises(CaptureError):self.store.save(p)
 def test_consent(self):
  for c in [{},{'confirmed':True},{'confirmed':True,'public_only':True,'x':'data'}]:
   p=payload();p['consent']=c
   with self.assertRaises(CaptureError):self.store.save(p)
 def test_instagram_url_only(self):
  p=payload('https://www.instagram.com/p/abc/?token=SECRET');p['fields']={'notes':'user intent'};r=self.store.save(p);self.assertEqual(r['status'],'partial')
  p['fields']['title']='private'
  with self.assertRaises(CaptureError):self.store.save(p)
 def test_instagram_bad_paths(self):
  for s in ['https://instagram.com/direct/inbox','https://instagram.com/accounts','https://instagram.com/stories/name/123']:
   p=payload(s);p['fields']={}
   with self.assertRaises(CaptureError):self.store.save(p)
 def test_meta_session_confirmation(self):
  p=payload('https://www.facebook.com/ads/library/?id=123')
  with self.assertRaises(CaptureError):self.store.save(p)
  p['consent']['isolated_logged_out']=True;self.assertTrue(self.store.save(p)['ok'])
 def test_meta_outside_library(self):
  with self.assertRaises(CaptureError):self.store.save(payload('https://facebook.com/messages'))
 def test_screenshot_rights(self):
  p=payload();p['screenshot']='data:image/png;base64,'+base64.b64encode(png()).decode()
  with self.assertRaises(CaptureError):self.store.save(p)
  p['rights_basis']='client-owned';p['consent']['screenshot']=True;r=self.store.save(p);self.assertTrue(self.store.verify(r['id'])['ok'])
 def test_rate_limit(self):
  for i in range(20):self.store.save(payload('https://example.com/'+str(i)))
  with self.assertRaises(CaptureError):self.store.save(payload('https://example.com/21'))
 def test_no_arbitrary_commands(self):
  for command in ['exec','download','shell','write_file']:
   with self.assertRaises(CaptureError):dispatch({'command':command},self.store)
 def test_dns_private(self):
  with patch('socket.getaddrinfo',return_value=[(2,1,6,'',('127.0.0.1',443))]),self.assertRaises(CaptureError):public_addresses('example.com')
 def test_platform_download_rejected(self):
  with self.assertRaises(CaptureError):download('https://www.instagram.com/p/abc/','www.instagram.com',self.root)
 def test_native_roundtrip(self):
  p=plan(self.root,self.root/'home');install(p);host=Path(p['install_root'])/'host.py'
  def call(msg,origin=None):
   data=json.dumps(msg).encode();r=subprocess.run([sys.executable,str(host),origin or p['origin']],input=struct.pack('=I',len(data))+data,capture_output=True,check=True);n=struct.unpack('=I',r.stdout[:4])[0];return json.loads(r.stdout[4:4+n])
  self.assertTrue(call({'command':'health'})['ok']);r=call({'command':'capture','payload':payload()});self.assertTrue(r['ok']);self.assertTrue(call({'command':'verify','id':r['id']})['ok']);self.assertFalse(call({'command':'health'},'chrome-extension://'+'a'*32+'/')['ok'])
 def test_oversize_native_frame(self):
  p=plan(self.root,self.root/'home');install(p);r=subprocess.run([sys.executable,str(Path(p['install_root'])/'host.py'),p['origin']],input=struct.pack('=I',MAX_MESSAGE+1),capture_output=True);self.assertIn(b'Message size',r.stdout)
if __name__=='__main__':unittest.main()

class RegressionTests(unittest.TestCase):
 def test_capture_id_cannot_change_evidence(self):
  with tempfile.TemporaryDirectory() as t:
   s=Store(Path(t),b'k');p=payload();s.save(p);p['fields']['title']='changed'
   with self.assertRaises(CaptureError):s.save(p)
 def test_dom_origin_allowlist(self):
  with tempfile.TemporaryDirectory() as t:
   p=payload('https://not-approved.example/');p['method']='visible-dom'
   with self.assertRaises(CaptureError):dispatch({'command':'capture','payload':p},Store(t,b'k'))
 def test_invalid_png(self):
  with tempfile.TemporaryDirectory() as t:
   p=payload();p['rights_basis']='client-owned';p['consent']['screenshot']=True;p['screenshot']='data:image/png;base64,'+base64.b64encode(b'\x89PNG\r\n\x1a\nnot-an-image').decode()
   with self.assertRaises(CaptureError):Store(t,b'k').save(p)
 def test_url_markup_encoded(self):self.assertNotIn('![',url('https://example.com/![[malicious]]'))
 def test_media_private_dns_all_ips(self):
  with patch('socket.getaddrinfo',return_value=[(2,1,6,'',('1.1.1.1',443)),(2,1,6,'',('192.168.1.1',443))]),self.assertRaises(CaptureError):public_addresses('example.com')

class HostnameTests(unittest.TestCase):
 def test_instagram_dot(self):
  p=payload('https://www.instagram.com./p/test/');p['fields']={'title':'must fail'}
  with self.assertRaises(CaptureError):validate(p)
 def test_meta_fake_path(self):
  with self.assertRaises(CaptureError):validate(payload('https://facebook.com/ads/library-private'))

class DuplicateIntegrityTests(unittest.TestCase):
 def test_corrupt_duplicate_not_success(self):
  with tempfile.TemporaryDirectory() as t:
   store=Store(t,b'k');p=payload();r=store.save(p);Path(r['note']).write_text('corrupted')
   with self.assertRaises(CaptureError):store.save(p)
 def test_duplicate_calls_rate_limited(self):
  with tempfile.TemporaryDirectory() as t:
   store=Store(t,b'k');p=payload()
   for _ in range(20):store.save(p)
   with self.assertRaises(CaptureError):store.save(p)
