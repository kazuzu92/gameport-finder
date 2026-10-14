#!/usr/bin/env python3
"""GamePort Finder V2: source aggregation, repository discovery and conservative archival.
Uses Python stdlib. This script does NOT download or redistribute copyrighted game files.
"""
import concurrent.futures
import json
import os
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'games.json'
SOURCES = [
    dict(id='ultimate',name='Ultimate Catalog of Web Game Ports',url='https://raw.githubusercontent.com/Carter54git/Ultimate-Catalog-Of-Web-Game-Ports/main/README.md',format='ultimate',site='https://github.com/Carter54git/Ultimate-Catalog-Of-Web-Game-Ports'),
    dict(id='decomp',name='Awesome Decomp Games',url='https://raw.githubusercontent.com/SubmitGame/awesome-decomp-games/main/README.md',format='decomp',site='https://github.com/SubmitGame/awesome-decomp-games'),
    dict(id='browser',name='Awesome Browser Game Ports',url='https://raw.githubusercontent.com/bitburner/Awesome-Browser-Game-Ports/main/README.md',format='browser',site='https://github.com/bitburner/Awesome-Browser-Game-Ports'),
]
LINK = re.compile(r'\[([^\]]+)\]\((https?://[^)\s]+)(?:\s+"[^"]*")?\)')
HEADERS={'User-Agent':'GamePortFinder/2.0 (public-source-index)','Accept':'application/vnd.github+json'}
TOKEN=os.environ.get('GITHUB_TOKEN','')
if TOKEN: HEADERS['Authorization']='Bearer '+TOKEN
QUERIES=['browser game port wasm in:name,description,readme','webassembly game port in:description','game decompilation web browser in:description','topic:browser-game','topic:webassembly-game']
PLATFORMS=['PS1','PS2','PS3','PS4','PS5','PSP','PS Vita','Wii','Wii U','GameCube','Nintendo DS','Nintendo 3DS','Nintendo 64','SNES','NES','GBA','Game Boy','Xbox 360','Xbox','Dreamcast','Arcade','PC','Android']
RULES=[('PS1',r'\b(?:ps1|psx|playstation\s*1)\b'),('PS2',r'\b(?:ps2|playstation\s*2)\b'),('PS3',r'\b(?:ps3|playstation\s*3)\b'),('PSP',r'\bpsp\b'),('GameCube',r'\bgame\s*cube\b'),('Wii',r'\bwii\b'),('Nintendo DS',r'\b(?:nintendo\s*ds|nds)\b'),('Nintendo 64',r'\b(?:n64|nintendo\s*64)\b'),('GBA',r'\b(?:gba|game\s*boy\s*advance)\b'),('SNES',r'\b(?:snes|super\s*nintendo)\b'),('PC',r'\b(?:windows|pc\s*game|dos\s*game)\b')]

def request(url,timeout=20,method='GET'):
    req=urllib.request.Request(url,headers=HEADERS,method=method)
    with urllib.request.urlopen(req,timeout=timeout) as r:return r.read().decode('utf-8','replace')

def safeurl(value):
    try:
        p=urllib.parse.urlsplit(value)
        if p.scheme not in ('http','https') or not p.hostname:return None
        if p.hostname.lower() in ('localhost','127.0.0.1','0.0.0.0','::1'):return None
        return value
    except (ValueError,TypeError):return None

def markdown_links(v):return [{'label':m[1].casefold(),'url':m[2]} for m in LINK.finditer(v)]
def text(v):return re.sub(r'[`*_~<>]','',LINK.sub(lambda m:m[1],v)).strip()
def canonical(v):
    v=re.sub(r'\s*\((?:[2-9]|web|browser|port)\)\s*$','',v,flags=re.I)
    v=''.join(c for c in unicodedata.normalize('NFKD',v).casefold() if not unicodedata.combining(c))
    return re.sub('[^a-z0-9]','',v)
def valid(v):return 2<len(v)<145 and v.casefold() not in ('game','title','name','source','demo','repository','---') and not re.fullmatch(r'[-: |]+',v)

def new_entry(name,source,demo=None,repo=None,**extras):
    e={'name':name,'demos':[],'repos':[],'sources':[source],'sourceLinks':[],'tags':[],'platforms':[]}
    if safeurl(demo):e['demos'].append(demo)
    if safeurl(repo):e['repos'].append(repo)
    e.update(extras)
    return e

