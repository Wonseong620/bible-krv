import tempfile
import threading
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from server.quota import Quota, QuotaExceeded, TIMEZONE

class QuotaTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'quota.sqlite3'
        self.now=datetime(2026,9,7,12,tzinfo=TIMEZONE)
        self.quota=Quota(self.path,lambda:self.now)
    def test_exactly_100_responses_persist(self):
        for _ in range(100): self.assertEqual(self.quota.run(lambda:'answer'),'answer')
        generated=[]
        with self.assertRaises(QuotaExceeded): self.quota.run(lambda:generated.append(True))
        self.assertEqual(generated,[])
        self.assertEqual(Quota(self.path,lambda:self.now).status()['remaining'],0)
    def test_failure_does_not_count(self):
        def fail(): raise RuntimeError('generation failed')
        with self.assertRaises(RuntimeError): self.quota.run(fail)
        self.assertEqual(self.quota.status()['remaining'],100)
    def test_rollover_on_completion(self):
        self.now=self.now.replace(hour=23,minute=59,second=59)
        def generate():
            self.now += timedelta(seconds=2)
            return 'answer'
        self.quota.run(generate)
        self.assertEqual(self.quota.status()['completed'],1)
        self.now -= timedelta(days=1)
        self.assertEqual(self.quota.status()['completed'],0)
    def test_concurrent_last_slot(self):
        for _ in range(99): self.quota.run(lambda:'answer')
        outcomes=[]
        barrier=threading.Barrier(2)
        def attempt():
            barrier.wait()
            try: self.quota.run(lambda:'answer');outcomes.append('ok')
            except QuotaExceeded: outcomes.append('full')
        threads=[threading.Thread(target=attempt) for _ in range(2)]
        for t in threads:t.start()
        for t in threads:t.join()
        self.assertCountEqual(outcomes,['ok','full'])
        self.assertEqual(self.quota.status()['completed'],100)
    def test_next_day_restores_budget(self):
        for _ in range(100): self.quota.run(lambda:'answer')
        self.now += timedelta(days=1)
        self.assertEqual(self.quota.status()['remaining'],100)
        self.quota.run(lambda:'answer')
        self.assertEqual(self.quota.status()['remaining'],99)

if __name__=='__main__':unittest.main()
