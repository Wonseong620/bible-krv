import json
import unittest
from unittest.mock import patch
from server.app import counsel

class GuidanceTests(unittest.TestCase):
    def test_guidance_skips_scripture_template(self):
        for kind in ('clarify', 'redirect'):
            with self.subTest(kind=kind), patch('server.app.ollama', return_value={'message':{'content':json.dumps({'disposition':kind,'interpretation':'','response':'','suggestions':[]})}}):
                result=counsel([{'role':'user','content':'입력'}])
                self.assertEqual(result['mode'],kind)
                self.assertEqual(result['verses'],[])
                self.assertNotIn('① 말씀',result['reply'])
                self.assertEqual(len(result['suggestions']),3)
