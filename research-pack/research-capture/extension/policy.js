export const VERSION='0.2.1';
export const HOST='com.jev.research_capture';
export function cleanURL(value){
 const u=new URL(value);
 if(!['https:','http:'].includes(u.protocol)||u.username||u.password||u.port)throw Error('Use a public HTTP(S) URL without credentials or custom ports.');
 const h=u.hostname.toLowerCase().replace(/\.+$/,'');u.hostname=h;
 if(h==='localhost'||h.endsWith('.local')||h.endsWith('.internal')||h.endsWith('.localhost')||/^(127\.|10\.|192\.168\.|169\.254\.|172\.(1[6-9]|2\d|3[01])\.)/.test(h))throw Error('Private origins are blocked.');
 const keep=new URLSearchParams();for(const k of ['v','id','view_all_page_id']){const v=u.searchParams.get(k);if(v&&/^[\w-]{1,128}$/.test(v))keep.set(k,v);}
 u.search=keep.toString();u.hash='';return u.href;
}
export function classify(value){
 const u=new URL(cleanURL(value)),h=u.hostname;
 if(h==='instagram.com'||h.endsWith('.instagram.com'))return 'instagram_handoff';
 if(['youtube.com','www.youtube.com','m.youtube.com','youtu.be'].includes(h))return 'youtube';
 if(['facebook.com','www.facebook.com'].includes(h)){
  if(u.pathname==='/ads/library'||u.pathname.startsWith('/ads/library/'))return 'meta_ad_library';
  if(/^\/(?:[A-Za-z0-9_.-]+\/posts\/[A-Za-z0-9_.-]+\/?|(?:reel|watch)\/[A-Za-z0-9_.-]+\/?)$/.test(u.pathname))return 'facebook';
  throw Error('Unsupported/private Facebook surface.');
 }
 if(['x.com','www.x.com','twitter.com','www.twitter.com'].includes(h)){if(!/^\/[A-Za-z0-9_]+\/status\/[0-9]+\/?$/.test(u.pathname))throw Error('Only public X post references supported.');return 'x';}
 return 'web';
}
export function redact(s){return String(s||'').replace(/(bearer\s+[\w.-]{16,}|sk-[\w-]{16,}|(?:api[_-]?key|password|access[_-]?token|secret)\s*[:=]\s*\S+)/gi,'[REDACTED]');}
