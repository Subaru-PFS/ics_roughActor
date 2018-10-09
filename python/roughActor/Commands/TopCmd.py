import opscore.protocols.keys as keys
import opscore.protocols.types as types
from opscore.utility.qstr import qstr

class TopCmd(object):

    def __init__(self, actor):
        # This lets us access the rest of the actor.
        self.actor = actor

        # Declare the commands we implement. When the actor is started
        # these are registered with the parser, which will call the
        # associated methods when matched. The callbacks will be
        # passed a single argument, the parsed and typed command.
        #
        self.vocab = [
            ('ping', '', self.ping),
            ('status', '', self.status),
            ('monitor', '<period>', self.monitor),
        ]

        # Define typed command arguments for the above commands.
        self.keys = keys.KeysDictionary("rough_rough", (1, 1),
                                        keys.Key("period", types.Int(),
                                                 help='the period to sample at.'),
                                        )

    def ping(self, cmd):
        """Query the actor for liveness/happiness."""

        cmd.warn("text='I am an empty and fake actor'")
        cmd.finish("text='Present and (probably) well'")

    def status(self, cmd):
        """Report camera status and actor version. """

        self.actor.sendVersionKey(cmd)
        
        cmd.inform('text="Present!"')
        cmd.finish()

    def monitor(self, cmd):
        """ Enable/disable/adjust period controller monitors. """

        period = cmd.cmd.keywords['period'].values[0]

        self.actor.monitor('gauge', period, cmd=cmd)
        cmd.finish()
