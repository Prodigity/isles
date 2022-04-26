# Isles

Isles is a microservice inspired framework that helps you deal with threading.

Within isles every thread is known as an isle;
A separate entity that can only communicate with others by sending messages.

All messages are handled in the order they are received regardless of thread switching. This makes a message in a certain sense "atomic" and reduces your chances of creating race conditions. Effectively you don't need to use locks as long as the entire operation can be contained within one message.

If there are multiple messages involved with an operation, then locks still need to be used to prevent race conditions. Fortunately when to place these is easier to spot than in regular threading code!

Besides making it easier to not write code that has race conditions, isles has another advantage; logging.

All messages are routed and logged by the islemanager.

If something goes wrong, you can check the log and see every message that has been passed around; timestamp, sender, receiver, topic, data.
This makes it much easier to debug when thread switching is causing you trouble.

## Under development

Extend isles across several machines with special peerthrough nodes.

Plug into live sessions with interactive consoles and debug or fix on the spot.
