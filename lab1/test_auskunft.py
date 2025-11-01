"""
Simple client server unit test
"""

import logging
import threading
import unittest
import clientserver
from context import lab_logging

lab_logging.setup(stream_level=logging.INFO)


class TestEchoService(unittest.TestCase):
    """Testet Echo, GET und GETALL Funktionen"""
    _server = clientserver.Server()
    _server_thread = threading.Thread(target=_server.serve)

    @classmethod
    def setUpClass(cls):
        cls._server_thread.start()

    def setUp(self):
        super().setUp()
        self.client = clientserver.Client()

    def test_srv_echo(self):
        """Testet das ursprüngliche Echo-Verhalten"""
        msg = self.client.call("Hello VS2Lab")
        self.assertEqual(msg, 'Hello VS2Lab*')

    def test_srv_get_existing(self):
        """Testet GET für existierenden Namen"""
        result = self.client.get("Anna Mueller")
        self.assertEqual(result, "+49 151 2345678")

    def test_srv_get_notfound(self):
        """Testet GET für nicht vorhandenen Namen"""
        result = self.client.get("Max Mustermann")
        self.assertEqual(result, "NOTFOUND")

    def test_srv_getall(self):
        """Testet GETALL – alle Einträge"""
        result = self.client.get_all()
        self.assertIn("Anna Mueller:+49 151 2345678", result)
        self.assertIn("Viktor Schroeder:+49 156 3456789", result)
        # Sollte alle 20 Einträge enthalten:
        self.assertEqual(len(result.splitlines()), 20)

    def tearDown(self):
        self.client.close()

    @classmethod
    def tearDownClass(cls):
        cls._server._serving = False
        cls._server_thread.join()


if __name__ == '__main__':
    unittest.main()
