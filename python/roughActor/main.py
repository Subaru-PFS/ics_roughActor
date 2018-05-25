#!/usr/bin/env python

import actorcore.ICC

class OurActor(actorcore.ICC.ICC):
    def __init__(self, name,
                 productName=None, configFile=None,
                 modelNames=(),
                 debugLevel=20):

        """ Setup an Actor instance. See help for actorcore.Actor for details. """
        
        # This sets up the connections to/from the hub, the logger, and the twisted reactor.
        #
        actorcore.ICC.ICC.__init__(self, name, 
                                   productName=productName, 
                                   configFile=configFile)

#
# To work
def main():
    theActor = OurActor('rough', productName='roughActor')
    theActor.run()

if __name__ == '__main__':
    main()
