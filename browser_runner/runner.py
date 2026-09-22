"""Ten-worker, approval-gated public Meta Ad Library observer.

Live collection is deliberately off by default. Each worker invokes the licensed
Browser Use + Jev upstream adapter and emits authenticated loopback cockpit events.
"""
import argparse, concurrent.futures, json, os, shutil, sys, tempfile, uuid, threading, multiprocessing, queue, time
from datetime import datetime, timezone
from pathlib import Path
from .events import CockpitClient
from .policy import PolicyError, meta_library_url
from . import upstream_adapter

MAX_WORKERS = 10

def load_companies(path):
    raw = json.loads(Path(path).read_text())
    companies = raw if isinstance(raw, list) else raw.get("companies", raw.get("advertisers")) if isinstance(raw, dict) else None
    if not isinstance(companies, list) or not companies:
        raise ValueError("input JSON must contain a nonempty companies array")
    if len(companies) > 50: raise ValueError("at most 50 companies per run")
    seen, cleaned = set(), []
    for item in companies:
        if not isinstance(item, dict): raise ValueError("each company must be an object")
        name, page_id = str(item.get("name", "")).strip(), str(item.get("page_id", "")).strip()
        if not name or len(name) > 240 or any(ord(c) < 32 for c in name) or not page_id.isdigit() or len(page_id) > 32:
            raise ValueError("each company needs a bounded printable name and numeric page_id")
        if page_id in seen: raise ValueError("page_id values must be unique")
        seen.add(page_id); cleaned.append({"name": name, "page_id": page_id})
    return cleaned

def make_plan(companies, workers):
    return {"mode": "planned", "source": "public Meta Ad Library", "company_count": len(companies),
      "worker_count": workers, "approval_required": ["--execute", "--approve-live-collection"],
      "browser": "Browser Use + Jev upstream adapter", "limits": [
        "No local browser/profile/cookie fallback", "No Instagram browser or UI automation",
        "Visible public-page observations only; not a complete inventory, spend, or performance claim",
        "Source blockages and unresolved identity are distinct from zero ads"],
      "companies": [{**c, "url": meta_library_url(c["page_id"])} for c in companies]}

def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2) + "\n")
    try: temp.chmod(0o600)
    except OSError: pass
    temp.replace(path)

def work(index, company, run_id, output, client, worker_id, use_jev=False, emit_start=True):
    url = meta_library_url(company["page_id"])
    if emit_start:
        client.emit(run_id, worker_id, "worker_started", company=company["name"], url=url,
                    detail={"company_index": index + 1, "page_id": company["page_id"], "job_id": f"{index+1:03d}-{company['page_id']}"})
    job_dir = output / "workers" / f"{index + 1:03d}-{company['page_id']}"
    job = {"company": company, "url": url, "output": str(job_dir)}
    try:
        result = upstream_adapter.collect(job)
        outcome = result.get("outcome", "source_error")
        if use_jev:
            from .jev_review import review
            judgment=review(company=company['name'], url=url, page_text=result.pop('_review_text',''))
            result.setdefault('detail', {})['jev_review']=judgment
            expected={'active_ads':'active','no_active_ads':'none','source_blocked':'blocked'}
            if judgment['choice'] != expected.get(outcome, 'review') or judgment['confidence'] < .8:
                outcome='identity_unresolved'
        ads = int(result.get("ads", 0))
        event_type = {"active_ads": "observation", "no_active_ads": "zero_ads",
                      "source_blocked": "source_blocked", "identity_unresolved": "worker_failed",
                      "source_error": "worker_failed"}.get(outcome, "worker_failed")
        detail = {"outcome": outcome, "job_id": f"{index+1:03d}-{company['page_id']}", **(result.get("detail") or {})}
        # Failure states are terminal; emit exactly one of them so the cockpit cannot overwrite state.
        if outcome in {"active_ads", "no_active_ads", "source_blocked"}:
            client.emit(run_id, worker_id, event_type, company=company["name"], url=url, ads=ads, detail=detail)
        if outcome in {"active_ads", "no_active_ads"}:
            client.emit(run_id, worker_id, "worker_complete", company=company["name"], url=url, ads=ads,
                        detail={"outcome": outcome, "job_id": detail["job_id"]})
        elif outcome != "source_blocked":
            client.emit(run_id, worker_id, "worker_failed", company=company["name"], url=url, ads=ads,
                        detail={"outcome": outcome, "job_id": detail["job_id"]})
        row = {"company": company, "url": url, "worker_id": worker_id, "outcome": outcome, "ads": ads, "detail": detail}
    except Exception as exc:
        row = {"company": company, "url": url, "worker_id": worker_id, "outcome": "source_error", "ads": 0,
               "detail": {"reason": type(exc).__name__, "message": str(exc), "job_id": f"{index+1:03d}-{company['page_id']}"}}
        client.emit(run_id, worker_id, "worker_failed", company=company["name"], url=url, ads=0, detail=row["detail"])
    write_json(job_dir / "result.json", row)
    return row

