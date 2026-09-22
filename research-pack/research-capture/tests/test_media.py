import io,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'companion'))
from core import CaptureError
import media
class Response:
 def __init__(self,status=200,mime='audio/wav',body=None,length=None):
  self.status=status;self.mime=mime;self.body=io.BytesIO(body if body is not None else b'RIFF'+b'\0'*4+b'WAVE'+b'\0'*32);self.length=length
 def getheader(self,k,default=None):return self.mime if k=='Content-Type' else self.length if k=='Content-Length' else default
 def read(self,n):return self.body.read(n)
class Connection:
 def __init__(self,response):self.response=response;self.closed=False;self.calls=[]
 def request(self,*args,**kwargs):self.calls.append((args,kwargs))
 def getresponse(self):return self.response
 def close(self):self.closed=True
class DownloadTests(unittest.TestCase):
 def run_download(self,response):
  c=Connection(response)
  with tempfile.TemporaryDirectory() as t,patch('media.public_addresses',return_value=['1.1.1.1']),patch('media.PinnedHTTPS',return_value=c):
   result=media.download('https://assets.example/clip.wav','assets.example',Path(t))
   self.assertTrue((Path(t)/result['path']).is_file());self.assertTrue(c.closed);return result,c
 def test_success_bytes_hash_and_no_credentials(self):
  r,c=self.run_download(Response());self.assertEqual(r['bytes'],44);self.assertNotIn('Cookie',c.calls[0][1]['headers']);self.assertNotIn('Authorization',c.calls[0][1]['headers'])
 def test_redirect_denied_and_closed(self):
  c=Connection(Response(status=302))
  with tempfile.TemporaryDirectory() as t,patch('media.public_addresses',return_value=['1.1.1.1']),patch('media.PinnedHTTPS',return_value=c),self.assertRaises(CaptureError):media.download('https://assets.example/a','assets.example',Path(t))
  self.assertTrue(c.closed);self.assertEqual(len(c.calls),1)
 def test_mime_spoof_rejected(self):
  with self.assertRaises(CaptureError):self.run_download(Response(mime='image/png',body=b'<html>sign in</html>'))
 def test_declared_oversize(self):
  with self.assertRaises(CaptureError):self.run_download(Response(length=str(media.LIMIT+1)))
 def test_stream_oversize(self):
  with patch('media.LIMIT',10),self.assertRaises(CaptureError):self.run_download(Response())
 def test_platform_trailing_dot_no_network(self):
  with patch('media.public_addresses') as dns,tempfile.TemporaryDirectory() as t,self.assertRaises(CaptureError):media.download('https://www.instagram.com./p/test/','www.instagram.com.',Path(t))
  dns.assert_not_called()
 def test_signed_url_stays_reference(self):
  with patch('media.public_addresses') as dns,tempfile.TemporaryDirectory() as t,self.assertRaises(CaptureError):media.download('https://assets.example/a?sig=secret','assets.example',Path(t))
  dns.assert_not_called()
 def test_invalid_url_records_failure_without_secret(self):
  with tempfile.TemporaryDirectory() as t:
   out=Path(t)/'out';r=subprocess.run([sys.executable,str(Path(media.__file__)),'--source','https://user:secret@example.com/clip','--output',str(out),'--rights','licensed','--approve-download','--allow-host','example.com'],capture_output=True)
   self.assertNotEqual(r.returncode,0);m=json.loads((out/'media-manifest.json').read_text());self.assertEqual(m['status'],'failed');self.assertNotIn('secret',json.dumps(m))
