import sqlite3
import tempfile
import unittest
from datetime import datetime,timedelta
from pathlib import Path
from server.quota import Quota,TIMEZONE
from server.trends import classify,KEYWORDS

class TrendsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'test.sqlite3'
        self.now=datetime(2026,9,7,15,tzinfo=TIMEZONE)
        self.q=Quota(self.path,lambda:self.now)
    def test_fixed_nouns_and_no_personal_text(self):
        labels=classify('제 이름은 홍길동이고 연락처는 010-1234-5678입니다. 면접 면접 때문에 걱정돼요.')
        self.assertIn('취업',labels['keyword'])
        self.assertEqual(labels['keyword'].count('취업'),1)
        self.q.run(lambda:'ok',labels)
        with sqlite3.connect(self.path) as c:
            dump='\n'.join(c.iterdump())
        self.assertNotIn('홍길동',dump);self.assertNotIn('010-1234-5678',dump)
    def test_threshold_failure_and_followup(self):
        labels=classify('취업 걱정')
        for _ in range(4):self.q.run(lambda:'ok',labels)
        self.assertEqual(self.q.trends()['keywords'],[])
        def fail():raise RuntimeError()
        with self.assertRaises(RuntimeError):self.q.run(fail,labels)
        self.q.run(lambda:'followup')
        self.assertEqual(self.q.trends()['keywords'],[])
        self.q.run(lambda:'ok',labels)
        self.assertIn('취업',self.q.trends()['keywords'])
        self.assertNotIn('count',str(self.q.trends()))
    def test_top_seven_persistence_and_new_day(self):
        for _ in range(5):self.q.run(lambda:'ok',{'keyword':list(KEYWORDS)[:9]})
        self.assertEqual(len(self.q.trends()['keywords']),7)
        self.assertEqual(Quota(self.path,lambda:self.now).trends(),self.q.trends())
        self.now+=timedelta(days=1)
        self.assertEqual(self.q.trends()['keywords'],[])
    def test_unknown_labels_ignored(self):
        self.q.run(lambda:'ok',{'topic':['홍길동'],'keyword':['010-1234-5678']})
        with sqlite3.connect(self.path) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM daily_trends').fetchone()[0],0)

if __name__=='__main__':unittest.main()
