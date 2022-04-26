import unittest
from isles.isles import SugarCall

class TestConnection(unittest.TestCase):
    def setUp(self):
        self.route = None
        self.args = None
        self.kwargs = None

    def createPacket(self, route, data):
        self.route = route
        self.args = data["args"]
        self.kwargs = data["kwargs"]
        return (self.route, self.args, self.kwargs)
    
    def requestResponse(self, packet):
        return packet

    def test_singleAttributeSingleArg(self):
        sugarcall = SugarCall([], self)
        sugarcall.a(12)
        self.assertEqual(self.route, ["a"])
        self.assertEqual(self.args, (12,))
        self.assertEqual(self.kwargs, {})
    
    def test_multipleAttributesSingleArg(self):
        sugarcall = SugarCall([], self)
        sugarcall.to.infinity.en.beyond(1000000000000)
        self.assertEqual(self.route, ["beyond", "en", "infinity", "to"])
        self.assertEqual(self.args, (1000000000000,))
        self.assertEqual(self.kwargs, {})
    
    def test_multipleAttributesMultipleArgs(self):
        sugarcall = SugarCall([], self)
        sugarcall.a.b.a.c(1,2,1,3)
        self.assertEqual(self.route, ["c","a","b","a"])
        self.assertEqual(self.args, (1,2,1,3,))
        self.assertEqual(self.kwargs, {})

    def test_multipleAttributesSingleKwarg(self):
        sugarcall = SugarCall([], self)
        sugarcall.a.b.b.a(foobar=1337)
        self.assertEqual(self.route, ["a","b","b","a"])
        self.assertEqual(self.args, ())
        self.assertDictEqual(self.kwargs, {"foobar":1337})

    def test_multipleAttributesMultipleKwargs(self):
        sugarcall = SugarCall([], self)
        sugarcall.a.b.b.a(foobar=1337, fazbaz=1336)
        self.assertEqual(self.route, ["a","b","b","a"])
        self.assertEqual(self.args, ())
        self.assertDictEqual(self.kwargs, {"foobar":1337, "fazbaz":1336})

    def test_multipleAttributesMultipleArgsAndKwargs(self):
        sugarcall = SugarCall([], self)
        sugarcall.s.u.g.a.r(1,2,3,4, "hoedje van hoedje van", papier=True, alu=False)
        self.assertEqual(self.route, ["r","a","g","u", "s"])
        self.assertEqual(self.args, (1,2,3,4, "hoedje van hoedje van",))
        self.assertDictEqual(self.kwargs, {"papier":True, "alu":False})