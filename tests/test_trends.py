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
        self.assertNotIn('취업부담',self.q.trends()['keywords'])
        self.assertIn('가족관계',self.q.trends()['keywords'])
        self.assertNotIn('question',self.q.trends())
        self.assertEqual(Quota(self.path,lambda:self.now).trends(),self.q.trends())
    def test_first_record_failure_and_day_boundary(self):
        self.add('취업 걱정')
        self.assertIn('취업부담',self.q.trends()['keywords'])
        before=self.q.trends()
        def fail():raise RuntimeError()
        with self.assertRaises(RuntimeError):self.q.run(fail,question='취업 걱정')
        self.assertEqual(self.q.trends(),before)
        self.now+=timedelta(days=1)
        self.add('취업 걱정')
        self.assertIn('취업부담',self.q.trends()['keywords'])
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

    def test_contextual_concerns(self):
        from server.trends import classify
        labels=classify('엄마와 말이 안 통해서 자꾸 싸워요')['keyword']
        self.assertIn('가족관계',labels)
        self.assertIn('소통문제',labels)
        self.assertIn('관계갈등',labels)
        labels=classify('남들보다 뒤처지는 것 같고 앞날이 막막해요')['keyword']
        self.assertIn('비교심리',labels)
        self.assertIn('불안심리',labels)
        self.assertNotIn('소통문제',classify('오늘 좋은 대화를 나눴어요')['keyword'])

    def test_ranking_uses_only_latest_twenty(self):
        for _ in range(5): self.add('취업 걱정')
        for _ in range(20): self.add('가족 걱정')
        result = self.q.trends()
        self.assertEqual(result['window'], 20)
        self.assertNotIn('취업부담', result['keywords'])
        self.assertIn('가족관계', result['keywords'])
        self.assertEqual(self.q.status()['limit'], 100)
        with sqlite3.connect(self.path) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM recent_exchanges').fetchone()[0], 25)
