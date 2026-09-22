"""Negative fixture tests; no browser or model calls."""
import copy,json,tempfile,unittest
from pathlib import Path
from jev_contract import ContractError,strict_json
from replay import replay
from demo import build,ROOT
class Kit(unittest.TestCase):
    def setUp(self):
        self.q=json.loads((ROOT/'fixtures/request.json').read_text());self.r=json.loads((ROOT/'fixtures/response.json').read_text())
    def test_replay(self):
        r=replay(self.q,self.r);self.assertFalse(r['accepted']);self.assertTrue(r['review_required']);self.assertEqual(r['network_calls'],0)
    def test_unknown_choice(self):
        self.r['answers']['primary_angle']['choice']='invented'
        with self.assertRaises(ContractError):replay(self.q,self.r)
    def test_bad_probabilities(self):
        self.r['answers']['primary_angle']['probabilities']['other']=1
        with self.assertRaises(ContractError):replay(self.q,self.r)
    def test_missing_answer(self):
        del self.r['answers']['journey_stage']
        with self.assertRaises(ContractError):replay(self.q,self.r)
    def test_wrong_model(self):
        self.r['model']='unexpected'
        with self.assertRaises(ContractError):replay(self.q,self.r)
    def test_duplicate_keys(self):
        with self.assertRaises(ContractError):strict_json('{"a":1,"a":2}')
    def test_nonfinite(self):
        with self.assertRaises(ContractError):strict_json('{"a":NaN}')
    def test_report_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'report';build(p)
            self.assertIn('SYNTHETIC / OFFLINE',(p/'index.html').read_text())
            with self.assertRaises(FileExistsError):build(p)
    def test_taxonomy(self):
        t=json.loads((ROOT/'schemas/taxonomy.json').read_text())
        self.assertEqual(len(t['awareness']),6);self.assertEqual(len(t['angles']),15)
        self.assertNotIn('top',t['awareness']);self.assertIn('review',t['funnel_extension'])
if __name__=='__main__':unittest.main()
