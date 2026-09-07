import json
import unittest
from unittest.mock import patch
from server.app import counsel

class ConversationTests(unittest.TestCase):
    def test_first_followup_and_reset(self):
        calls=[]
        def fake(path,payload):
            calls.append(payload)
            first='interpretation' in payload['format']['properties']
            answer={'interpretation':'본문의 의미입니다.','response':'함께 생각해 보아요.'} if first else {'response':'그동안 마음이 많이 무거우셨겠어요. 지금 가장 부담되는 일이 무엇인가요?'}
            return {'message':{'content':json.dumps(answer)}}
        with patch('server.app.ollama',side_effect=fake):
            first=counsel([{'role':'user','content':'앞날이 불안해요'}])
            self.assertEqual(first['mode'],'template')
            self.assertNotIn('humanize-korean',calls[-1]['messages'][0]['content'])
            self.assertTrue(first['reply'].startswith('① 말씀'))
            rows=[{'role':'user','content':'앞날이 불안해요'},{'role':'assistant','content':first['reply']},{'role':'user','content':'취업 때문에요'}]
            follow=counsel(rows)
            self.assertEqual(follow['mode'],'conversation')
            self.assertEqual(follow['version'],'1.2')
            self.assertIn('humanize-korean',calls[-1]['messages'][0]['content'])
            self.assertIn('AI 상담 도우미임을 정직하게',calls[-1]['messages'][0]['content'])
            self.assertNotIn('① 말씀',follow['reply'])
            self.assertEqual(follow['verses'],[])
            self.assertEqual(calls[-1]['messages'][1:],rows)
            # Clearing browser history sends a single new user message.
            reset=counsel([{'role':'user','content':'새로운 고민이 있어요'}])
            self.assertEqual(reset['mode'],'template')
            self.assertNotIn('humanize-korean',calls[-1]['messages'][0]['content'])
            self.assertTrue(reset['reply'].startswith('① 말씀'))
    def test_invalid_followup_response_rejected(self):
        rows=[{'role':'user','content':'고민'},{'role':'assistant','content':'응답'},{'role':'user','content':'후속'}]
        with patch('server.app.ollama',return_value={'message':{'content':'{"response": ""}'}}):
            with self.assertRaises(ValueError):counsel(rows)

if __name__=='__main__':unittest.main()
