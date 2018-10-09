#!/usr/bin/env python

import logging
from twisted.internet import reactor
import actorcore.ICC

class OurActor(actorcore.ICC.ICC):
    def __init__(self, name,
                 productName=None):

        """ Setup an Actor instance. See help for actorcore.Actor for details. """
        
        # This sets up the connections to/from the hub, the logger, and the twisted reactor.
        #
        super().__init__(name, productName=productName)

        self.everConnected = False
        self.monitors = dict()

    def connectionMade(self):
        if self.everConnected is False:
            logging.info("Attaching all controllers...")
            self.allControllers = [s.strip() for s in self.config.get(self.name, 'startingControllers').split(',')]
            self.attachAllControllers()
            self.everConnected = True

    def statusLoop(self, controller):
        try:
            self.callCommand("%s status" % (controller))
        except:
            pass

        if self.monitors[controller] > 0:
            reactor.callLater(self.monitors[controller],
                              self.statusLoopCB,
                              controller)

    def monitor(self, controller, period, cmd=None):
        if controller not in self.monitors:
            self.monitors[controller] = 0

        running = self.monitors[controller] > 0
        self.monitors[controller] = period

        if (not running) and period > 0:
            cmd.warn('text="starting %gs loop for %s"' % (self.monitors[controller],
                                                          controller))
            self.statusLoopCB(controller)
        else:
            cmd.warn('text="adjusted %s loop to %gs"' % (controller, self.monitors[controller]))

# To work
def main():
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', type=str, required=True,
                        help='runnng actor name: rough1 or rough2')
    parser.add_argument('--logLevel', default=logging.INFO, type=int, nargs='?',
                        help='logging level')
    args = parser.parse_args()
    
    theActor = OurActor(args.name,
                        productName='roughActor')
    theActor.run()

if __name__ == '__main__':
    main()
