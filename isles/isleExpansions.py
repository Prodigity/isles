from isles.isles import Isle, Packet
import socket, select, json

class Peer(Isle):
    """ Base class for isles with socket capabilities """
    def __init__(self, conn, addr):
        self.peerSocket = conn
        self.addr = addr
        self.rxBuffer = b''
        self.txBuffer = b''
        super().__init__()
        self.eventlooptasks.append(self.peerloop)
    
    @classmethod
    def createFromBoundSocket(cls, conn, addr):
        """ Pass in a bound socket you got from a server.accept() """
        return cls(conn, addr)

    @classmethod
    def createByConnecting(cls, host, port, timeout):
        """ Pass in the host and port of the server you wish this peer to be connected with """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s.connect((host, port))
        return cls(s, "Address format that I don't know by head so FIXME")

    def requestResponse(self, packet, timeout=3):
        """ TODO: Should I override requestResponse, make a new function? Integrate everything within the current packet system? """
        if packet.receiver[-1] != "peer":
            return super().requestResponse(packet, timeout)
        else:
            # Send packet:
            # - Remove 
            self.addPacketToTXBuffer()
            # Receive packet
            # COBIFY
            # Add to TX buffer
            # Check for RX responses
            
    def COBS_encode(self, raw_packet):
        # https://en.wikipedia.org/wiki/Consistent_Overhead_Byte_Stuffing
        """ Reversible algorithm that removes all but the last zero byte.
        Allow binary data to be send while still using a null terminator.
        
        Takes 1.6 seconds for 10 megabytes; fast enough for me at the moment.
        """
        
        assert raw_packet[-1] == 0, "Not null terminated!"
        
        raw_list = list(raw_packet)
        coby_list = []
        index = 0
        offset = 0
        while index < len(raw_list):
            if raw_list[index] == 0:
                coby_list.append((index - offset) + 1)
                coby_list += raw_list[offset:index]
                index += 1
                offset = index
            elif index - offset == 254:
                coby_list.append(255)
                coby_list += raw_list[offset:index]
                offset = index
            else:
                index += 1
        
        return bytes(coby_list) + b'\x00'
    
    def COBS_decode(self, raw_packet):
        assert raw_packet[-1] == 0, "Not null terminated!"
        pointer = raw_packet[0]
        index = 1
        offset = 1
        new_packet = b""

        while index < len(raw_packet):
            if index == pointer:
                if pointer < 255 or pointer == len(raw_packet) - 1:
                    new_packet += raw_packet[offset:index] + b"\x00"
                else:
                    new_packet += raw_packet[offset:index]
                pointer += raw_packet[index]
                offset = index + 1
            index += 1

        return new_packet

    def addPacketToTXBuffer(self, packet):
        # Serialize packet as objects can't be transmitted
        # Add null byte to denote the end of this packet
        # Add to txbuffer so that it can be send later on
        self.txBuffer += self.COBS_encode(packet.toBytes() + b'\x00')

    def socketSend(self):
        # Send whatever part of the txbuffer the socket is willing to eat
        # Remember what we didn't send.
        # Return how much we sent
        sent = self.peerSocket.send(self.txBuffer[:min(len(self.txBuffer), 4096)])
        self.txBuffer = self.txBuffer[sent:]
        return sent

    def socketReceive(self):
        # Get as much as 4096 bytes from the socket
        # Store it in our rxbuffer
        # Return how much we received
        data = self.peerSocket.recv(4096)
        self.rxBuffer += data
        return len(data)

    def readPacketFromRXBuffer(self):
        # Find packet within rxbuffer
        # Deserialize packet
        # Return packet otherwise return None
        if b'\x00' in self.rxBuffer:
            rawPacket, self.rxBuffer = self.rxBuffer.split(b'\x00', maxsplit=1)
            packet = Packet.createFromBytes(self.COBS_decode(rawPacket + b'x\00')[:-1])
            return packet
        else:
            return None

    def getSocketState(self):
        # Get the state of our socket
        isReadable, isWritable, isError = select.select(
            [self.peerSocket],
            [self.peerSocket],
            [],
            60 # timeout
        )
        return isReadable, isWritable, isError

    def peerloop(self):
        # Check what is up with our socket
        isReadable, isWritable, isError = self.getSocketState()

        # Send data to peer if we have any data in txBuffer and if the socket permits
        if self.peerSocket in isWritable and len(self.txBuffer) > 0:
            if self.socketSend() == 0:
                self.running = False # Client closed connection

        # Get data from peer if the socket permits
        if self.peerSocket in isReadable:
            if self.socketReceive() == 0:
                self.running = False # Client closed connection

    def shutdown(self):
        # Clean up socket before we shutdown this isle
        self.peerSocket.close()



class Peerthrough(Peer):
    """ Derived from Peer. Isle that acts as a proxy between the manager and an external peer """
    def setup(self):
        # If we receive a packet from the islemanager, we handle it with onReceivePacket
        self.onReceiveCall.append(self.onReceivePacket)

    def onReceivePacket(self, packet):
        # Gets called when we receive a packet from the islemanager
        # Changes sender and receiver address to reflect next routing point and response address route
        packet.receiver.pop()
        self.addPacketToTXBuffer(packet)
        return True

    def loop(self):
        # Send packet to isle if we have a packet in rxBuffer
        while (packet := self.readPacketFromRXBuffer()) is not None:
            packet.sender.append(self.identifier)
            self.sendPacket(packet)



class Server(Isle):
    """ Isle that accepts socket connections and creates Peers to handle those connections """
    def __init__(self, identifier, host='127.0.0.1', port=44168, peer=Peer):
        self.host = host
        self.port = 44168
        self.peer = peer
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        super().__init__(identifier)
    
    def peerIsleCreation(self, conn, addr):
        packet = self.createPacket(["islemanager"], {"command": "addIsle", "isle": self.peer(conn, addr)})
        self.sendPacket(packet)

    def loop(self):
         # This blocks. Do we need to be able to converse with server?
         # If so, we need to use Select() here. Food for thought.
        conn, addr = self.server_socket.accept()
        self.peerIsleCreation(conn, addr)