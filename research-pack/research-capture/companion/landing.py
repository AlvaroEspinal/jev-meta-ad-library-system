"""Explicit public-page extraction; never executes JavaScript or follows links."""
from html.parser import HTMLParser
from urllib.parse import urlsplit
from core import CaptureError,url
from media import PinnedHTTPS,public_addresses
class Page(HTMLParser):
 def __init__(self):
  super().__init__();self.skip=0;self.stack=[];self.items=[];self.current=None
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if self.skip or tag in {'script','style','noscript','form','iframe','template'} or 'hidden' in a or a.get('aria-hidden')=='true':
   if tag not in {'meta','link','input','img','br','hr','source'}:self.skip+=1
   return
  if tag in {'h1','h2','h3','p','a','button'}:self.current={'tag':tag,'text':''}
 def handle_endtag(self,tag):
  if self.skip:self.skip-=1;return
  if self.current and tag==self.current['tag']:
   text=' '.join(self.current['text'].split())
   if text:self.items.append({'tag':tag,'text':text[:3000]})
   self.current=None
 def handle_data(self,data):
  if not self.skip and self.current:self.current['text']+=data+' '
def extract(body,source):
 p=Page();p.feed(body);items=p.items[:100]
 return {'status':'captured','source_url':url(source),'method':'static-html-no-js','fields':{'headline':next((x['text'] for x in items if x['tag']=='h1'),None),'subheadline':None,'offer':None,'cta_candidates':[x['text'] for x in items if x['tag'] in {'a','button'}],'proof':None,'structure':items,'claims':None},'limitations':['Static HTML only, not rendered browser text','Offer, proof and claims require reviewed evidence; not inferred from paragraphs']}
def fetch(source,allowed_hosts):
 u=urlsplit(url(source));raw=urlsplit(source)
 if u.scheme!='https' or u.hostname not in allowed_hosts or raw.query:raise CaptureError('Landing fetch requires exact approved public HTTPS host and unsigned URL')
 if any(u.hostname==h or u.hostname.endswith('.'+h) for h in ('instagram.com','facebook.com','youtube.com','x.com','twitter.com')):raise CaptureError('Platform/private routes are not landing-page targets')
 conn=PinnedHTTPS(u.hostname,public_addresses(u.hostname)[0])
 try:
  conn.request('GET',u.path or '/',headers={'User-Agent':'ResearchCapture/0.2','Accept':'text/html'})
  r=conn.getresponse()
  if r.status!=200 or r.getheader('Content-Type','').split(';')[0].lower()!='text/html':raise CaptureError('Landing inaccessible/unsupported; no redirects or challenge bypass')
  data=r.read(1_000_001)
  if len(data)>1_000_000:raise CaptureError('Landing exceeds 1 MB cap')
  return extract(data.decode('utf-8',errors='replace'),source)
 finally:conn.close()
