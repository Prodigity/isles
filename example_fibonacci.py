from isles.isles import route, Isle, IsleManager

class SimpleMath(Isle):
    @route
    def add(self, a, b):
        """ Custom function with route makes this 'callable' from other isles.
        The return value (or exception) is actually send back to the calling isle. """
        return a + b

class Fibonacci(Isle):
    def setup(self):
        """ setup runs once after __init__ """
        self.a = 0
        self.b = 1
    
    def next(self, a, b):
        """ Custom function """
        return b, self.call.simplemath.add(a, b)

    def loop(self):
        """ Pre-defined function that runs repeatedly """
        self.a, self.b = self.next(self.a, self.b)

if __name__ == "__main__":
    isleManager = IsleManager()
    isleManager.addIsle(SimpleMath("simplemath"))
    isleManager.addIsle(Fibonacci("fibonacci"))
    isleManager.start()