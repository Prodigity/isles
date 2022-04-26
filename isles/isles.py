""" Isles is a microservice inspired framework that helps you deal with threading.

For more information check the github page:


== Overview ==
Here are the most common parts you will have to deal with:

= class Isle =
Isles have their own threads and act like servers and/or clients.
They can interact with other isles by sending packets.
An Isle can make its functions public to other isles with the @route decorator.
Isles can send requests, responses and exceptions to one another.
An eventloop takes care of handling incoming packets, sleep and loop code.

= decorator @route =
Makes a function within an isle public, i.e.; callable by other isles. 

= class IsleManager =
The islemanager gets all the isles running, routes packets between them and also stops them.
It logs and prints all packets it routes for easy debugging.

= class TempIsle =
Allows threads that aren't isles to still call isle functions.
Primarily used to deal with codebases that use regular threading.

You typically won't have to deal with these, but there also is:

= class Packet =
Packets contain a sender, receiver, identifier/subject and data.
Their main purpose is to hold data and have the relevant information for routing.
It does not impose a standard on the contents of the data but it should preferably be suitable for marshalling.

= class Connection =
Holds packet queues between isle and islemanager with simple functions to send and retrieve packets.

= class SugarCall =
Enables a nicer way to send and receive packets. Instead of;
    packet = self.createPacket(["scrape", "Scraper"], {"args": "http://foobar.com"})
    result = self.requestResponse(packet)
This allows you to type;
    result = self.call.Scraper.scrape("http://foobar.com")

== Example ==
    from isles import Isle, IsleManager, route

    class serverIsle(Isle):
        @route
        def double(self, number):
            # This function can get called by other isles
            return number * 2

    class clientIsle(Isle)
        def setup(self):
            # This function only runs once
            self.myNumber = 1

        def loop(self):
            # This function is called repeatedly
            self.myNumber = self.call.server.double(self.myNumber)

    if __name__ == "__main__":
        isleManager = IsleManager()
        isleManager.addIsle(serverIsle(), "server")
        isleManager.addIsle(clientIsle(), "client")
        isleManager.start() # Loop forever unless one of the isles sends a stop packet.

Here "server" and "client" are each in their own threads.
The decorator @route denotes a function that is "public" for other isles.
To make it easier and cleaner to use, the packet system has been abstracted away behind function calls;
Simply call *self.call.ISLENAME.ISLEFUNCTION(args)* and you can just pretend you are directly dealing with functions.

Exceptions that are not caught within functions are passed on to the code that called them!
"""

from threading import Thread, Lock
import json
import uuid
import queue
import time
import signal

def threadContextSwitch():
    """ We call this in a thread to force a thread context switch to happen """
    # TODO: Replace this with Events and Conditions to be more efficient with CPU cycles.
    time.sleep(0.01)    

