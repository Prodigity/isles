from isles.isles import route, Isle, IsleManager
import time

class Creator(Isle):
    class Creation(Isle):
        def loop(self):
            self.call.creator.isleprint(f"Hello I am {self.identifier}")
            self.running = False
    
    @route
    def isleprint(self, text):
        pass # Could print(text), but the log shows everything already so..
        return None #?

    def setup(self):
        self.timestamp = time.time()

    def createChild(self):
        self.spawnChildrenPacket = self.createPacket(["islemanager"], {"command": "addIsle", "isle": self.Creation()})
        self.sendPacket(self.spawnChildrenPacket)

    def loop(self):
        if self.timestamp < time.time() - 1:
            self.createChild()
            self.timestamp = time.time()

if __name__ == "__main__":
    isleManager = IsleManager()
    isleManager.addIsle(Creator("creator"))
    isleManager.start()