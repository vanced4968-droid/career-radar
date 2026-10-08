#!/usr/bin/env python3
"""Low-volume public recruitment metadata refresh; never uses credentials or hidden APIs."""
from __future__ import annotations
import hashlib, json, os, re, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "data" / "jobs.json"
KST = timezone(timedelta(hours=9))
NOW = datetime.now(KST)
JK = "https://www.jobkorea.co.kr/starter/calendar"
JS = "https://jasoseol.com/search"
UA = "CareerRadar-PersonalCalendar/1.1 (public jobs metadata, noncommercial)"
S = requests.Session()
S.headers.update({"User-Agent":UA, "Accept-Language":"ko-KR,ko;q=0.9",
                  "Accept":"text/html,application/xhtml+xml"})
SOURCE_DIAGNOSTICS = {}
KINDS = {"한국서부발전":"공기업","한국남부발전":"공기업","국가철도공단":"공기업",
         "인천공항시설관리":"공기업","LS ELECTRIC":"대기업","현대오토에버":"대기업",
         "CJ대한통운":"대기업","삼천리":"대기업","S-OIL":"대기업",
         "KT DS":"대기업","HL Klemove":"대기업","이마트":"대기업",
         "오뚜기":"대기업","DN솔루션즈":"중견기업"}

def permitted(url):
    p=urlsplit(url)
    address=p.scheme+"://"+p.netloc+"/robots.txt"
    r=S.get(address,timeout=18)
    if r.status_code==404: return True
    r.raise_for_status()
    if "html" in r.headers.get("Content-Type","").lower():
        raise RuntimeError("robots.txt returned HTML; refusing crawl")
    robots=RobotFileParser()
    robots.parse(r.text.splitlines())
    return robots.can_fetch(UA,url)

def get(url):
    r=S.get(url,timeout=26)
    r.raise_for_status()
    if "html" not in r.headers.get("content-type","text/html").lower():
        raise RuntimeError("non-HTML response")
    if len(r.content)>12000000: raise RuntimeError("response too large")
    return r.text

def ident(source,*parts):
    return source+"-"+hashlib.sha256("|".join(parts).encode()).hexdigest()[:18]

def date(s):
    m=re.search(r"(\d{2,4})[./-](\d{1,2})[./-](\d{1,2})",s or "")
    if not m:return ""
    y,mo,d=map(int,m.groups())
    if y<100:y+=2000
    try: return datetime(y,mo,d).strftime("%Y-%m-%d")
    except ValueError: return ""

def jasoseol(html):
    soup=BeautifulSoup(html,"html.parser")
    jobs=[]
    for company_tag in soup.find_all("h5"):
        title_tag=company_tag.find_next("h4")
        if not title_tag or title_tag.find_previous("h5") is not company_tag:continue
        company=company_tag.get_text(" ",strip=True)
        title=title_tag.get_text(" ",strip=True)
        if len(company)<2 or len(title)<3:continue
        pieces=[]
        for item in title_tag.next_elements:
            if getattr(item,"name",None) in ("h4","h5"):break
            if getattr(item,"name",None)=="p":
                label=item.get_text(" ",strip=True)
                if label and label not in pieces:pieces.append(label)
                if len(pieces)>=12:break
        period=next((re.search(r"(\d{2}/\d{2}/\d{2})\s*[-~]\s*(\d{2}/\d{2}/\d{2})",p)
                     for p in pieces if re.search(r"\d{2}/\d{2}/\d{2}\s*[-~]\s*\d{2}/\d{2}/\d{2}",p)),None)
        start,end=(date(period[1]),date(period[2])) if period else ("","")
        type_line=next((p for p in pieces if any(k in p for k in ("대기업","중견기업","공기업","공공기관","기타기업"))),"")
        kind=("대기업" if "대기업" in type_line else
              "중견기업" if "중견기업" in type_line else
              "공기업" if "공기업" in type_line or "공공기관" in type_line else "기타")
        employment=next((v for v in ("신입","인턴","경력","계약직") if v in type_line),"미확인")
        link=title_tag.find_parent("a",href=True) or company_tag.find_parent("a",href=True)
        if not link:
            candidate=title_tag.find_next("a",href=True)
            following=title_tag.find_next("h5")
            if candidate and "/recruit/" in candidate.get("href","") and (
                following is None or candidate.sourceline is not None and following.sourceline is not None and candidate.sourceline<following.sourceline):
                link=candidate
        url=urljoin(JS,link["href"]) if link else JS
        jobs.append(dict(id=ident("jasoseol",company,title,end),source="jasoseol",
            source_detail="자소설닷컴 공개 목록",company=company,title=title,
            positions=pieces[0][:700] if pieces else "",company_type=kind,
            employment=employment,start_date=start,end_date=end,result_date="",
            test_date="",url=url,verified=NOW.date().isoformat()))
    return jobs