def parse_ultimate(md,src):
    out=[]
    for line in md.splitlines():
        if not re.match(r'^\|\s*\d+\s*\|',line):continue
        cells=[x.strip() for x in line.strip().strip('|').split('|')]
        if len(cells)<4:continue
        name=text(cells[1]);dl=markdown_links(cells[2]);rl=markdown_links(cells[3]);demo=dl[0]['url'] if dl else None;repo=rl[0]['url'] if rl else None
        if valid(name):out.append(new_entry(name,src['id'],demo,repo,sourceLinks=[src['site']]))
    return out

def parse_other(md,src):
    out=[];heading='';in_browser=False
    for line in md.splitlines():
        h=re.match(r'^#{1,6}\s+(.*)',line)
        if h:
            heading=text(h[1]);in_browser=bool(re.search(r'browser|web ports|play in your browser|playable in browser|web games',heading,re.I));continue
        if src['format']=='decomp' and not in_browser:continue
        if line.strip().startswith('|'):
            cells=[x.strip() for x in line.strip().strip('|').split('|')]
            if len(cells)<2:continue
            name=text(cells[0]);ll=[l for c in cells for l in markdown_links(c)]
        elif src['format']=='browser' and re.match(r'^\s*[-*]\s+',line):
            ll=markdown_links(line);name=text(re.sub(r'^\s*[-*]\s+','',line).split(' - ')[0]);name=re.sub(r'\s*https?://.*$','',name).strip()
        else:continue
        if not valid(name) or not ll:continue
        repos=[x['url'] for x in ll if 'github.com/' in x['url'] or 'gitlab.com/' in x['url']]
        demos=[x['url'] for x in ll if 'github.com/' not in x['url'] and 'gitlab.com/' not in x['url'] and not re.search(r'\.(?:png|jpg|webp|gif|svg)(?:\?|$)',x['url'],re.I)]
        if demos or repos:out.append(new_entry(name,src['id'],demos[0] if demos else None,repos[0] if repos else None,sourceLinks=[src['site']]))
    return out

def discover():
    """Search GitHub public repositories; NOT treated as playable without a verified demo field."""
    found=[];count=0;errors=[]
    if not TOKEN:return found,{'id':'github-discovery','name':'GitHub — découverte de projets','url':'https://github.com/search','count':0,'ok':False,'error':'Token GitHub non configuré'}
    for q in QUERIES:
        try:
            u='https://api.github.com/search/repositories?'+urllib.parse.urlencode({'q':q,'per_page':50,'sort':'updated'})
            obj=json.loads(request(u))
            for r in obj.get('items',[]):
                if r.get('archived') or r.get('fork'):continue
                descr=(r.get('description') or '')[:280];full=r.get('full_name','')
                if not full or not re.search(r'game|port|emulat|wasm|webassembly|decomp|retro|browser',full+' '+descr,re.I):continue
                repo=safeurl(r.get('html_url'));homepage=safeurl(r.get('homepage'))
                # A homepage can be a project wiki; never mark it as a playable demo automatically.
                name=(r.get('name') or full.split('/')[-1]).replace('_',' ').replace('-',' ').strip()
                if not valid(name):continue
                found.append(new_entry(name,'github-discovery',repo=repo,sourceLinks=['https://github.com/search'],description=descr,projectUrl=homepage,updatedAt=r.get('pushed_at','')))
                count+=1
        except Exception as exc:errors.append(str(exc)[:90])
    return found,{'id':'github-discovery','name':'GitHub — découverte de projets','url':'https://github.com/search','count':count,'ok':not errors,'error':'; '.join(errors[:2])}

def infer_platforms(description):
    # Only infer from an explicit platform mention, not from an unrelated game title.
    return [platform for platform,pattern in RULES if re.search(pattern,description or '',re.I)]

# Small reviewed map: known releases; this does not infer that a given web project emulates them.
KNOWN_PLATFORMS={
    'dragonballzbudokaitenkaichi3':['PS2','Wii'],
    'proevolutionsoccer6':['PS2','PC'],
    'crashbashonline':['PS1'],
    'crashteamracing':['PS1'],
    'supermario64':['Nintendo 64'],
    'ocarinaoftime':['Nintendo 64'],
    'animalcrossing':['GameCube'],
    'thesimpsonshitandrun':['PS2','PC'],
    'grandtheftautovicecity':['PS2','PC'],
    'grandtheftauto3':['PS2','PC'],
    'tekken3':['PS1'],
    'sonicmania':['PC'],
    'halocombatevolved':['Xbox','PC'],
    'callofdutymodernwarfare2':['PC','PS3','Xbox 360'],
}

