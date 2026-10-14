#!/usr/bin/env python3
"""Static index builder: public markdown catalogues + optional curated entries.
No third-party dependencies or keys required. GitHub API enrichment requires GITHUB_TOKEN.
"""
import json, os, re, sys, time, urllib.request, urllib.error, unicodedata
from pathlib import Path
from urllib.parse import urlparse
ROOT=Path(__file__).resolve().parents[1]
SOURCES=[
 {"id":"ultimate","name":"Ultimate Catalog of Web Game Ports","url":"https://raw.githubusercontent.com/Carter54git/Ultimate-Catalog-Of-Web-Game-Ports/main/README.md","format":"ultimate","site":"https://github.com/Carter54git/Ultimate-Catalog-Of-Web-Game-Ports"},
 {"id":"decomp","name":"Awesome Decomp Games","url":"https://raw.githubusercontent.com/SubmitGame/awesome-decomp-games/main/README.md","format":"decomp","site":"https://github.com/SubmitGame/awesome-decomp-games"},
 {"id":"browser","name":"Awesome Browser Game Ports","url":"https://raw.githubusercontent.com/bitburner/Awesome-Browser-Game-Ports/main/README.md","format":"browser","site":"https://github.com/bitburner/Awesome-Browser-Game-Ports"}
]
UA='GamePortFinder/1.0 (+https://github.com/)'
LINK=re.compile(r'\[([^\]]+)\]\((https?://[^)\s]+)(?:\s+"[^"]*")?\)')

def get(url,timeout=24):
 req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'text/plain, application/json;q=0.8'})
 with urllib.request.urlopen(req,timeout=timeout) as r: return r.read().decode('utf-8','replace')

def text(s):
 s=LINK.sub(lambda m:m.group(1),s)
 return re.sub(r'[`*_~<>]','',s).strip()

def links(s): return [{'label':m.group(1).lower(),'url':m.group(2)} for m in LINK.finditer(s)]

def valid(s):
 if not s or len(s)>150: return False
 if s.lower() in ('game','title','name','games','demo','port','project','source','repository','---'): return False
 if re.match(r'^[-:|\s]+$',s):return False
 return True

def canon(s):
 s=re.sub(r'\s*\((?:[2-9]|gamecube|web|browser|port)\)\s*$','',s,flags=re.I)
 s=unicodedata.normalize('NFKD',s).casefold()
 s=''.join(c for c in s if not unicodedata.combining(c))
 return re.sub('[^a-z0-9]+','',s)

def cleanurl(url):
 try:
  p=urlparse(url)
  return url if p.scheme in ('http','https') and p.netloc and not any(x in p.netloc for x in ['localhost','127.0.0.1']) else ''
 except Exception:return ''

def parse_ultimate(md,src):
 out=[]
 for line in md.splitlines():
  if not re.match(r'^\|\s*\d+\s*\|',line): continue
  c=[x.strip() for x in line.strip().strip('|').split('|')]
  if len(c)<4:continue
  name=text(c[1]); demo=next((x['url'] for x in links(c[2])),None); repo=next((x['url'] for x in links(c[3])),None)
  if valid(name):out.append(entry(name,demo,repo,src))
 return out

def entry(name,demo,repo,src):
 return {'name':name,'demos':[u for u in [cleanurl(demo)] if u],'repos':[u for u in [cleanurl(repo)] if u], 'sources':[src['id']], 'sourceLinks':[src['site']]}