class Packet():
    """ Packets allow isles to send data to one another

    Packets are used for routing and do not enforce data contents
    Note: That is not currently properly reflected in toDict(), toBytes(), toJSON()
    
    Routing happens by explicitly describing the path to an Isle, e.g.;
        receiver = ["functionOfIsleXYZ", "IsleXYZ", "hostA"]
    Here hostA receives the packet first and sends it to IsleXYZ, who sends it to functionOfIsleXYZ

    When a packet is routed by anything else than the islemanager, the receiver and sender path is adjusted to reflect the new path;
        receiver    = ["functionOfIsleXYZ", "IsleXYZ", "hostA"]
        sender      = ["IsleABC"]
        ..routed by sockets from hostB to hostA ->
        receiver    = ["functionOfIsleXYZ", "IsleXYZ"]
        sender      = ["IsleABC", "hostB"]
        ..routed from IsleXYZ to functionOfIsleXYZ ->
        receiver    = ["functionOfIsleXYZ"]
        sender      = ["IsleABC", "hostB", "IsleXYZ"]

    The identifier has mainly two purposes;
    1) To associate responses to initial requests
    2) For tracing debugging purposes in the logs

    """
    def __init__(self, sender, receiver, data, identifier=None):
        """ Initialization of packet

        Args:
            sender (str): Identifier of the isle sending the packet
            receiver (str): Identifier of the isle intended to receive this packet
            data (dict?): Contents of the packet
            identifier (str): Identifier of the message subject.
        """
        if identifier is None:
            self.identifier = uuid.uuid4().hex
        else:
            self.identifier = identifier
        self.sender = sender
        self.receiver = receiver
        self.data = data

    def toDict(self):
        """ Return a dictionary representing this packet

        Returns:
            A dictionary containing the identifier, sender, receiver and data of this packet
        """
        return {
            "identifier": self.identifier,
            "sender": self.sender,
            "receiver": self.receiver,
            "data": self.data,
        }

    def toJSON(self):
        """ Returns a json string representation of this packet

        Returns:
            A json string containing the identifier, sender, receiver and data of this packet
        """
        return json.dumps(self.toDict(), separators=(',', ':'))

    def toBytes(self):
        """ Returns a byte converted json string representation of this packet

        Returns:
            Bytes representing a json string containing the identifier, sender, receiver and data of this packet
        """
        return self.toJSON().encode()

    def createReply(self, data):
        """ Creates a packet instance from an existing packet, reversing sender and receiver 

        Args:
            cls (obj): The class from which to instantiate a new Packet; Likely Packet itself
            packet (Packet): The packet from which a reply packet will be made
            data (dict): Data that you want to send back
        Returns:
            Packet instance ready to be send back as a reply
        """
        # TODO: Find out and document why I split this up into an instance method and a class method..
        return self.__createReply(self, data)

    @classmethod
    def __createReply(cls, packet, data):
        """ Creates a packet instance from an existing packet, reversing sender and receiver

        Args:
            cls (obj): The class from which to instantiate a new Packet; Likely Packet itself
            packet (Packet): The packet from which a reply packet will be made
            data (dict): Data that you want to send back
        Returns:
            Packet instance ready to be send back as a reply
        """
        return cls(sender=packet.receiver, receiver=packet.sender, data=data, identifier=packet.identifier)

    @classmethod
    def createFromBytes(cls, packetBytes):
        """ Creates a packet instance from a bytes representation
        Args:
            packetBytes (bytes): Bytes representing a packet """
        return cls.createFromJSON(packetBytes.decode())

    @classmethod
    def createFromJSON(cls, packetJSON):
        """ Creates a packet instance from a json string representation
        Args:
            packetJSON (str): JSON string representing a packet """
        return cls.createFromDict(json.loads(packetJSON))

    @classmethod
    def createFromDict(cls, packetRepresentation):
        """ Creates a packet instance from a dictionary representation
        Args:
            packetDict (dict): Dictionary representing a packet """
        return cls(packetRepresentation['sender'],
            packetRepresentation['receiver'],
            packetRepresentation['data'],
            packetRepresentation['identifier'])

class Connection():
    """ Connection provides a packet queue to and from the isle and islemanager.

    Both islemanager and the isle have a reference to the Connection object.
    The functions prefixed 'router' are for the islemanager and the prefix 'owner' is for the isle.
    """
    def __init__(self):
        """ Initializes this connection by creating two queues """
        self.toRouter = queue.Queue()
        self.toOwner = queue.Queue()

    def ownerSend(self, packet):
        """ Put a packet from the owner in the queue heading towards the router 
        Args:
            packet (Packet): Packet that you wish to send """
        self.toRouter.put(packet)

    def ownerReceive(self):
        """ Get packets from router
        Returns:
            A packet if there are any, otherwise it returns None """
        try:
            packet = self.toOwner.get_nowait()
        except queue.Empty:
            packet = None
        return packet

    def routerSend(self, packet):
        """ Put a packet from the router in the queue heading towards the owner 
        Args:
            packet (Packet): Packet that you wish to send """
        self.toOwner.put(packet)

    def routerReceive(self):
        """ Get packets from owner
        Returns:
            A packet if there are any, otherwise it returns None """
        try:
            packet= self.toRouter.get_nowait()
        except queue.Empty:
            packet = None
        return packet


