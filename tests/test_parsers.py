import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import sync_jobs as s

class TestParsers(unittest.TestCase):
    def test_jasoseol(self):
        sample="""<main><h5>DN솔루션즈</h5><h4>2026 하반기 신입사원 채용</h4>
        <p>기계, 제어, 품질</p><p>중견기업신입</p><p>26/10/08 - 26/10/21 (13일)</p>
        <h5>SK바이오사이언스</h5><h4>2026 하반기 신입 채용</h4>
        <p>생산, 품질</p><p>대기업신입</p><p>26/10/07 - 26/10/21 (13일)</p></main>"""
        found=s.jasoseol(sample)
        self.assertEqual(len(found),2)
        self.assertEqual(found[0]["end_date"],"2026-10-21")
        self.assertEqual(found[0]["company_type"],"중견기업")
        self.assertEqual(found[1]["start_date"],"2026-10-07")

    def test_jobkorea(self):
        sample="""<h3>2026.년10월</h3><table><caption>공채달력</caption><tbody><tr>
        <td><strong>14</strong><p><strong>마감</strong>한국서부발전㈜</p></td>
        <td><strong>15</strong><p><strong>발표</strong>교보증권㈜</p></td>
        </tr></tbody></table>"""
        found=s.jobkorea(sample)
        self.assertEqual(len(found),2)
        self.assertEqual(found[0]["end_date"],"2026-10-14")
        self.assertEqual(found[0]["company_type"],"공기업")
        self.assertEqual(found[1]["result_date"],"2026-10-15")

    def test_date(self):
        self.assertEqual(s.date("26/10/08"),"2026-10-08")
        self.assertEqual(s.date("2026-02-30"),"")
        self.assertEqual(s.date(""),"")

if __name__=="__main__":unittest.main()
