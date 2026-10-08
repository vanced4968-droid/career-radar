from urllib.request import Request,urlopen
from urllib.parse import quote
from datetime import datetime,timezone
import concurrent.futures,time
urls = {
"jina_jasoseol": "https://r.jina.ai/https://jasoseol.com/search",
"jina_jobkorea": "https://r.jina.ai/https://www.jobkorea.co.kr/starter/calendar",
"job_alio": "https://job.alio.go.kr/recruit.do",
"alio_gov": "https://alio.go.kr/information/informationRecruitList.do",
"bing_rss": "https://www.bing.com/search?format=rss&q="+quote("site:jasoseol.com/recruit 2026 채용"),
"work24_notice": "https://www.work24.go.kr/cm/e/a/0110/selectOpenApiIntro.do",
}
def check(pair):
    k,u=pair
    try:
        t=time.monotonic()
        req=Request(u,headers={"User-Agent":"CareerRadar-PersonalCalendar/1.1","Accept":"text/html,text/plain,application/rss+xml"})
        with urlopen(req,timeout=18) as f:
            data=f.read(100000).decode("utf-8","replace")
            return k,f.status,round(time.monotonic()-t,1),len(data),data[:120].replace("\n"," "),sum(x in data for x in ("공채","채용","recruit","jobs","RSS"))
    except Exception as e:
        return k,"FAILED",0,0,str(e)[:150],0
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
    for o in pool.map(check,urls.items()):
        print(o,flush=True)
