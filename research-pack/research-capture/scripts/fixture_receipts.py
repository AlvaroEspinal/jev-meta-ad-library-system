#!/usr/bin/env python3
import base64,json,sys,uuid,zlib,struct
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'companion'))
from core import Store,now
root=Path(__file__).resolve().parents[1]/'artifacts/fixture-vault';s=Store(root,b'fixture-only-not-a-secret')
def chunk(k,d):return struct.pack('>I',len(d))+k+d+struct.pack('>I',zlib.crc32(k+d)&0xffffffff)
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00\xff\xff\xff'))+chunk(b'IEND',b'')
for kind,url,f in [('web','https://example.com/fixture',{'title':'Web fixture','primary_text':'Fixture only'}),('youtube','https://youtube.com/watch?v=fixture',{'title':'Video fixture','identity':'Fixture Channel','source_id':'fixture'}),('meta','https://www.facebook.com/ads/library/?id=123',{'title':'Ad fixture','identity':'Fixture Builder','source_id':'123','primary_text':'Fixture ad copy','headline':'Fixture headline','cta':'Learn more'}),('ig','https://instagram.com/p/fixture/',{'notes':'User-entered URL handoff fixture, not browser capture'})]:
 p={'schema_version':1,'capture_id':str(uuid.uuid4()),'captured_at':now(),'source_url':url,'project':'fixture','rights_basis':'client-owned','fields':f,'media_references':[],'consent':{'confirmed':True,'public_only':True,'isolated_logged_out':kind=='meta','screenshot':kind!='ig'},'method':'manual' if kind!='ig' else 'instagram-url-handoff'}
 if kind!='ig':p['screenshot']='data:image/png;base64,'+base64.b64encode(png).decode()
 print(json.dumps(s.save(p)))
