#!/usr/bin/env python

import logging

import actorcore.ICC

class OurActor(actorcore.ICC.ICC):
    def __init__(self, name,
                 productName=None):

        """ Setup an Actor instance. See help for actorcore.Actor for details. """
        
        # This sets up the connections to/from the hub, the logger, and the twisted reactor.
        #
        super().__init__(name, productName=productName)
#
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