def jobkorea(html):
    soup=BeautifulSoup(html,"html.parser")
    heading=next((h.get_text(" ",strip=True) for h in soup.find_all(["h2","h3","h4"])
         if re.search(r"20\d{2}[^0-9]{0,12}\d{1,2}\s*월",h.get_text(" ",strip=True))),"")
    match=re.search(r"(20\d{2})[^0-9]{0,12}(\d{1,2})\s*월",heading)
    if not match:raise RuntimeError("cannot locate calendar month")
    y,mo=map(int,match.groups())
    tables=[t for t in soup.find_all("table") if
            t.find("caption") and "공채달력" in t.find("caption").get_text(" ",strip=True)]
    if not tables:raise RuntimeError("cannot locate recruitment calendar table")
    code={"시작":"start_date","마감":"end_date","발표":"result_date","인적성":"test_date"}
    jobs=[]
    for cell in tables[0].select("tbody td"):
        first=cell.find("strong")
        if not first:continue
        try:
            d=int(first.get_text(" ",strip=True))
            day=datetime(y,mo,d).strftime("%Y-%m-%d")
        except (ValueError,TypeError):continue
        for item in cell.find_all("p"):
            kind=next((b.get_text(" ",strip=True) for b in item.find_all("strong")
                       if b.get_text(" ",strip=True) in code),None)
            if not kind:continue
            name=item.get_text(" ",strip=True).replace(kind,"",1).strip()
            name=re.sub(r"더보기.*$","",name).strip()
            name=re.sub(r"^(?:㈜|\(주\)|주식회사\s*)+","",name).strip()
            name=re.sub(r"\s*㈜\s*$","",name).strip()
            if not (2<=len(name)<=100):continue
            a=item.find("a",href=True)
            url=urljoin(JK,a["href"]) if a else JK
            dates={k:(day if code[kind]==k else "") for k in code.values()}
            jobs.append(dict(id=ident("jobkorea",name,day,kind),source="jobkorea",
                source_detail="잡코리아 공개 공채달력",company=name,
                title="공채달력 등록 일정 · 세부 공고 확인 필요",positions="",
                company_type=KINDS.get(name,"기타"),employment="미확인",
                url=url,verified=NOW.date().isoformat(),**dates))
    return list({j["id"]:j for j in jobs}.values())

def scan_jasoseol():
    found={}
    max_pages=max(1,min(5,int(os.getenv("JASO_PAGES","3"))))
    for i in range(1,max_pages+1):
        if i>1:time.sleep(1.5)
        url=JS if i==1 else JS+"?page="+str(i)
        if not permitted(url):raise RuntimeError("robots.txt disallows "+url)
        jobs=jasoseol(get(url))
        new=[j for j in jobs if j["id"] not in found]
        if not new:break
        for j in new:found[j["id"]]=j
    return list(found.values())



# Read-only conversion of public HTML to markdown. No credentials or private APIs.
# This is a lower-volume fallback when the source's public HTML rejects GitHub runners.
def public_reader(url):
    reader_url = "https://r.jina.ai/" + url
    last_error=None
    for attempt in range(2):
        try:
            response = S.get(reader_url, timeout=22,
                             headers={"Accept":"text/plain","X-Cache-Tolerance":"1800"})
            response.raise_for_status()
            break
        except requests.RequestException as error:
            last_error=error
            if attempt==1: raise
            time.sleep(3*(attempt+1))
    if len(response.content) > 12000000:
        raise RuntimeError("public reader response too large")
    body = response.text
    if "Markdown Content:" not in body:
        raise RuntimeError("public reader returned no markdown document")
    return body.split("Markdown Content:",1)[1]

def reader_jasoseol(md):
    # The official public listing's read-only markdown cards include /recruit/ID links.
    card = re.compile(
        r"#####\s+(?P<company>[^#\n]{2,100}?)\s+####\s+"
        r"(?P<content>[^\n]{5,4000}?)\]\((?P<url>https://jasoseol\.com/recruit/\d+)\)")
    results = []
    for m in card.finditer(md):
        company = re.sub(r"\s+"," ",m.group("company")).strip()
        content = m.group("content")
        headline = re.sub(r"\s+"," ",content.split("![Image",1)[0]).strip()
        if len(headline) < 4 or "더보기" in company:
            continue
        period = re.search(r"(?<!\d)(\d{2}/\d{2}/\d{2})\s*[-~]\s*(\d{2}/\d{2}/\d{2})",content)
        start, end = (date(period[1]),date(period[2])) if period else ("","")
        company_type = ("대기업" if "대기업" in content else "중견기업" if "중견기업" in content
                        else "공기업" if "공기업" in content or "공공기관" in content else "기타")
        employment = next((v for v in ("신입","인턴","경력","계약직") if v in content),"미확인")
        url=m.group("url")
        jid=url.rsplit("/",1)[-1]
        results.append(dict(id="jasoseol-"+jid,source="jasoseol",
            source_detail="자소설닷컴 공개 페이지 메타데이터",company=company,
            title=headline[:200],positions=headline[:800],company_type=company_type,
            employment=employment,start_date=start,end_date=end,result_date="",
            test_date="",url=url,verified=NOW.date().isoformat()))
    return list({j["id"]:j for j in results}.values())

