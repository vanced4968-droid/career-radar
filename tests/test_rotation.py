import sys,unittest
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import sync_jobs as s

KST=timezone(timedelta(hours=9))
class RotationCoverageTests(unittest.TestCase):
    def test_midnight_and_backup_scan_distinct_older_pages(self):
        a=datetime(2026,10,10,0,0,tzinfo=KST)
        b=datetime(2026,10,10,0,30,tzinfo=KST)
        with patch.object(s,"NOW",a):
            midnight=s.target_pages(24,6)
        with patch.object(s,"NOW",b):
            backup=s.target_pages(24,6)
        self.assertEqual(midnight[:24],list(range(1,25)))
        self.assertEqual(backup[:24],list(range(1,25)))
        self.assertEqual(len(midnight),30)
        self.assertEqual(len(backup),30)
        self.assertTrue(set(midnight[24:]).isdisjoint(backup[24:]))

    def test_rolling_pages_advance_each_day(self):
        a=datetime(2026,10,10,0,0,tzinfo=KST)
        b=datetime(2026,10,11,0,0,tzinfo=KST)
        with patch.object(s,"NOW",a):
            current=s.target_pages(24,6)
        with patch.object(s,"NOW",b):
            subsequent=s.target_pages(24,6)
        self.assertTrue(set(current[24:]).isdisjoint(subsequent[24:]))


    def test_schedule_slot_stable_when_runner_is_delayed(self):
        with patch.object(s,"NOW",datetime(2026,10,10,0,45,tzinfo=KST)):
            with patch.dict("os.environ",{"JASO_SCAN_SLOT":"primary"}):
                primary=s.target_pages(24,6)
            with patch.dict("os.environ",{"JASO_SCAN_SLOT":"backup"}):
                backup=s.target_pages(24,6)
        self.assertTrue(set(primary[24:]).isdisjoint(backup[24:]))

if __name__=="__main__":unittest.main()