# <syntatic sugar>
def route(func):
    """ Decorator that gives a function the attribute _route=True """
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    wrapper._route = True
    return wrapper

class SugarCall:
    """ Enables syntatic sugar for request & response in isles.

    Instead of using this code in your isle;
        packet = self.createPacket(["scrape", "Scraper"], {"args": "http://foobar.com"})
        result = self.requestResponse(packet)

    This allows you to type;
        result = self.call.Scraper.scrape("http://foobar.com")
    """
    def __init__(self, route, owner):
        """ Initialization code
        Args:
            route (list): Holds the route (=attributes) to the receiver of our packet
            owner (Isle): The owner of this SugarCall """
        self.route = route
        self.owner = owner
    
    def __getattr__(self, route):
        """ When an attribute of this instance is requested, it creates a new SugarCall instance, passes this attribute & all prior attributes and returns the instance.
        The new SugarCall instance has an attribute self.route that is a list of all attributes requested so far.
        This happens repeatedly until all attributes have been captured.

        Example:
            sugarcall = SugarCall([], None)
            sugarcall.a.b.c()
            ->
                1) creates SugarCall([a], sugarcall)
                2) creates SugarCall([b, a], sugarcall1)
                3) creates SugarCall([c, b, a], sugarcall2)
        
        Args:
            route (list): Holds the route (=attributes) to the receiver of our packet
        Returns:
            A new instance of a SugarCall with the next attribute included in the route
        """
        return self.createNewSugarCall([route] + self.route, self.owner)
    
    @classmethod
    def createNewSugarCall(cls, route, owner):
        """ Creates new instance of SugarCall
        
        Args:
            route (list): Holds the route (=attributes) to the receiver of our packet
            owner (Isle): The owner of this SugarCall
        Returns:
            A new instance of SugarCall
        """
        return cls(route, owner)
    
    def __call__(self, *args, **kwargs):
        """ When a SugarCall instance is finally called, this function is evoked.
        This sends a packet from our owner to the intended receiver.
        
        Args:
            args (list): Arguments (unnamed, by index) you wish to pass in your Packet
            kwargs (dict): Keyword arguments you wish to send to the function you are calling
        Returns:
            Instance of Packet containing a response
        """
        packet = self.owner.createPacket(self.route, {"args": args, "kwargs": kwargs})
        return self.owner.requestResponse(packet)

# </syntatic sugar>

