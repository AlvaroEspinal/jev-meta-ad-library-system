"""Generate a static, escaped, offline synthetic evidence report."""
import argparse,html,json
from pathlib import Path
from replay import replay
ROOT=Path(__file__).resolve().parents[1]
def build(out):
    out=Path(out);out.mkdir(exist_ok=False)
    record=json.loads((ROOT/'fixtures/ad-record.json').read_text())
    receipt=replay(json.loads((ROOT/'fixtures/request.json').read_text()),json.loads((ROOT/'fixtures/response.json').read_text()))
    taxonomy=json.loads((ROOT/'schemas/taxonomy.json').read_text())
    body='<h1>Jev research fixture</h1><p>SYNTHETIC / OFFLINE • Not real inference or a performance benchmark</p><h2>Full record and evidence</h2><pre>'+html.escape(json.dumps(record,indent=2))+'</pre>'
    body+='<h2>Dominant angle × awareness</h2><p>One synthetic record; review-only, not accepted research. Funnel is separate and unclassified.</p><table><tr><th scope="col">Angle</th>'
    stages=[x for x in taxonomy['awareness'] if x!='review']
    body+=''.join('<th scope="col">'+html.escape(x)+'</th>' for x in stages)+'</tr>'
    for key,angle in taxonomy['angles'].items():
        if key=='review':continue
        body+='<tr><th scope="row">'+html.escape(angle['label'])+'</th>'+''.join('<td>'+str(int(key=='process_mechanism' and s=='solution_aware'))+'</td>' for s in stages)+'</tr>'
    body+='</table><h2>Replay receipt</h2><pre>'+html.escape(json.dumps(receipt,indent=2))+'</pre>'
    page="""<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src 'none'"><title>Jev synthetic evidence</title><style>body{font:16px/1.55 system-ui;max-width:1100px;margin:40px auto;padding:0 24px;color:#172033;background:#fafafa}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#fff;border:1px solid #cbd5e1;padding:20px}table{border-collapse:collapse;display:block;overflow:auto}td,th{padding:12px;border:1px solid #94a3b8;text-align:left}h2{margin-top:40px}</style><main>"""+body+"</main></html>"
    (out/'index.html').write_text(page)
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2))
    (out/'ad-record.json').write_text(json.dumps(record,indent=2))
    return receipt
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();build(a.out);print('Synthetic report saved; network_calls=0')