def reader_jobkorea(md):
    month_match=re.search(r"(20\d{2})\s*\.\s*년?\s*(\d{1,2})\s*월",md)
    if not month_match:
        raise RuntimeError("calendar month missing from public reader")
    year,month=map(int,month_match.groups())
    pattern=re.compile(r"\[\*\*(시작|마감|발표|인적성)\*\*([^\]\n]{2,180})\]"
                       r"\((https?://[^\s)]+)(?:\s+\"[^\"]*\")?\)")
    keys={"시작":"start_date","마감":"end_date","발표":"result_date","인적성":"test_date"}
    results={}
    for row in md.splitlines():
        if not re.match(r"^\|\s*\*\*\d{1,2}\*\*",row):
            continue
        for cell in row.strip().strip("|").split("|"):
            m=re.match(r"\s*\*\*(\d{1,2})\*\*(.*)$",cell)
            if not m:continue
            try:stamp=datetime(year,month,int(m[1])).strftime("%Y-%m-%d")
            except ValueError:continue
            for entry in pattern.finditer(m[2]):
                event,name,url=entry.groups()
                name=re.sub(r"^(?:\s*(?:㈜|\(주\)|주식회사))+\s*","",name)
                name=re.sub(r"\s*㈜\s*$","",name).strip()
                if not (2<=len(name)<=100):continue
                match=re.search(r"/Recruit/GI_Read/(\d+)",url,re.I)
                key=match.group(1) if match else hashlib.sha256(
                    (name+"|"+event+"|"+stamp).encode()).hexdigest()[:16]
                idx="jobkorea-"+key
                if idx not in results:
                    results[idx]=dict(id=idx,source="jobkorea",
                        source_detail="잡코리아 공개 공채달력 일부",company=name,
                        title="공채달력 일정 · 원본 공고 확인 필요",positions="",
                        company_type=KINDS.get(name,"기타"),employment="미확인",
                        start_date="",end_date="",result_date="",test_date="",
                        url=url,verified=NOW.date().isoformat())
                results[idx][keys[event]]=stamp
    return list(results.values())

def source_total(md):
    m=re.search(r"공고\s*([\d,]+)\s*건",md or "")
    return int(m[1].replace(",","")) if m else None

def target_pages(first, count):
    """Newest pages every run; rotate 300 older pages between midnight and backup runs.

    Two daily runs use complementary page windows. As public search pagination changes,
    this remains a best-effort rolling archive rather than an exhaustive export.
    """
    start=max(first+1,int(os.getenv("JASO_DEEP_START","25")))
    span=max(1,min(int(os.getenv("JASO_DEEP_SPAN","300")),500))
    day_number=NOW.date().toordinal()
    slot=1 if NOW.hour>=0 and NOW.minute>=25 else 0
    offset=((day_number*count*2+slot*count) % span) if count else 0
    older=[start+((offset+i)%span) for i in range(count)]
    return [*range(1,first+1),*older]

def fallback_jobkorea():
    # Only the PUBLIC recruitment calendar page is supported. The page truncates
    # days with '더보기 +N', so it cannot be claimed as a complete JobKorea feed.
    md=public_reader(JK)
    jobs=reader_jobkorea(md)
    if len(jobs)<5:
        raise RuntimeError("JobKorea public calendar parsed fewer than five records")
    more=[int(x) for x in re.findall(r"더보기\s*\+(\d+)",md)]
    SOURCE_DIAGNOSTICS["jobkorea"]={
        "pages_scanned":1,"page_failures":0,"visible_events":len(jobs),
        "additional_hidden_events_indicated":sum(more),
        "partial":True,
        "note":"공채달력 현재 월의 공개된 일부 일정만 수집; 더보기 항목과 일반 채용검색은 미포함"
    }
    return jobs

