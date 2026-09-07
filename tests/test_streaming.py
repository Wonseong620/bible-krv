import json
import unittest
from unittest.mock import patch
from server.streaming import fields_so_far
from server.app import counsel

class StreamingTests(unittest.TestCase):
    def test_partial_json_escapes_and_nested_keys(self):
        raw=json.dumps({'disposition':'counsel','response':'한글 "response": 문장\n다음 \\ 줄','suggestions':['a','b','c']},ensure_ascii=True)
        for end in range(1,len(raw)+1):
            fields=fields_so_far(raw[:end])
            if 'response' in fields:self.assertTrue('한글 "response": 문장\n다음 \\ 줄'.startswith(fields['response']))
        self.assertEqual(fields_so_far(raw)['response'],'한글 "response": 문장\n다음 \\ 줄')
    def test_stream_preview_matches_final(self):
        answer={'disposition':'counsel','interpretation':'해석입니다.','response':'응답입니다.','suggestions':['a','b','c']}
        raw=json.dumps(answer,ensure_ascii=False)
        events=[]
        def fake(payload,preview):
            self.assertEqual(payload['options']['num_ctx'],16384)
            self.assertEqual(payload['options']['num_predict'],1800)
            for i in range(1,len(raw)+1):preview(raw[:i])
            return {'message':{'content':raw}}
        with patch('server.app.stream_ollama',side_effect=fake):
            result=counsel([{'role':'user','content':'불안해요'}],events.append)
        self.assertEqual([e for e in events if e['type']=='partial'][-1]['reply'],result['reply'])

    def test_http_stream_completion_and_failure_are_atomic(self):
        import tempfile,threading
        from pathlib import Path
        from urllib.request import Request,urlopen
        from http.server import ThreadingHTTPServer
        from server import app
        from server.quota import Quota
        with tempfile.TemporaryDirectory() as directory:
            quota=Quota(Path(directory)/'test.sqlite3')
            server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            def generate(rows,emit):
                emit({'type':'partial','reply':'작성 중'})
                return {'reply':'완료','suggestions':['a','b','c']}
            def request():
                return Request('http://127.0.0.1:'+str(server.server_port)+'/api/chat',data=json.dumps({'messages':[{'role':'user','content':'질문'}]}).encode(),headers={'Content-Type':'application/json','Accept':'application/x-ndjson'})
            try:
                with patch.object(app,'QUOTA',quota),patch.object(app.Handler,'trusted',return_value=True),patch.object(app,'counsel',side_effect=generate):
                    with urlopen(request()) as response:events=[json.loads(line) for line in response]
                    self.assertEqual([e['type'] for e in events if e['type'] != 'ping'],['partial','done'])
                    self.assertEqual(quota.status()['completed'],1)
                def fail(rows,emit):
                    emit({'type':'partial','reply':'작성 중'})
                    raise ValueError('interrupted')
                with patch.object(app,'QUOTA',quota),patch.object(app.Handler,'trusted',return_value=True),patch.object(app,'counsel',side_effect=fail):
                    with urlopen(request()) as response:events=[json.loads(line) for line in response]
                    self.assertEqual(events[-1]['type'],'error')
                    self.assertEqual(quota.status()['completed'],1)
            finally:server.shutdown();server.server_close();worker.join()