def _job_process(index, company, run_id, output_s, port, token, worker_id, seq_base, use_jev, result_queue):
    """One process per company. Browser Harness imports/cached routes cannot survive a job."""
    client=CockpitClient(port, token, initial_seq={worker_id: seq_base})
    row=work(index, company, run_id, Path(output_s), client, worker_id, use_jev, emit_start=False)
    result_queue.put((index, row))

def execute(companies, workers, output, client, *, use_jev=False, worker_timeout=210):
    run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    output.mkdir(parents=True, exist_ok=False)
    try: output.chmod(0o700)
    except OSError: pass
    client.emit(run_id, "coordinator", "run_started", detail={"companies": len(companies), "workers": workers,
        "mode": "public_meta_library_observe_only", "jev_review": use_jev})
    # New spawned process per company, bounded to ten concurrent slots. Never reuse Browser Harness state.
    context=multiprocessing.get_context('spawn'); results=context.Queue(); pending=list(enumerate(companies)); active={}; rows=[]; stopped=False; free_slots=list(range(workers))
    port=int(client.url.rsplit(':',1)[1].split('/')[0])
    def launch():
        while pending and free_slots and not stopped:
            index, company=pending.pop(0); slot=free_slots.pop(0); worker_id=f"worker-{slot+1:02d}"; seq_base=index*10
            # Parent creates the durable cockpit receipt before a child can crash.
            client._seq[worker_id]=seq_base
            client.emit(run_id,worker_id,"worker_started",company=company['name'],url=meta_library_url(company['page_id']),detail={"company_index":index+1,"page_id":company['page_id'],"job_id":f"{index+1:03d}-{company['page_id']}"})
            proc=context.Process(target=_job_process,args=(index,company,run_id,str(output),port,client.token,worker_id,seq_base+1,use_jev,results))
            proc.start(); active[index]=(proc,company,worker_id,slot,time.monotonic(),seq_base)
    launch()
    def record_failed(index, item, reason):
        proc,company,worker_id,slot,_,seq_base=item
        client._seq[worker_id]=seq_base+9
        detail={"reason":reason,"cleanup_status":"unconfirmed_after_parent_termination" if reason=="worker_timeout" else "not_applicable","job_id":f"{index+1:03d}-{company['page_id']}"}
        row={"company":company,"url":meta_library_url(company['page_id']),"worker_id":worker_id,"outcome":"source_error","ads":0,"detail":detail}
        write_json(output/'workers'/f"{index+1:03d}-{company['page_id']}"/'result.json',row)
        client.emit(run_id,worker_id,"worker_failed",company=company['name'],url=row['url'],ads=0,detail=detail)
        return row
    while active:
        try:
            index,row=results.get(timeout=.25)
        except queue.Empty:
            now=time.monotonic(); failed=None
            for candidate,item in active.items():
                proc,_,_,_,started,_=item
                if proc.exitcode is not None: failed=(candidate,item,'child_exited_without_result'); break
                if now-started > worker_timeout: failed=(candidate,item,'worker_timeout'); break
            if failed is None: continue
            index,item,reason=failed; active.pop(index); proc,_,_,slot,_,_=item
            if proc.is_alive(): proc.terminate(); proc.join(timeout=5)
            row=record_failed(index,item,reason)
        else:
            item=active.pop(index); proc,_,_,slot,_,_=item; proc.join(timeout=1)
            if proc.is_alive(): proc.terminate(); proc.join(timeout=5)
        free_slots.append(slot); free_slots.sort(); rows.append(row)
        if row['outcome'] not in {'active_ads','no_active_ads'}: stopped=True
        if not stopped: launch()
    for index,company in pending:
        row={"company":company,"url":meta_library_url(company['page_id']),"worker_id":"unassigned","outcome":"unobserved_after_stop","ads":0,"detail":{"reason":"another job reported a failure","job_id":f"{index+1:03d}-{company['page_id']}"}}
        write_json(output/'workers'/f"{index+1:03d}-{company['page_id']}"/'result.json',row); rows.append(row)
    rows.sort(key=lambda r: int(r['detail'].get('job_id','0').split('-')[0]))
    summary={"run_id":run_id,"companies":len(rows),"active_ads":sum(r['outcome']=='active_ads' for r in rows),"zero_ads":sum(r['outcome']=='no_active_ads' for r in rows),"blocked":sum(r['outcome']=='source_blocked' for r in rows),"unresolved_or_error":sum(r['outcome'] not in {'active_ads','no_active_ads','source_blocked','unobserved_after_stop'} for r in rows),"unobserved_after_stop":sum(r['outcome']=='unobserved_after_stop' for r in rows),"visible_ads":sum(r['ads'] for r in rows),"results":rows}
    summary['status']='complete' if not (summary['blocked'] or summary['unresolved_or_error']) else 'stopped_needs_review'
    write_json(output/'summary.json',summary)
    client.emit(run_id,"coordinator","run_complete",ads=summary['visible_ads'],detail={k:summary[k] for k in summary if k not in {'run_id','results'}})
    return summary

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--companies", required=True, help="JSON: [{name,page_id}] or {companies:[...]}")
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--output", default="runs")
    parser.add_argument("--cockpit-port", type=int)
    parser.add_argument("--cockpit-token", help="Deprecated: use JEV_COCKPIT_TOKEN environment variable")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--approve-live-collection", action="store_true")
    parser.add_argument("--approve-paid-jev", action="store_true", help="Allow one review-only Jev decision per observed company")
    args = parser.parse_args(argv)
    if not 1 <= args.workers <= MAX_WORKERS: parser.error("--workers must be 1-10")
    companies = load_companies(args.companies)
    if not args.execute:
        print(json.dumps(make_plan(companies, args.workers), indent=2)); return 0
    if not args.approve_live_collection:
        parser.error("live collection requires --approve-live-collection")
    cockpit_token = os.environ.get("JEV_COCKPIT_TOKEN", "").strip() or (args.cockpit_token or "")
    if not args.cockpit_port or not cockpit_token:
        parser.error("live collection requires --cockpit-port and JEV_COCKPIT_TOKEN")
    if args.approve_paid_jev and not os.environ.get('OPENROUTER_JEV_API_KEY'):
        parser.error("--approve-paid-jev requires OPENROUTER_JEV_API_KEY in your environment")
    client = CockpitClient(args.cockpit_port, cockpit_token)
    summary = execute(companies, args.workers, Path(args.output).resolve(), client, use_jev=args.approve_paid_jev)
    print(json.dumps(summary, indent=2)); return 0

if __name__ == "__main__":
    raise SystemExit(main())