def enrich_repo_metadata(g,cache,limit):
    """Enrich a bounded number of GitHub projects per update; cached across runs."""
    if not g['repos'] or g.get('description') or limit[0] <= 0:return
    m=re.match(r'^https://github\.com/([^/]+)/([^/#?]+)',g['repos'][0])
    if not m:return
    key=(m[1]+'/'+m[2]).removesuffix('.git')
    if key in cache:info=cache[key]
    else:
        if limit[0]<=0:return
        limit[0]-=1
        try:
            info=json.loads(request('https://api.github.com/repos/'+key,timeout=9))
            cache[key]={'description':info.get('description') or '', 'topics':info.get('topics') or [],'homepage':info.get('homepage') or ''}
            info=cache[key]
        except Exception:return
    if info.get('description'):g['description']=info['description'][:350]
    more=' '.join([info.get('description','')]+info.get('topics',[]))
    g['platforms']=list(dict.fromkeys(g['platforms']+infer_platforms(more)))
    if not g.get('projectUrl') and safeurl(info.get('homepage')):g['projectUrl']=info['homepage']


def check_link(url):
    """A failed HTTP response is NOT a proof a game is unplayable."""
    for method in ('HEAD','GET'):
        try:
            req=urllib.request.Request(url,method=method,headers={'User-Agent':HEADERS['User-Agent'],'Range':'bytes=0-0'})
            with urllib.request.urlopen(req,timeout=6) as r:return 'responds'
        except urllib.error.HTTPError as exc:
            if exc.code in (401,403,405,429,503):
                if exc.code==405 and method=='HEAD':continue
                return 'unknown'
            if method=='HEAD':continue
            return 'error' if exc.code in (404,410) else 'unknown'
        except Exception:
            if method=='HEAD':continue
            return 'unknown'
    return 'unknown'

