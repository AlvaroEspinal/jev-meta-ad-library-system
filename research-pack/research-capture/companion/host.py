#!/usr/bin/env python3
"""Chrome native messaging. No ports or arbitrary paths. Explicit workflows use configured, bounded local adapters."""
import json,os,struct,sys
from pathlib import Path
from urllib.parse import urlsplit
from core import Store,CaptureError,MAX_MESSAGE

def exact(stream,n):
    b=b''
    while len(b)<n:
        v=stream.read(n-len(b))
        if not v:raise CaptureError('Truncated native message')
        b+=v
    return b

DEFAULT_ORIGINS=['https://example.com','https://developer.chrome.com','https://www.youtube.com','https://youtube.com','https://www.facebook.com','https://facebook.com']

def dispatch(msg,store,origins=None,config=None):
    origins=DEFAULT_ORIGINS if origins is None else origins
    if not isinstance(msg,dict):raise CaptureError('Object required')
    if msg.get('command')=='health' and set(msg)=={'command'}:return {'ok':True,'status':'ready','version':'0.2.1','network':'configured-explicit-only','vault_root':str(store.root),'allowed_capture_origins':origins}
    if msg.get('command')=='workflow':
        if not config:raise CaptureError('Workflow configuration missing')
        from workflows import Workflows
        p=msg.get('payload',{})
        if isinstance(p,dict) and p.get('method')=='visible-dom':
            u=urlsplit(p.get('source_url',''))
            if f'{u.scheme}://{u.netloc}' not in origins:raise CaptureError('Origin not approved for DOM capture')
        return Workflows(config).run(msg)
    if msg.get('command')=='capture' and set(msg)=={'command','payload'}:
        p=msg['payload']
        if isinstance(p,dict) and (p.get('method')=='visible-dom' or p.get('screenshot')):
            u=urlsplit(p.get('source_url',''))
            if f'{u.scheme}://{u.netloc}' not in origins:raise CaptureError('Origin not approved for DOM/screenshot capture; use manual reference')
        return store.save(p)
    if msg.get('command')=='verify' and set(msg)=={'command','id'}:return store.verify(msg['id'])
    raise CaptureError('Unsupported command')

def main():
    os.umask(0o077)
    try:
        config=Path(__file__).resolve().parent/'config.json'
        c=json.loads(config.read_text())
        if len(sys.argv)!=2 or sys.argv[1]!=c['origin']:raise CaptureError('Caller origin denied')
        header=exact(sys.stdin.buffer,4);size=struct.unpack('=I',header)[0]
        if not 0<size<=MAX_MESSAGE:raise CaptureError('Message size exceeds limit')
        msg=json.loads(exact(sys.stdin.buffer,size))
        store=None if isinstance(msg,dict) and msg.get('command')=='workflow' else Store(c['capture_root'],bytes.fromhex(c['receipt_key']))
        result=dispatch(msg,store,c.get('allowed_capture_origins',DEFAULT_ORIGINS),c)
    except Exception as e:
        result={'ok':False,'status':'failed','error':str(e) if isinstance(e,CaptureError) else 'Local host error; inspect installation/configuration. No capture claimed.'}
    output=json.dumps(result).encode();sys.stdout.buffer.write(struct.pack('=I',len(output))+output);sys.stdout.buffer.flush()
if __name__=='__main__':main()
