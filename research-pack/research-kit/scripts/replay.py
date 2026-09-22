"""Offline typed replay; no inference, credentials or network."""
import argparse,hashlib,json
from pathlib import Path
from jev_contract import canonical,strict_json,validate_request,validate_response,ContractError

def replay(request,response):
    request=validate_request(request,'synthetic/fixture')
    answers=validate_response(response,request['questions'],'synthetic/fixture')
    return {'schema_version':'jev-replay/1','status':'replay_validated','request_sha256':hashlib.sha256(canonical(request)).hexdigest(),'answers':answers,'model':response['model'],'provider':'offline','network_calls':0,'cost':0,'accepted':False,'review_required':True,'outcome_verified':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--request',required=True);p.add_argument('--response',required=True);p.add_argument('--out',required=True);a=p.parse_args()
    try:r=replay(strict_json(Path(a.request).read_bytes()),strict_json(Path(a.response).read_bytes()))
    except (ContractError,OSError):r={'status':'replay_failed','network_calls':0,'accepted':False,'review_required':True,'outcome_verified':False}
    with Path(a.out).open('x') as f:json.dump(r,f,indent=2)
    print(r['status']);raise SystemExit(0 if r['status']=='replay_validated' else 1)