def parse_other(md,src):
 out=[]; heading=''; in_browser=False
 for line in md.splitlines():
  h=re.match(r'^#{1,6}\s+(.*)',line)
  if h:
   heading=text(h[1]);in_browser=bool(re.search(r'browser|web ports|play in your browser|playable in browser|web games',heading,re.I));continue
  if src['format']=='decomp' and not in_browser:continue
  if line.strip().startswith('|'):
   c=[x.strip() for x in line.strip().strip('|').split('|')]
   if len(c)<2 or re.match(r'^[-: ]+$',c[0]):continue
   name=text(c[0]); ll=[a for cell in c for a in links(cell)]
  elif src['format']=='browser' and re.match(r'^\s*[-*]\s+',line):
   ll=links(line);name=text(re.sub(r'^\s*[-*]\s+','',line).split(' - ')[0]);name=re.sub(r'\s*https?://.*$','',name).strip()
  else:continue
  if not valid(name) or not ll:continue
  repo=next((x['url'] for x in ll if 'github.com/' in x['url'] or 'gitlab.com/' in x['url']),None)
  # First linked title is often itself the actual demo (browser list). For decomp, first link is often a GitHub repo.
  demo=next((x['url'] for x in ll if not ('github.com/' in x['url'] or 'gitlab.com/' in x['url']) and not x['url'].endswith(('.png','.jpg','.webp','.gif'))),None)
  if demo or repo:out.append(entry(name,demo,repo,src))
 return out

def build():
 raw=[];stats=[]
 curated=ROOT/'data'/'curated.json'
 if curated.exists():
  for e in json.loads(curated.read_text(encoding='utf-8')):
   raw.append({'name':e['name'],'demos':e.get('demos',[]),'repos':e.get('repos',[]),'sources':['curated'],'sourceLinks':[],'tags':e.get('tags',[]),'platforms':e.get('platforms',[])})
 for src in SOURCES:
  try:
   md=get(src['url']);rows=parse_ultimate(md,src) if src['format']=='ultimate' else parse_other(md,src)
   if len(rows)<3:raise ValueError('Format not recognized or too few entries')
   raw.extend(rows);stats.append({'name':src['name'],'count':len(rows),'ok':True,'url':src['site']});print(src['id'],len(rows))
  except Exception as ex:
   print('WARNING',src['id'],str(ex),file=sys.stderr)
   stats.append({'name':src['name'],'count':0,'ok':False,'url':src['site'],'error':str(ex)[:100]})
 # fallback: preserve last good index when one or more feeds fail; never throw away existing data
 prevfile=ROOT/'data'/'games.json'
 if prevfile.exists():
  try:
   prev=json.loads(prevfile.read_text(encoding='utf-8'))
   for g in prev.get('games',[]):
    raw.append({k:g.get(k,[]) for k in ['name','demos','repos','sources','sourceLinks','tags','platforms']})
  except Exception:pass
 merged={}
 for e in raw:
  key=canon(e['name']);
  if len(key)<2:continue
  if key not in merged:merged[key]={'id':key,'name':e['name'],'demos':[],'repos':[],'sources':[],'sourceLinks':[],'tags':[],'platforms':[]}
  g=merged[key]
  for f in ['demos','repos','sources','sourceLinks','tags','platforms']:
   for x in e.get(f,[]):
    if x and x not in g[f]:g[f].append(x)
  if e['name'] and len(e['name'])<len(g['name']) and not re.search(r'\([2-9]\)',e['name']):g['name']=e['name']
 games=sorted(merged.values(),key=lambda g:g['name'].casefold())
 for g in games:
  g['type']='Jouable (lien signalé)' if g['demos'] else 'Projet / dépôt'
 # Optional *bounded* link check; each result explicitly describes URL responsiveness, not playability
 if os.getenv('CHECK_LINKS')=='1':
  import concurrent.futures
  unique=sorted(set(u for g in games for u in g['demos']))[:600]
  def check(url):
   try:
    req=urllib.request.Request(url,method='HEAD',headers={'User-Agent':UA})
    with urllib.request.urlopen(req,timeout=6) as res:return url,'responds' if res.status<400 else 'error'
   except urllib.error.HTTPError as e:return url,'unknown' if e.code in (403,405,429) else 'error'
   except Exception:return url,'unknown'
  with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:health=dict(pool.map(check,unique))
  for g in games:g['linkChecks']={u:health.get(u,'unchecked') for u in g['demos']}
 obj={'generatedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'total':len(games),'sources':stats,'games':games,'disclaimer':'Liens publics indexés, non testés en jeu. Les droits et la compatibilité dépendent des projets.'}
 prevfile.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
 print('Built',len(games),'unique games')
 if not any(s['ok'] for s in stats) and not prevfile.exists():sys.exit(1)
if __name__=='__main__':build()
