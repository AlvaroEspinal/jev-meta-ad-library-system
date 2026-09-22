import contextlib,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'companion'))
import jev_client
from research import make_record,request_for,classify
from core import validate
from test_workflows import payload
class ClientTest(unittest.TestCase):
 def test_dry_run_no_key_or_network(self):
  with tempfile.TemporaryDirectory() as t:
   req=Path(t)/'request.json';out=Path(t)/'result.json';e,_=validate(payload());req.write_text(json.dumps(request_for(make_record(e))))
   with patch('jev_client.get_key') as key,patch('jev_client.urlopen') as net,contextlib.redirect_stdout(io.StringIO()):jev_client.main(['--input',str(req),'--out',str(out)])
   key.assert_not_called();net.assert_not_called();self.assertEqual(json.loads(out.read_text())['status'],'dry_run')
 def test_import_hash_binding(self):
  e,_=validate(payload());record=make_record(e);q=request_for(record)['questions'];answer={k:{'type':'choice','choice':'review','confidence':1,'probabilities':{x:float(x=='review') for x in v['criteria']}} for k,v in q.items()};_,receipt=classify(record)
  raw={'schema_version':'jev-decision/2','status':'completed','request_sha256':receipt['request_sha256'],'resolved_model':'synthetic/fixture','provider':'openrouter','usage':{'input_tokens':12,'output_tokens':3,'cost':0.01},'latency_ms':40,'answers':answer}
  _,result=classify(record,'shadow_import',raw);self.assertEqual(result['status'],'structurally_validated');self.assertFalse(result['accepted']);self.assertEqual(result['cost'],0.01);self.assertEqual(result['latency_ms'],40)
  raw['request_sha256']='wrong';_,result=classify(record,'shadow_import',raw);self.assertEqual(result['status'],'failed')
 def test_redirect_refused(self):
  from urllib.request import Request
  from urllib.error import HTTPError
  with self.assertRaises(HTTPError):jev_client.NoRedirect().redirect_request(Request('https://openrouter.ai/'),None,302,'move',{},'https://evil.example/')
 def test_nonobject_response_fails_honestly(self):
  e,_=validate(payload());_,r=classify(make_record(e),'shadow_import',[]);self.assertEqual(r['status'],'failed')
 def test_large_evidence_is_bounded_and_flagged(self):
  e,_=validate(payload());record=make_record(e);record['evidence']=[{'id':str(i),'text':'x'*30000} for i in range(50)];req,receipt=classify(record);self.assertTrue(req['state']['evidence_truncated']);self.assertEqual(receipt['cost'],0)
