import json
import sys
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'app'))
from monitor import Monitor
from server import Server


class LiveTests(unittest.TestCase):
    def test_create_modify_delete_and_baseline(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'part.sldprt'
            p.write_text('old')
            m = Monitor({'cad': d})
            m.scan()
            self.assertEqual(m.state()['events'], [])
            p.write_text('changed geometry')
            m.scan()
            self.assertEqual(m.state()['events'][0]['event'], 'MODIFIED')
            p.unlink()
            m.scan()
            self.assertEqual(m.state()['events'][0]['event'], 'DELETED')
            p.write_text('new')
            m.scan()
            self.assertEqual(m.state()['events'][0]['event'], 'CREATED')

    def test_unavailable_root_is_not_deletion(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)/'cad'
            root.mkdir()
            (root/'p').write_text('x')
            m = Monitor({'cad': root})
            m.scan()
            root.rename(Path(d)/'offline')
            m.scan()
            self.assertEqual(m.state()['state'], 'PARTIAL')
            self.assertEqual(m.state()['events'], [])

    def test_http_activity_and_handoff_guard(self):
        with tempfile.TemporaryDirectory() as d:
            s = Server(Path(d), 0)
            t = threading.Thread(target=s.serve_forever, daemon=True)
            t.start()
            try:
                data = json.load(urllib.request.urlopen(s.origin+'/api/activity'))
                self.assertIn('roots', data)
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(s.origin+'/handoff-download')
                self.assertEqual(error.exception.code, 404)
                req = urllib.request.Request(s.origin+'/api/run', data=b'{"command":"build-ai-handoff"}', headers={'Content-Type':'application/json'}, method='POST')
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(req)
                self.assertEqual(error.exception.code, 403)
                req.add_header('Origin',s.origin)
                req.add_header('X-K01-Token',s.token)
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(req)
                self.assertEqual(error.exception.code, 400)
            finally:
                s.shutdown()
                s.server_close()
