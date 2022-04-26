from isles.isles import route, Isle, IsleManager
from threading import Thread

class Gibson(Isle):
    @route
    def secret(self, password):
        if password == "love":
            return "Access granted"
        else:
            return "Permission denied"

def notAnIsle(isleManager):
    # With tempisles we can still send requests to isles even if we are in a completely different thread from the rest
    with isleManager.createTempIsle() as tempisle:
        print(tempisle.call.gibson.secret("love"))

if __name__ == "__main__":
    isleManager = IsleManager()
    isleManager.addIsle(Gibson("gibson"))
    new_thread = Thread(target=notAnIsle,args=(isleManager,))
    new_thread.start()
    isleManager.start()
    new_thread.join()