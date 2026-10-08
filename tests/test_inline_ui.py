import shutil,subprocess,re,unittest
from pathlib import Path

HTML=Path(__file__).resolve().parents[1]/"index.html"
class UserInterfaceSmokeTest(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"),"Node.js required for JavaScript syntax check")
    def test_embedded_javascript_syntax(self):
        scripts=re.findall(r"<script\b[^>]*>(.*?)</script>",HTML.read_text(encoding="utf-8"),re.S|re.I)
        self.assertGreaterEqual(len(scripts),2)
        for i,js in enumerate(scripts):
            with self.subTest(script=i):
                cp=subprocess.run(["node","--check"],input=js,capture_output=True,text=True,timeout=25)
                self.assertEqual(cp.returncode,0,cp.stderr[:3000])

    def test_application_tracker_dom_and_state(self):
        doc=HTML.read_text(encoding="utf-8")
        for term in ['data-view="applied"','id="statApplied"','id="appliedCount"',
                     'id="showEnded"',"function persistRecord(","function applicationEditor(",
                     "function showQuickDate(","function renderList()","radar_applications",
                     "data-record-save","data-apply","version:2,exported_at"]:
            with self.subTest(term=term):self.assertIn(term,doc)
        self.assertNotIn("$('statSaved')",doc)
        self.assertNotIn("$('openOnly')",doc)

    @unittest.skipUnless(shutil.which("node"),"Node.js required for dedupe regression")
    def test_real_data_deduplication(self):
        cp=subprocess.run(["node","tests/test_dedupe_live.js"],cwd=HTML.parent,
                          capture_output=True,text=True,timeout=25)
        self.assertEqual(cp.returncode,0,cp.stdout+"\n"+cp.stderr)

    @unittest.skipUnless(shutil.which("node"),"Node.js required for calendar UI tests")
    def test_mobile_calendar_d_day_and_swipe(self):
        cp=subprocess.run(["node","tests/test_calendar_ux.js"],cwd=HTML.parent,
                          capture_output=True,text=True,timeout=25)
        self.assertEqual(cp.returncode,0,cp.stdout+"\n"+cp.stderr)

if __name__=="__main__":
    unittest.main()
