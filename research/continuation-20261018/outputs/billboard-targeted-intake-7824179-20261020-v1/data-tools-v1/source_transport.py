"""Bounded public HTML evidence collection. No photos, credentials or rights approval."""
from pathlib import Path
from datetime import datetime, timezone
from html.parser import HTMLParser
import argparse
import gzip
import hashlib
import json
import re
import time
import urllib.request
import urllib.parse

PAGE_CAP=2_000_000
TOTAL_CAP=110_000_000


def sha(body): return hashlib.sha256(body).hexdigest()
def utc(): return datetime.now(timezone.utc).isoformat()
def write(path,value):
    temporary=path.with_suffix(path.suffix+'.partial')
    temporary.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    temporary.replace(path)


def checked_url(url):
    u=urllib.parse.urlsplit(url)
    if (u.scheme!='https' or u.hostname not in {'www.flickr.com','flickr.com'} or u.username or u.password
        or u.query or u.fragment or u.port is not None or not re.fullmatch(r'/photos/[a-zA-Z0-9_@-]+/[0-9]+/?',u.path)):
        raise ValueError('Only exact public Flickr photo landing pages are accepted')
    return url


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,msg,headers,newurl):
        checked_url(newurl)  # Do not follow login, image, external-host or token redirects.
        return super().redirect_request(request,fp,code,msg,headers,newurl)


class LicenseLinks(HTMLParser):
    def __init__(self): super().__init__(); self.links=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='a' and 'href' in a:
            url=urllib.parse.urlsplit(a['href'])
            if (url.hostname in {'creativecommons.org','www.creativecommons.org'} and url.path.startswith('/licenses/')
                and not url.username and not url.password and not url.query and not url.fragment):
                self.links.append({'url':a['href'],'class':a.get('class',''),'rel':a.get('rel','')})


def load_plan(path):
    plan=json.loads(path.read_text(encoding='utf-8'))
    assert plan['schema']==1 and plan['purpose']=='public-source-evidence-only'
    assert plan['approved_for_training'] is False
    rows=plan['images']
    assert len(rows)==55 and len({r['image_id'] for r in rows})==55
    excluded=set(plan['excluded_image_ids'])
    assert len(excluded)==5 and not any(r['image_id'] in excluded for r in rows)
    for r in rows:
        assert re.fullmatch('[0-9a-f]{16}',r['image_id'])
        checked_url(r['source_url'])
    return plan


def fetch(url):
    request=urllib.request.Request(checked_url(url),headers={'User-Agent':'FrameTrail public attribution evidence review (no image downloads)'})
    with urllib.request.build_opener(SafeRedirect()).open(request,timeout=10) as response:
        checked_url(response.geturl())
        content_type=response.headers.get_content_type()
        if content_type not in {'text/html','application/xhtml+xml'}:
            raise ValueError('Non-HTML response refused; photographs are not fetched')
        if response.headers.get('Content-Length') and int(response.headers['Content-Length'])>PAGE_CAP:
            raise ValueError('Source page exceeds 2 MB limit')
        body=response.read(PAGE_CAP+1)
        if len(body)>PAGE_CAP: raise ValueError('Source page exceeds 2 MB limit')
        charset=response.headers.get_content_charset() or 'utf-8'
        parser=LicenseLinks();parser.feed(body.decode(charset,'replace'))
        return body,{'http_status':response.status,'final_url':response.geturl(),'content_type':content_type,
                     'candidate_license_links':list({json.dumps(x,sort_keys=True):x for x in parser.links}.values())}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan',type=Path,required=True)
    ap.add_argument('--output',type=Path)
    ap.add_argument('--check-only',action='store_true')
    args=ap.parse_args()
    plan=load_plan(args.plan)
    if args.check_only:
        print(json.dumps({'plan_valid':True,'images':55,'excluded':5,'photographs_downloaded':0,'approved_for_training':False}))
        return
    if not args.output: ap.error('--output is required for evidence collection')
    args.output.mkdir(parents=True,exist_ok=False)
    (args.output/'pages').mkdir()
    report={'schema':1,'purpose':'public-source-evidence-only','status':'running','started_at_utc':utc(),
            'plan_sha256':sha(args.plan.read_bytes()),'annotation_sha256':plan['annotation_sha256'],
            'planned_images':55,'page_cap_bytes':PAGE_CAP,'total_raw_html_cap_bytes':TOTAL_CAP,
            'html_bytes':0,'photographs_downloaded':0,'rights_verified':False,'approved_for_training':False,'images':[],
            'limits':'Fetched HTML and extracted links are evidence, not licence or intended-use clearance. Errors do not prove a licence is absent. No login, access-control workaround or alternate endpoint is used.'}
    write(args.output/'source-evidence.json',report)
    for number,row in enumerate(plan['images'],1):
        record={'photo':row['photo'],'image_id':row['image_id'],'source_url':row['source_url'],
                'publisher_license_url':row['license_url'],'checked_at_utc':utc(),'rights_verified':False}
        try:
            body,meta=fetch(row['source_url'])
            if report['html_bytes']+len(body)>TOTAL_CAP: raise ValueError('Total HTML byte cap exceeded')
            page=args.output/'pages'/(row['image_id']+'.html.gz')
            page.write_bytes(gzip.compress(body,mtime=0))
            record.update(meta,status='retrieved-unreviewed',page_file=page.relative_to(args.output).as_posix(),
                          html_bytes=len(body),html_sha256=sha(body),stored_sha256=sha(page.read_bytes()))
            report['html_bytes']+=len(body)
        except (OSError,ValueError,AssertionError) as error:
            record.update(status='unavailable',error_type=type(error).__name__,error=str(error)[:500])
        report['images'].append(record)
        write(args.output/'source-evidence.json',report)
        print(f"{number}/55 photo {row['photo']}: {record['status']}",flush=True)
        time.sleep(.2)
    unavailable=sum(r['status']=='unavailable' for r in report['images'])
    report.update(status='completed-with-unavailable-sources' if unavailable else 'completed-evidence-collection',
                  finished_at_utc=utc(),retrieved_images=55-unavailable,unavailable_images=unavailable)
    write(args.output/'source-evidence.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='images'},indent=2))
    if unavailable: raise SystemExit(2)


if __name__=='__main__': main()
