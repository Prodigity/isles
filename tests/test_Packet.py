import unittest
from isles.isles import Packet

class TestPacket(unittest.TestCase):
    def setUp(self):
        self.packetA = Packet(sender=["Alice"], receiver=["Bob"], data={'a': 1, 'b':2, 'c':[3,4,5]}, identifier="Spam")
        self.packetB = Packet(sender=["Mario"], receiver=["Luigi"], data={'game': 'Super Mario Bros', 'lives': 12, 'score':1000, 'time':300}, identifier="Bro")
    
    def test_toDict(self):
        self.assertDictEqual(self.packetA.toDict(), {"sender":["Alice"], "receiver":["Bob"], "data": {'a': 1, 'b':2, 'c':[3,4,5]}, "identifier":"Spam"})
        self.assertDictEqual(self.packetB.toDict(), {"sender":["Mario"], "receiver":["Luigi"], "data": {'game': 'Super Mario Bros', 'lives': 12, 'score':1000, 'time':300}, "identifier":"Bro"})
    
    def test_toJSON(self):
        #   "identifier": self.identifier,
        #   "sender": self.sender,
        #   "receiver": self.receiver,
        #   "data": self.data,
        self.assertEqual(self.packetA.toJSON(), '{"identifier":"Spam","sender":["Alice"],"receiver":["Bob"],"data":{"a":1,"b":2,"c":[3,4,5]}}')
        self.assertEqual(self.packetB.toJSON(), '{"identifier":"Bro","sender":["Mario"],"receiver":["Luigi"],"data":{"game":"Super Mario Bros","lives":12,"score":1000,"time":300}}')
    
    def test_toBytes(self):
        self.assertEqual(self.packetA.toBytes(), b'{"identifier":"Spam","sender":["Alice"],"receiver":["Bob"],"data":{"a":1,"b":2,"c":[3,4,5]}}')
        self.assertEqual(self.packetB.toBytes(), b'{"identifier":"Bro","sender":["Mario"],"receiver":["Luigi"],"data":{"game":"Super Mario Bros","lives":12,"score":1000,"time":300}}')
    
    def test_createReply(self):
        replyA = self.packetA.createReply({"Foo":42})
        self.assertEqual(replyA.identifier, self.packetA.identifier)
        self.assertEqual(replyA.sender, self.packetA.receiver)
        self.assertEqual(replyA.receiver, self.packetA.sender)
        self.assertDictEqual(replyA.data, {"Foo":42})

        replyB = self.packetB.createReply({"Bar":9001})
        self.assertEqual(replyB.identifier, self.packetB.identifier)
        self.assertEqual(replyB.sender, self.packetB.receiver)
        self.assertEqual(replyB.receiver, self.packetB.sender)
        self.assertDictEqual(replyB.data, {"Bar":9001})
    
    def test_toAndCreateAll(self):
        marshalMethods = [
            ("toBytes", "createFromBytes"),
            ("toDict", "createFromDict"),
            ("toJSON", "createFromJSON"),
        ]
        for myPacket in [self.packetA, self.packetB]:
            for marshalMethod in marshalMethods:
                newPacket = getattr(Packet, marshalMethod[1])(getattr(myPacket, marshalMethod[0])())
                self.assertEqual(newPacket.identifier, myPacket.identifier)
                self.assertEqual(newPacket.sender, myPacket.sender)
                self.assertEqual(newPacket.receiver, myPacket.receiver)
                self.assertDictEqual(newPacket.data, myPacket.data)