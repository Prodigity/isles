from isles.isles import Isle, IsleManager
from isles.isleExpansions import Peer, Server
import time

class myPeer(Peer):
    def setup(self):
        self.timestamp = time.time()

    def loop(self):
        if self.timestamp + 1 < time.time():
            self.timestamp = time.time()
            packet = self.createPacket(["Islet", "Isle", "HostB"], f"The time is {self.timestamp}")
            self.addPacketToTXBuffer(packet)

if __name__ == "__main__":
    isleManager = IsleManager()
    isleManager.addIsle(Server("myServer", peer=myPeer))
    isleManager.start()