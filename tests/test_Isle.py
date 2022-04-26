import unittest
from isles.isles import Isle, route

class MyIsle(Isle):
    @route
    def add(self, a, b):
        return a + b
    
    @route
    def sub(self, a, b):
        return a - b

class TestIsle(unittest.TestCase):
    def setUp(self):
        self.myIsle = MyIsle(identifier="eiland")
        self.packet = self.myIsle.createPacket(receiver=["Santa"], data={"abc":123})
        self.packet.identifier = "packetidentifier"
    
    def test_identifier(self):
        self.assertEqual(self.myIsle.identifier, "eiland")
    
    def test_routes(self):
        self.assertDictEqual(self.myIsle.routes, {"add": self.myIsle.add, "sub": self.myIsle.sub})
    
    def test_createPacket(self):
        self.assertEqual(self.packet.receiver, ["Santa"])
        self.assertEqual(self.packet.sender, ["eiland"])
        self.assertDictEqual(self.packet.data, {"abc":123})

    def test_sendPacket(self):
        identifier = self.myIsle.sendPacket(self.packet)
        self.assertIsNotNone(recvPacket := self.myIsle.connection.routerReceive())
        self.assertEqual(self.packet.identifier, identifier)
        self.assertEqual(self.packet.identifier, recvPacket.identifier)
        self.assertEqual(self.packet.receiver, recvPacket.receiver)
        self.assertEqual(self.packet.sender, recvPacket.sender)
        self.assertDictEqual(self.packet.data, recvPacket.data)
    
    def test_requestResponseTimeout(self):
        with self.assertRaises(TimeoutError):
            self.myIsle.requestResponse(self.packet)
    
    def test_requestResponseReturn(self):
        fake_response = self.packet.createReply(data={"return":6})
        self.myIsle.connection.routerSend(fake_response)
        result = self.myIsle.requestResponse(self.packet)
        self.assertEqual(result, 6)

    def test_requestResponseException(self):
        try:
            200 / 0
        except Exception as e:
            fake_response = self.packet.createReply(data={"exception": e})
        self.myIsle.connection.routerSend(fake_response)
        with self.assertRaises(ZeroDivisionError):
            result = self.myIsle.requestResponse(self.packet)

    def test_handleIslet(self):
        myPacket = self.packet.createReply({"args": (3,6), "kwargs":{}})
        myPacket.receiver = ["add", "eiland"]
        self.myIsle.connection.routerSend(myPacket)
        self.myIsle._Isle__handleIncomingPackets()
        response = self.myIsle.connection.routerReceive()
        self.assertIsNotNone(response)
        self.assertEqual(response.data["return"], 9)