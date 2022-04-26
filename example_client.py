from isles.isles import Isle, IsleManager
from isles.isleExpansions import Peer, Server
import time

class MyPeer(Peer):
    def loop(self):
        packet = self.readPacketFromRXBuffer()
        if packet is not None:
            print(packet.data)

if __name__ == "__main__":
    isleManager = IsleManager()
    isleManager.addIsle(MyPeer.createByConnecting("localhost", 44168, 10))
    isleManager.start()