class Isle():
    """ Isles have their own threads and act like servers and/or clients.

    They can interact with other isles by sending packets.
    An Isle can make its functions public to other isles with the @route decorator.
    Isles can send requests, responses and exceptions to one another.
    An eventloop takes care of handling incoming packets, sleep and loop code.    
    """
    def __init__(self, identifier=None):
        """ Initialization code

        Args:
            identifier (str): Optional identifier for this isle, will assume a random identifier if none is given
        Attributes:
            call (SugarCall): Syntatic sugar for sending and receiving packets. See SugarCall.
            identifier (str): Unique identifier for this isle
            connection (Connection): Object that holds the packets queues to and from the islemanager
            routes (dict): Maps the name of public functions to the reference of the functions themselves
            eventlooptasks (list): List of functions that must be executed in the eventloop
        """
        self.call = SugarCall([], self)
        if identifier is None:
            self.identifier = uuid.uuid4().hex
        else:
            self.identifier = identifier
        self.connection = Connection()
        self.routes = self._getRoutes()
        self.eventlooptasks = [
            self.loop,
            self.__handleIncomingPackets,
            threadContextSwitch,
        ]
        self.setup()
    
    def _getRoutes(self):
        """ Get a dictionary of all public functions

        Returns:
            Dictionary mapping name->reference of functions decorated by @route
         """
        routes = {}
        for attributename in dir(self):
            attributeref = getattr(self, attributename)
            if getattr(attributeref, '_route', None) is True:
                routes[attributename] = attributeref
        return routes

    def setup(self):
        """ Override setup in your subclass to do some initial variable setup """
        pass

    def loop(self):
        """ Override loop in your subclass to repeatedly run some code in this thread/isle """
        pass

    def shutdown(self):
        """ Override shutdown in your subclass to do some cleaning (closing files, sockets, connections) before the instance gets removed """
        pass

    def eventloop(self):
        """ Eventloop runs code in loop() if any, handles incoming messages, goes to sleep and repeats.
        
        If we receive a shutdown command, loop() will stop first and incoming messages will be handled for a few more seconds.
        Currently that is hardcoded to 3 seconds.
        """
        self.running = True
        while self.running:
            for task in self.eventlooptasks:
                task()
        self.shutdown()

    def __handleIncomingPackets(self):
        """ Handles all incoming packets except those captured by requestResponse

        - It deals with response packets that arrive too late
        - It deals with request packets meant for islets (public functions of isles)
        - It deals with shutdown packets

        Will loop through all messages in queue until it has dealt with them all
        """
        while (packet := self.connection.ownerReceive()):
            if (self.__handleTooLate(packet) or
                self.__handleIslet(packet) or
                self.__handleShutdown(packet)):
                pass # Packet was handled
            else:
                 # TODO: Determine a procedure for handling packets we don't have a clue what to do with
                reply = packet.createReply({"exception": Exception("Packet dropped: No takers.")})
                # self.sendPacket
                pass # Packet was dropped, tell islemanager?

    def __handleIslet(self, packet):
        """ Handles packets destined for islets (public functions)
        
        Args:
            packet (Packet): A packet we received
        Returns:
            True if this packet was meant for an islet, False if it wasn't
        """
        # TODO: Might want to consider giving packets a dedicated islet field to reduce ambiguity (Is this for an isle or islet?).
        # Checking length is not a very nice way of doing this.
        if len(packet.receiver) == 2:
            func = self.routes[packet.receiver[-2]]
            try:
                response = func(*packet.data["args"], **packet.data["kwargs"])
            except TypeError as e:
                print(self, packet.data["args"], packet.data["kwargs"])
                packet = packet.createReply({"exception": e})
            else:
                packet = packet.createReply({"return": response})
            self.sendPacket(packet)
            return True
        else:
            return False
    
    def __handleTooLate(self, packet):
        """ Handles response packets that decide to show up after we already timed out.
        
        Args:
            packet (Packet): A packet we received
        Returns:
            True if this packet contains a response, False if it does not
        """
        if "return" in packet.data:
            # Could consider telling islemanager for logging purposes.
            return True
        else:
            return False

    def __handleShutdown(self, packet):
        """ Handles the 'shutdown' packet
        
        Args:
            packet (Packet): A packet we received
        Returns:
            True if this packet tells us to shutdown, False if it does not
        """
        if packet.data == 'shutdown':
            self.running = False
            return True
        else:
            return False

    def createPacket(self, receiver, data):
        """ Creates a packet

        Automatically uses the identifier of this isle as the sender.
        
        Args:
            receiver (list): The path to the intended receiver for this packet
            data (dict): The data that goes into the packet
        Returns:
            A packet ready to be sent.
        """
        assert type(receiver) == list, "createPacket: receiver should be a list!"
        return Packet([self.identifier], receiver, data)

    def sendPacket(self, packet):
        """ Sends a packet 
        
        Args:
            packet (Packet): The packet to send
        Returns:
            The identifier/subject of the packet
        """
        self.connection.ownerSend(packet)
        return packet.identifier

    def requestResponse(self, packet, timeout=3):
        """ Send a packet containing a request and returns the result
        
        Args:
            packet (Packet): A packet containing a request
        Returns:
            The result that the receiver sends back
        
        Note: Raises an exception if a timeout occurs or if receiver sends an exception
        """
        receiver = packet.receiver
        identifier = self.sendPacket(packet)
        timestamp = time.time()
        while True:
            if time.time() > timestamp + timeout:
                raise TimeoutError(f"Packet timeout: isle {self.identifier}, identifier {identifier}, to {receiver}")
            if (receivedPacket := self.connection.ownerReceive()) is not None:
                if receivedPacket.identifier == identifier:
                    if "return" in receivedPacket.data:
                        return receivedPacket.data["return"]
                    elif "exception" in receivedPacket.data:
                        raise receivedPacket.data["exception"]
                    else:
                        print(receivedPacket.data)
                        raise Exception("Malformed packet received!") # TODO: Reconsider if isle should have to deal with this.
                else:
                    # We weren't looking for this packet, throw it to the back of the pipe..
                    # Inefficient because we might repeatedly come across the same packets before getting a reply.
                    # TODO: Create internal buffer to store already seen packets to increase efficiency.
                    self.connection.routerSend(receivedPacket)
            threadContextSwitch()

