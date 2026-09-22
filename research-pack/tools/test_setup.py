"""Generic installer tests: real files ONLY in TemporaryDirectory, never real Chrome."""
import importlib.util,json,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('friend_install',ROOT/'research-capture/scripts/install.py');installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
class SetupTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();self.home=self.root/'Test Home';self.vault=self.root/'Vault With Spaces';self.vault.mkdir()
 def tearDown(self):self.tmp.cleanup()
 def test_dry_run_no_writes(self):
  p=installer.plan(self.vault,self.home,capture_subdir='Inbox/Research')
  self.assertFalse(self.home.exists());self.assertEqual(Path(p['capture_root']),self.vault/'Inbox/Research')
 def test_path_escape_refused(self):
  for sub in ['../escape','/tmp/escape','.', '']:
   with self.assertRaises(ValueError):installer.plan(self.vault,self.home,capture_subdir=sub)
 def test_symlink_refused(self):
  linked=self.root/'linked';linked.symlink_to(self.vault,target_is_directory=True)
  with self.assertRaises(ValueError):installer.plan(linked,self.home)
 def test_missing_vault_refused(self):
  with self.assertRaises(ValueError):installer.plan(self.root/'absent',self.home)
 def test_install_uninstall_restorable_custom_paths(self):
  chrome=self.root/'Isolated Chrome';p=installer.plan(self.vault,self.home,chrome);installer.install(p)
  config=json.loads((Path(p['install_root'])/'config.json').read_text());self.assertFalse(config['media_enabled']);self.assertFalse(config['landing_enabled']);self.assertEqual(config['allowed_media_hosts'],[])
  nm=Path(p['native_manifest']);self.assertEqual(json.loads(nm.read_text())['name'],'com.jev.research_capture')
  self.assertEqual((Path(p['install_root'])/'config.json').stat().st_mode&0o777,0o600)
  before=nm.read_bytes()
  with self.assertRaises(ValueError):installer.install(p)
  self.assertEqual(nm.read_bytes(),before)
  evidence=Path(p['capture_root'])/'keep.txt';evidence.write_text('synthetic evidence')
  cmd=[sys.executable,str(ROOT/'research-capture/scripts/uninstall.py'),'--home',str(self.home),'--chrome-profile-root',str(chrome)]
  r=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);self.assertTrue(nm.exists())
  r=subprocess.run(cmd+['--execute'],capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
  backup=Path(json.loads(r.stdout)['backup']);self.assertFalse(nm.exists());self.assertFalse(Path(p['install_root']).exists());self.assertEqual(evidence.read_text(),'synthetic evidence')
  (backup/'companion').rename(p['install_root']);(backup/'native-manifest.json').rename(nm);self.assertEqual(nm.read_bytes(),before)
 def test_uninstall_refuses_foreign_host(self):
  p=installer.plan(self.vault,self.home);nm=Path(p['native_manifest']);nm.parent.mkdir(parents=True);nm.write_text(json.dumps({'path':'/not/this/host'}))
  r=subprocess.run([sys.executable,str(ROOT/'research-capture/scripts/uninstall.py'),'--home',str(self.home),'--execute'],capture_output=True);self.assertNotEqual(r.returncode,0);self.assertTrue(nm.exists())
if __name__=='__main__':unittest.main(verbosity=2)