def fallback_jasoseol():
    records={}
    first=max(1,min(int(os.getenv("JASO_PAGES","24")),45))
    big=max(0,min(int(os.getenv("JASO_BIG_PAGES","12")),30))
    rotate=max(0,min(int(os.getenv("JASO_ROTATE_PAGES","6")),15))
    streams=[
      ("latest",JS,target_pages(first,rotate)),
    ]
    if big:
        streams.append(("large",JS+"?businessTypes=big_business",list(range(1,big+1))))
    successful_pages=0
    failed_pages=[]
    budget_start=time.monotonic()
    budget_seconds=max(120,min(int(os.getenv('JASO_SCAN_BUDGET','660')),840))
    reported_total=None
    per_stream={}
    for stream,base,pages in streams:
        collected=0
        seen_pages=set()
        for n in pages:
            if time.monotonic()-budget_start>budget_seconds:
                failed_pages.append(stream+':budget_limit')
                print('JASO_BUDGET_REACHED',stream,n,flush=True)
                break
            if n in seen_pages:continue
            seen_pages.add(n)
            url=base+("&" if "?" in base else "?")+"page="+str(n)
            try:
                md=public_reader(url)
                if stream=="latest" and n==1:
                    reported_total=source_total(md)
                batch=reader_jasoseol(md)
                if not batch:raise RuntimeError("page had no parseable job links")
                successful_pages+=1
                for job in batch:
                    if job["id"] not in records:
                        collected+=1
                    records[job["id"]]=job
            except Exception as ex:
                failed_pages.append(stream+":"+str(n))
                print("PAGE_FAILED",stream,n,str(ex)[:130],flush=True)
                # No point scanning thousands of old pages during global blocking,
                # but preserve records already collected in this run.
                if len(failed_pages)>=8 and successful_pages==0:
                    break
            time.sleep(1.25)
        per_stream[stream]=collected
    SOURCE_DIAGNOSTICS["jasoseol"]={
        "pages_scanned":successful_pages,"page_failures":len(failed_pages),
        "failed_page_samples":failed_pages[:10],
        "reported_site_results":reported_total,
        "stream_counts":per_stream,
        "partial":True,
        "note":"공개 채용검색 최신 페이지 + 대기업 + 이전 페이지 순환 수집; 자소설 채용달력 전수 접근 아님"
    }
    if len(records)<5:
        raise RuntimeError("Jasoseol pages parsed fewer than five total unique entries")
    print("JASO_PAGE_AUDIT",json.dumps(SOURCE_DIAGNOSTICS["jasoseol"],ensure_ascii=False),flush=True)
    return list(records.values())

def source_with_fallback(source, original):
    try:
        data=original()
        if len(data)>=5:return data
        raise RuntimeError("original list parsed too few records")
    except Exception as exc:
        print("PRIMARY_FAILED",source,str(exc)[:160],flush=True)
        return fallback_jobkorea() if source=="jobkorea" else fallback_jasoseol()

def main():
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    try: previous=json.loads(OUTPUT.read_text(encoding="utf-8"))
    except (FileNotFoundError,ValueError):previous={"jobs":[],"source_status":{}}
    status={}
    incoming=[]
    for source,url,method in [
        ("jobkorea",JK,lambda:source_with_fallback("jobkorea",lambda:jobkorea(get(JK)))),
        ("jasoseol",JS,fallback_jasoseol)]:
        try:
            results=method()
            if len(results)<2:raise RuntimeError("fewer than 2 parsed entries; possible page change")
            incoming.extend(results)
            status[source]={"ok":True,"count":len(results),"note":"공개 페이지 일부 수집, 전체 공고 보장 불가",**SOURCE_DIAGNOSTICS.get(source,{})}
            print("OK",source,len(results),flush=True)
        except Exception as error:
            status[source]={"ok":False,"count":0,"note":str(error)[:210],**SOURCE_DIAGNOSTICS.get(source,{})}
            print("FAILED",source,repr(error),file=sys.stderr,flush=True)
        time.sleep(1)
    jobs={}
    for j in [*previous.get("jobs",[]),*incoming]:
        if isinstance(j,dict) and j.get("id") and j.get("source"):
            jobs[(j["source"],j["id"])]=j
    # Keep ended postings in the public archive for two years; user application snapshots persist locally.
    cutoff=(NOW.date()-timedelta(days=730)).isoformat()
    kept=[j for j in jobs.values() if
          max((j.get(k,"") or "" for k in ("start_date","end_date","result_date","test_date")),default="") >=cutoff or
          not any(j.get(k) for k in ("start_date","end_date","result_date","test_date"))]
    success=any(x["ok"] for x in status.values())
    data={"updated_at":NOW.isoformat(timespec="seconds") if success else previous.get("updated_at",""),
          "last_attempt_at":NOW.isoformat(timespec="seconds"),
          "mode":"automatic" if success else "snapshot",
          "source_status":status,"jobs":kept}
    OUTPUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Records:",len(kept),"automatic:",success,flush=True)
    # A 0 exit code allows old data + a failure notice to remain visible.
    # Source results must be checked in the published status field.
    return 0

if __name__=="__main__":
    sys.exit(main())