def build():
    previous={}
    if DATA.exists():
        try:previous={g['id']:g for g in json.loads(DATA.read_text(encoding='utf-8')).get('games',[]) if g.get('id')}
        except Exception as exc: print('Previous index error:',exc,file=sys.stderr)
    incoming=[];stats=[];success=set();seen={}
    for item in json.loads((ROOT/'data'/'curated.json').read_text(encoding='utf-8')):
        incoming.append(new_entry(item['name'],'curated',tags=item.get('tags',[]),platforms=item.get('platforms',[]),demos=item.get('demos',[]),repos=item.get('repos',[]),description=item.get('description',''),image=item.get('image','')))
    for src in SOURCES:
        try:
            md=request(src['url']);rows=parse_ultimate(md,src) if src['format']=='ultimate' else parse_other(md,src)
            if len(rows)<3:raise ValueError('Format inattendu ou catalogue trop court')
            incoming.extend(rows);success.add(src['id'])
            stats.append({'id':src['id'],'name':src['name'],'count':len(rows),'ok':True,'url':src['site']})
            print(src['id'],len(rows))
        except Exception as exc:
            stats.append({'id':src['id'],'name':src['name'],'count':0,'ok':False,'url':src['site'],'error':str(exc)[:130]})
            print('WARNING:',src['id'],exc,file=sys.stderr)
    if os.getenv('DISCOVER_GITHUB','1')=='1':
        rows,stat=discover();incoming.extend(rows);stats.append(stat)
        if stat['ok']:success.add('github-discovery')
    today=time.strftime('%Y-%m-%d',time.gmtime());merged={}
    metadata_path=ROOT/'data'/'repo_metadata_cache.json'
    try:repo_cache=json.loads(metadata_path.read_text(encoding='utf-8'))
    except Exception:repo_cache={}
    repo_budget=[int(os.getenv('MAX_REPO_ENRICH','50'))]
    for entry in incoming:
        key=canonical(entry['name'])
        if not key:continue
        seen.setdefault(key,set()).update(entry.get('sources',[]))
        if key not in merged:
            merged[key]={'id':key,'name':entry['name'],'demos':[],'repos':[],'sources':[],'sourceLinks':[],'tags':[],'platforms':[],'description':'','image':'','projectUrl':'','archived':False,'missingCycles':0,'linkChecks':{}}
        game=merged[key]
        for field in ('demos','repos','sources','sourceLinks','tags','platforms'):
            for val in entry.get(field,[]):
                if val and val not in game[field]:game[field].append(val)
        for field in ('description','image','projectUrl'):
            if not game[field] and entry.get(field):game[field]=entry[field]
        if len(entry['name'])<len(game['name']):game['name']=entry['name']
    for key,old in previous.items():
        if key not in merged:merged[key]={'id':key,'name':old['name'],'demos':[],'repos':[],'sources':[],'sourceLinks':[],'tags':[],'platforms':[],'description':'','image':'','projectUrl':'','archived':False,'missingCycles':0,'linkChecks':{}}
        g=merged[key]
        for field in ('demos','repos','sources','sourceLinks','tags','platforms'):
            for val in old.get(field,[]):
                if val and val not in g[field]:g[field].append(val)
        for field in ('description','image','projectUrl'):
            if not g[field] and old.get(field):g[field]=old[field]
        g['linkChecks']=old.get('linkChecks',{})
        g['missingCycles']=old.get('missingCycles',0)
        g['archived']=old.get('archived',False)
    # Only count removal when EVERY previously contributing live source succeeded this run.
    # If a project disappears from all its sources for 3 successful runs, archive it, never delete.
    for key,g in merged.items():
        old=previous.get(key,{})
        watched=set(s for s in old.get('sources',[]) if s!='curated')
        seen_now=seen.get(key,set())
        if seen_now or 'curated' in g['sources']:
            g['missingCycles']=0;g['archived']=False
        elif watched and watched.issubset(success):
            g['missingCycles']=int(old.get('missingCycles',0))+1
            if g['missingCycles']>=3:g['archived']=True
        g['platforms']=list(dict.fromkeys(g['platforms']+KNOWN_PLATFORMS.get(key,[])+infer_platforms(g.get('description',''))))
        enrich_repo_metadata(g,repo_cache,repo_budget)
        g['platforms']=list(dict.fromkeys(g['platforms']))
        g['type']='Lien de démonstration recensé' if g['demos'] else 'Dépôt / projet (non confirmé jouable)'
        if not g.get('image') and g['repos']:
            m=re.match(r'^https://github\.com/([^/]+)/([^/#?]+)',g['repos'][0])
            if m:g['image']='https://opengraph.githubassets.com/1/'+m[1]+'/'+m[2]
    # Link checks: bound cost and rotate across days, retaining last known results.
    if os.getenv('CHECK_LINKS','1')=='1':
        URLs=sorted(set(url for g in merged.values() for url in g['demos']))
        max_checks=max(0,int(os.getenv('MAX_LINK_CHECKS','120')))
        if URLs:
            offset=(int(time.time()//86400)*max_checks)%len(URLs)
            sample=(URLs+URLs)[offset:offset+min(max_checks,len(URLs))]
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:checks=dict(pool.map(lambda u:(u,check_link(u)),sample))
            for g in merged.values():
                for url in g['demos']:
                    if url not in checks:continue
                    prev=g['linkChecks'].get(url,{})
                    if isinstance(prev,str):prev={'status':prev,'failures':0}
                    status=checks[url];fail=int(prev.get('failures',0))+1 if status=='error' else 0 if status=='responds' else int(prev.get('failures',0))
                    g['linkChecks'][url]={'status':'suspect' if fail>=3 else status,'failures':fail,'checkedAt':today}
    games=sorted(merged.values(),key=lambda x:x['name'].casefold())
    obj={'version':2,'generatedAt':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'total':len(games),'sources':stats,'games':games,'disclaimer':'Catalogue de liens tiers. Vérification HTTP ne prouve pas que le jeu est jouable. Pas de ROM hébergée.'}
    # Avoid replacing a healthy index with a tiny fallback after an outage.
    if not success and len(previous)>10:print('All external sources failed; existing index preserved',file=sys.stderr);return
    metadata_path.write_text(json.dumps(repo_cache,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    DATA.write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(f'Built {len(games)} games ({sum(bool(g["archived"]) for g in games)} archived), {len(success)} successful feeds')
if __name__=='__main__':build()
