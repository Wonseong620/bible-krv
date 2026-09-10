import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from http.server import ThreadingHTTPServer
from server import app

class MaintenanceTests(unittest.TestCase):
    def test_blocks_generation_without_quota_and_restores_dynamically(self):
        with tempfile.TemporaryDirectory() as directory:
            flag=Path(directory)/'maintenance.flag';flag.touch()
            server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            base=f'http://127.0.0.1:{server.server_port}'
            def get(path,question=None):
                data=None if question is None else json.dumps({'messages':[{'role':'user','content':question}]}).encode()
                request=Request(base+path,data=data,headers={'Content-Type':'application/json'})
                try:r=urlopen(request,timeout=5)
                except HTTPError as error:r=error
                with r:return r.status,json.load(r)
            try:
                with patch.object(app,'MAINTENANCE_FILE',flag),patch.object(app.Handler,'trusted',return_value=True),patch.object(app,'ollama') as model,patch.object(app.QUOTA,'run') as quota:
                    self.assertEqual(get('/api/health')[0],503)
                    status,data=get('/api/chat','오늘 진로가 고민이에요.')
                    self.assertEqual(status,503);self.assertTrue(data['maintenance'])
                    self.assertIn('점검',data['error']);model.assert_not_called();quota.assert_not_called()
                    status,data=get('/api/chat','지금 스스로를 해칠까 봐 무서워요.')
                    self.assertEqual(status,200);self.assertEqual(data['mode'],'self_harm')
                    model.assert_not_called();quota.assert_not_called()
                    flag.unlink();model.return_value={'models':[{'name':app.MODEL}]}
                    with patch.object(app.QUOTA,'status',return_value={'remaining':100}):
                        status,data=get('/api/health')
                    self.assertEqual(status,200);self.assertTrue(data['ready'])
            finally:server.shutdown();server.server_close();worker.join()
