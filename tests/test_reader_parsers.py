import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import sync_jobs as m

class PublicReaderParserTests(unittest.TestCase):
    def test_jobkorea_reader(self):
        txt = """Title: 2026 공채 달력
Markdown Content:
### 2026.년10월
| 일 | 월 |
| --- | --- |
| **14** [**마감**한국서부발전㈜](https://www.jobkorea.co.kr/starter/calendar#viewdetail "한국서부발전㈜") [**마감**㈜삼천리](https://www.jobkorea.co.kr/Recruit/GI_Read/50102653?Oem_Code=C1&PageGbn=ST&sc=419 "㈜삼천리") | **15** [**발표**교보증권㈜](https://www.jobkorea.co.kr/starter/calendar#viewdetail "교보증권㈜") |
| **20** [**마감**㈜삼천리](https://www.jobkorea.co.kr/Recruit/GI_Read/50102653?Oem_Code=C1&PageGbn=ST&sc=419 "㈜삼천리") | **21** |
"""
        out=m.reader_jobkorea(txt)
        self.assertEqual(len(out),3)
        self.assertEqual(next(x for x in out if x["company"]=="한국서부발전")["end_date"],"2026-10-14")
        sj=next(x for x in out if x["company"]=="삼천리")
        self.assertEqual(sj["end_date"],"2026-10-20")
        self.assertEqual(next(x for x in out if x["company"]=="교보증권")["result_date"],"2026-10-15")

    def test_jasoseol_reader(self):
        txt = """## 검색 결과
[![Image 36: 회사 로고](https://example.net/a.png) ##### SK이노베이션 E&S #### 도시가스사 대졸 신입사원(G3) 모집 경영지원, 마케팅 ![Image 37](https://example.net/s.png)대기업![Image 38](https://example.net/a.png)신입 26/10/08 - 26/10/21(12일) 2026년 10월 8일 15:00 ~ 2026년 10월 21일 14:59 ](https://jasoseol.com/recruit/106649)
[![Image 40: 회사 로고](https://example.net/b.png) ##### 엘티정밀 #### 미국 VMI 창고 운영인원 신입 및 경력사원 모집 ![Image 41](https://example.net/q.png)중견기업 신입, 경력 26/10/08 - 26/10/15(6일) ](https://jasoseol.com/recruit/106642)
"""
        out=m.reader_jasoseol(txt)
        self.assertEqual(len(out),2)
        self.assertEqual(out[0]["company"],"SK이노베이션 E&S")
        self.assertEqual(out[0]["end_date"],"2026-10-21")
        self.assertEqual(out[1]["company_type"],"중견기업")
        self.assertEqual(out[1]["url"],"https://jasoseol.com/recruit/106642")

if __name__=="__main__":unittest.main()
