import sqlite3
import tempfile
import unittest
from datetime import datetime,timedelta
from pathlib import Path
from server.quota import Quota,TIMEZONE

class TrendsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'test.sqlite3'
        self.now=datetime(2026,9,7,15,tzinfo=TIMEZONE)
        self.q=Quota(self.path,lambda:self.now)
    def add(self, question):
        return self.q.run(lambda:{'reply':'응답 원문'},question=question)
    def test_sliding_window_and_no_keyword_storage(self):
        for i in range(105):
            if i and i%100==0:self.now+=timedelta(days=1)
            self.add('취업 고민' if i<5 else '가족 걱정 '+str(i))
        with sqlite3.connect(self.path) as c:
            rows=c.execute('SELECT question,reply FROM recent_exchanges ORDER BY id').fetchall()
            tables=[r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        self.assertEqual(len(rows),100)
        self.assertEqual(rows[0],('가족 걱정 5','응답 원문'))
        self.assertEqual(rows[-1][0],'가족 걱정 104')
        self.assertNotIn('daily_trends',tables)
        self.assertNotIn('취업',self.q.trends()['keywords'])
        self.assertIn('가족',self.q.trends()['keywords'])
        self.assertNotIn('question',self.q.trends())
        self.assertEqual(Quota(self.path,lambda:self.now).trends(),self.q.trends())
    def test_failure_threshold_and_day_boundary(self):
        for _ in range(4):self.add('취업 걱정')
        def fail():raise RuntimeError()
        with self.assertRaises(RuntimeError):self.q.run(fail,question='취업 걱정')
        self.assertEqual(self.q.trends()['keywords'],[])
        self.now+=timedelta(days=1)
        self.add('취업 걱정')
        self.assertIn('취업',self.q.trends()['keywords'])
        self.assertEqual(self.q.status()['completed'],1)
    def test_top_ten_and_personal_text_not_exposed(self):
        for text in ['불안 두려움 외로움 관계 소통 갈등 용서','취업 진로 직장 가족 결혼 육아 신앙']:
            for _ in range(5):self.add(text+' 이름 홍길동')
        result=self.q.trends()
        self.assertEqual(len(result['keywords']),10)
        self.assertNotIn('홍길동',str(result))
    def test_migrates_away_from_persisted_labels(self):
        with sqlite3.connect(self.path) as c:
            c.execute('CREATE TABLE daily_trends(label TEXT)')
            c.execute("INSERT INTO daily_trends VALUES ('취업')")
        q=Quota(self.path,lambda:self.now)
        self.assertEqual(q.trends()['keywords'],[])
        with sqlite3.connect(self.path) as c:
            self.assertFalse(c.execute("SELECT name FROM sqlite_master WHERE name='daily_trends'").fetchone())
