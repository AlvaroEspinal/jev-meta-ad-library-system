"""Offline synthetic ten-worker replay. Never contacts a browser, model, or ad source."""
import argparse, time, uuid, os
from .events import CockpitClient

def main(argv=None):
 p=argparse.ArgumentParser(); p.add_argument('--cockpit-port',type=int,required=True);p.add_argument('--cockpit-token');p.add_argument('--workers',type=int,default=10);p.add_argument('--delay-ms',type=int,default=25); args=p.parse_args(argv)
 if not 1<=args.workers<=10: p.error('--workers must be 1-10')
 token=os.environ.get('JEV_COCKPIT_TOKEN','').strip() or (args.cockpit_token or '')
 if not token: p.error('set JEV_COCKPIT_TOKEN')
 c=CockpitClient(args.cockpit_port,token); run='fixture-ten-worker-'+uuid.uuid4().hex[:8]; total=0
 c.emit(run,'coordinator','run_started',detail={'fixture':True,'workers':args.workers})
 for i in range(args.workers):
  w=f'worker-{i+1:02d}'; company=f'Fixture Company {i+1}'; url=f'https://www.facebook.com/ads/library/?view_all_page_id={1000+i}'; job={'fixture':True,'job_id':f'{i+1:03d}-{1000+i}'}
  c.emit(run,w,'worker_started',company=company,url=url,detail=job)
  if i==7: c.emit(run,w,'source_blocked',company=company,url=url,ads=0,detail={**job,'outcome':'source_blocked'})
  elif i==8: c.emit(run,w,'zero_ads',company=company,url=url,ads=0,detail={**job,'outcome':'no_active_ads'}); c.emit(run,w,'worker_complete',company=company,url=url,ads=0,detail={**job,'outcome':'no_active_ads'})
  else:
   ads=i+1; total+=ads; c.emit(run,w,'observation',company=company,url=url,ads=ads,detail={**job,'outcome':'active_ads'}); c.emit(run,w,'worker_complete',company=company,url=url,ads=ads,detail={**job,'outcome':'active_ads'})
  time.sleep(args.delay_ms/1000)
 c.emit(run,'coordinator','run_complete',ads=total,detail={'fixture':True,'active_ads':8,'zero_ads':1,'blocked':1,'status':'complete'})
if __name__=='__main__': main()
