import unittest
from isles.isles import Connection

class TestConnection(unittest.TestCase):
    def setUp(self):
        self.connection = Connection()
    
    def test_ownerToRouter(self):
        for i in range(100):
            self.connection.ownerSend(i)
            self.assertEqual(i, self.connection.routerReceive())
    
    def test_routerToOwner(self):
        for i in range(100):
            self.connection.routerSend(i)
            self.assertEqual(i, self.connection.ownerReceive())
    
    def test_emptyReceive(self):
        self.assertIsNone(self.connection.ownerReceive())
        self.assertIsNone(self.connection.routerReceive())