class IsleManager:
    """ Routes packets between isles, responsible for shutdown and logging"""
    def __init__(self, printToConsole=True):
        """ Initialization.
        
        Args:
            printToConsole (bool): Decides whether islemanager should print routed packets to the console
        Attributes:
            identifier (str): Name of this islemanager, currently hardcoded to 'islemanager'
            isles (dict): Dictionary mapping of name->reference of all the isles
            running (bool): Tells islemanager if we should continue running
            isles_lock (Lock): A lock we need to create temporary isles on the fly
            islesToBeAdded (list): Isles we want to create on the fly but haven't yet
            logbuffer (str): Buffer containing logdata we haven't thrown on the screen yet
            printToConsole (bool): Decides whether islemanager should print routed packets to the console
            shutdownTimer (None|int): Used to shutdown everything somewhat gracefully
        
        Note: We include signal.signal in there to do a clean shutdown when the user presses ctrl+c.
        """
        signal.signal(signal.SIGINT, self.sigint)
        self.identifier = "islemanager"
        self.isles = {}
        self.running = False
        self.isles_lock = Lock()
        self.islesToBeAdded = []
        self.logbuffer = ""
        self.printToConsole = printToConsole
        self.shutdownTimer = None
    
    def print(self, message):
        if self.printToConsole:
            print(message)

    def addIsle(self, isleInstance):
        """ Add an isle instance to our pool and spin up a thread for it
        
        Args:
            isleInstance (Isle): An instance of an isle you wish to add to the islemanager
        """
        thread = Thread(target = isleInstance.eventloop, name=isleInstance.identifier)
        self.isles[isleInstance.identifier] = {
            "connection": isleInstance.connection,
            "thread": thread
        }
        thread.start()

    def createTempIsle(self):
        """ Create a temporary Isle to allow non isle threads to get access to isle functionality

        Temporary isles acquire a lock on the islemanager to register and be able to get access to isle functionality from non isle threads.
        
        Example:
            with isleManager.createTempIsle() as myTempIsle:
                results = myTempIsle.call.ISLE.ISLET(foo, bar)
            print(results)
        
        Returns:
            An instance of TempIsle with context manager functionality
        """
        return self.TempIsle(self)
    
    class TempIsle(Isle):
        def __init__(self, isleManagerReference):
            super().__init__()
            self.isleManagerReference = isleManagerReference

        def __enter__(self):
            """ On enter, acquire lock from islemanager in order to safely add ourselves to the list of isles """
            with self.isleManagerReference.isles_lock:
                self.isleManagerReference.isles[self.identifier] = {
                    "connection": self.connection,
                    "thread": None
                }
            return self

        def __exit__(self, exception_type, exception_value, traceback):
            """ On exit, acquire lock from islemanager in order to safely remove ourselves from the list of isles"""
            with self.isleManagerReference.isles_lock:
                del self.isleManagerReference.isles[self.identifier]
            return None

    def createPacket(self, receiver, data):
        """ Creates a packet

        Args:
            receiver (list): Path to recipient of Packet
            data (dict): Data that should be included in the Packet
        Returns:
            Instance of a packet ready to be sent
        """
        return Packet(self.identifier, receiver, data)

    def start(self):
        """ Tells the islemanager to start running its eventloop
        If it leaves the eventloop it will initiate the shutdown sequence
        """
        self.running = True
        self.eventloop()
        self.stop()

    def sigint(self, signum, frame):
        """ Allow clean shutdown when the user presses ctrl+c """
        self.running = False

    def stop(self):
        """ Performs the shutdown sequence 
        
        1) Write any remaining logs to file
        2) Tell every isle to shutdown.. and log all of that too
        3) Wait for all the threads to stop
        """
        self.print("Performing shutdown sequence")
        self.writeLogBufferToFile() # Write log to file
        for isle in self.isles:
            self.print(f"Sending shutdown packet to {isle}..")
            packet = self.createPacket(isle, "shutdown")
            self.writeToLogBuffer(packet) # Add shutdown packets to logbuffer
            self.isles[isle]["connection"].routerSend(packet)
        self.writeLogBufferToFile() # Write log to file
        self.print("Waiting for threads to stop")
        for isle in self.isles:
            self.isles[isle]["thread"].join()
            self.print(f"Thread {isle} stopped")
        self.print("Stopping self")

    def handlePacket(self, packet):
        """ Handle command packets intended for the islemanager 
        
        If the packet data dict contains a "command" key it will perform the following, if value is equal to..
            "shutdown" -> Starts shutdown sequence
            "addIsle" -> Start the process of creating a new isle

        Args:
            packet (Packet): A packet directed to this islemanager containing a command
        """
        if "command" in packet.data:
            if packet.data["command"] == "shutdown":
                self.running = False
            elif packet.data["command"] == "addIsle":
                self.islesToBeAdded.append(packet.data["isle"])

    def writeToLogBuffer(self, packet):
        """ Write packet to logbuffer and print it on the screen 
        
        Args:
            packet (Packet): Packet to be logged and potentially printed
        """
        self.logbuffer += f"{round(time.time())}, {str(packet.sender)}, {str(packet.receiver)}, {packet.identifier}, {packet.data}\n"
        self.print(f"{str(packet.sender):36} -> {str(packet.receiver):36} : {packet.identifier} - {packet.data}")
    
    def writeLogBufferToFile(self):
        """ Write logbuffer to file """
        try:
            with open("log.txt", 'a') as logfile:
                logfile.write(self.logbuffer)
                self.logbuffer = ""
        except PermissionError:
            print(f"{round(time.time())} Could not write to log, will try again later.")

    def eventloop(self):
        """ The beating heart of the islemanager. Responsible for routing, logging and handling packets"""
        while self.running:                
            # This lock allows the creation of temporary isles from non isle threads
            with self.isles_lock: 
                # We visit all the isles
                for isle in self.isles:
                    # We grab their associated connection
                    connection = self.isles[isle]["connection"]
                    # For every packet the isle has for us..
                    while (packet := connection.routerReceive()):
                        # We first write it to our logbuffer
                        self.writeToLogBuffer(packet)

                        # If it contains an exception we make sure to write our logbuffer to our logfile
                        if "exception" in packet.data:
                            self.writeLogBufferToFile()
                        
                        # Is this packet for us? Then run our own packet handling code
                        if packet.receiver[-1] == self.identifier:
                            self.handlePacket(packet)
                        else:
                            # Do we know the intended receiver? Then send them the packet
                            if packet.receiver[-1] in self.isles:
                                self.isles[packet.receiver[-1]]["connection"].routerSend(packet)
                            else:
                                # Apparently we did not know the intended receiver. Tell the sender they made a mistake and log it.
                                reply = packet.createReply({"exception": KeyError(f"{packet.receiver[-1]} does not exist (anymore)")})
                                reply.sender = [self.identifier]
                                self.writeToLogBuffer(reply)
                                connection.routerSend(reply)
                    
                    # After handling everything related to this isle we make sure to write our logbuffer to file
                    self.writeLogBufferToFile()
                
                # Now we add new isles we were instructed to add
                for isle in self.islesToBeAdded:
                    self.addIsle(isle)
                
                # All have been added, clear list
                self.islesToBeAdded = []
                # TODO: Check for dead threads and remove them, should be as easy as checking isle["thread"].is_alive, doing a join and removing it from the dictionary
            # We did everything we wanted to do at the moment, put this thread to sleep
            threadContextSwitch()
