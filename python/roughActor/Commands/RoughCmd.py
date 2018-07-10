import opscore.protocols.keys as keys
import opscore.protocols.types as types
from opscore.utility.qstr import qstr

from twisted.internet import reactor

class RoughCmd(object):

    def __init__(self, actor):
        # This lets us access the rest of the actor.
        self.actor = actor

        # Declare the commands we implement. When the actor is started
        # these are registered with the parser, which will call the
        # associated methods when matched. The callbacks will be
        # passed a single argument, the parsed and typed command.
        #
        self.vocab = [
            ('pump', '@raw', self.roughRaw),
            ('pump', 'ident', self.ident),
            ('pump', 'status', self.status),
            ('pump', 'start', self.startRough),
            ('pump', 'stop', self.stopRough),
            ('pump', 'standby <percent>', self.standby),
            ('pump', 'standby off', self.standbyOff),

            ('loop', '@(off)', self.loop),
            ('loop', '<loopTime>', self.loop),
            
            ('gauge', '@raw', self.gaugeRaw),
            ('gauge', 'status', self.pressure),
            ('gauge', '<setRaw>', self.setRaw),
            ('gauge', '<getRaw>', self.getRaw),
        ]

        # Define typed command arguments for the above commands.
        self.keys = keys.KeysDictionary("xcu_rough", (1, 2),
                                        keys.Key("percent", types.Int(),
                                                 help='the speed for standby mode'),
                                        keys.Key("getRaw", types.Int(),
                                                 help='the MPT200 query'),
                                        keys.Key("loopTime", types.Float(),
                                                 help='how quickly to spin-loop status'),
                                        keys.Key("setRaw",
                                                 types.CompoundValueType(types.Int(help='the MPT200 code'),
                                                                         types.String(help='the MPT200 value'))),
                                        )

        self.loopState = None
        self.loopId = None
        
    def roughRaw(self, cmd):
        """ Send a raw command to the rough controller. """

        cmd_txt = cmd.cmd.keywords['raw'].values[0]

        ctrlr = cmd.cmd.name
        ret = self.actor.controllers[ctrlr].pumpCmd(cmd_txt, cmd=cmd)
        cmd.finish('text="returned %r"' % (ret))

    def _doLoop(self):
        if self.loopState is None:
            return

        cmd, loopTime = self.loopState
        try:
            hz, errorMask, errorString = self.actor.controllers['pump'].quickStatus(cmd)
        except Exception as e:
            hz = 0
            errorMask = 0xffff
            errorString = f"FAILED to get pump status: {e}"
            cmd.warn(f'text="{errorString}"')
            self._stopLoop(doFail=True)
            return
        
        try:
            pressure = self.actor.controllers['gauge'].pressure(cmd)
        except Exception as e:
            pressure = 9999
            cmd.warn(f'text="FAILED to get gauge status: {e}"')
            self._stopLoop(doFail=True)
            return

        isOK = (# hz == 150 and
                errorString == "OK" and
                pressure <= 1000)

        content = ('pressure=%g; pumpSpeed=%d; pumpErrors=0x%04x,%r' %
                   (pressure, hz, errorMask, errorString))
        if isOK:
            cmd.inform(content)
            self.loopId = reactor.callLater(loopTime, self._doLoop)
        else:
            cmd.warn(content)
            self._stopLoop(cmd, doFail=True)
            return
        
    def _stopLoop(self, cmd=None, doFail=False):
        if self.loopId is not None:
            self.loopId.cancel()
            self.loopId = None
        
        if self.loopState is not None:
            loopCmd, _ = self.loopState
            loopCmd.finish('text="loop stopped"', fail=doFail)
            if cmd is not None:
                cmd.inform('text="loop stopped"')
        else:
            if cmd is not None:
                cmd.warn('text="no loop to stop"')
        self.loopState = None

    def _startLoop(self, cmd, loopTime):
        loopTime = max(loopTime, 0.1)
        savedState = self.loopState
        if savedState is not None:
            self.loopState = None
            raise RuntimeError(f"roughing loop was found running! {savedState}")
        
        cmd.inform('text="starting %gs roughing loop' % (loopTime))
        self.loopState = cmd, loopTime
        self._doLoop()
        
    def loop(self, cmd):
        """ Start or stop a safety loop """
        cmdKeys = cmd.cmd.keywords
        turnOff = 'off' in cmdKeys
        if turnOff:
            loopTime = 0
        else:
            loopTime = cmdKeys['loopTime'].values[0]

        if loopTime == 0:
            self._stopLoop(cmd)
            cmd.finish()
        else:
            if self.loopState is not None:
                self._stopLoop(cmd)

            self._startLoop(cmd, loopTime)
            
    def ident(self, cmd):
        """ Return the rough ids. 

         - the rough model
         - DSP software version
         - PIC software version
         - full speed in RPM
         
        """
        ctrlr = cmd.cmd.name
        ret = self.actor.controllers[ctrlr].ident(cmd=cmd)
        cmd.finish('ident=%s' % (','.join(ret)))

    def status(self, cmd):
        """ Return all status keywords. """
        ctrlr = cmd.cmd.name
        self.actor.controllers[ctrlr].status(cmd=cmd)
        cmd.finish()

    def standby(self, cmd):
        """ Go into standby mode, where the pump runs at a lower speed than normal. """
        
        ctrlr = cmd.cmd.name
        percent = cmd.cmd.keywords['percent'].values[0]
        ret = self.actor.controllers[ctrlr].startStandby(percent=percent,
                                                         cmd=cmd)
        cmd.finish('text=%r' % (qstr(ret)))

    def standbyOff(self, cmd):
        """ Drop out of standby mode and go back to full-speed."""
        
        ctrlr = cmd.cmd.name
        ret = self.actor.controllers[ctrlr].stopStandby(cmd=cmd)
            
        cmd.finish('text=%r' % (qstr(ret)))

    def startRough(self, cmd):
        """ Turn on roughing pump. """
        
        ctrlr = cmd.cmd.name
        ret = self.actor.controllers[ctrlr].startPump(cmd=cmd)
        cmd.finish('text=%s' % (','.join(ret)))

    def stopRough(self, cmd):
        """ Turn off roughing pump. """

        ctrlr = cmd.cmd.name
        ret = self.actor.controllers[ctrlr].stopPump(cmd=cmd)
        cmd.finish('text=%s' % (','.join(ret)))

    def gaugeRaw(self, cmd):
        """ Send a raw command to a rough-side pressure gauge. """

        cmd_txt = cmd.cmd.keywords['raw'].values[0]
        ctrlr = cmd.cmd.name
        
        ret = self.actor.controllers[ctrlr].gaugeCmd(cmd_txt, cmd=cmd)
        cmd.finish('text="returned %s"' % (qstr(ret)))

    def getRaw(self, cmd):
        """ Send a direct query command to the PCM's gauge controller. """

        ctrlr = cmd.cmd.name
        cmdCode = cmd.cmd.keywords['getRaw'].values[0]
        
        ret = self.actor.controllers[ctrlr].gaugeRawQuery(cmdCode, cmd=cmd)
        cmd.finish('text=%s' % (qstr("returned %r" % ret)))

    def setRaw(self, cmd):
        """ Send a direct control command to the PCM's gauge controller. """

        ctrlr = cmd.cmd.name
        parts = cmd.cmd.keywords['setRaw'].values[0]
        cmdCode, cmdValue = parts

        cmd.diag('text="code=%r, value=%r"' % (cmdCode, cmdValue))
    
        ret = self.actor.controllers[ctrlr].gaugeRawSet(cmdCode, cmdValue, cmd=cmd)
        cmd.finish('text=%s' % (qstr("returned %r" % ret)))

    def pressure(self, cmd):
        """ Fetch the latest pressure reading from a rough-side pressure gauge. """
        
        ctrlr = cmd.cmd.name
        ret = self.actor.controllers[ctrlr].pressure(cmd=cmd)
        cmd.finish('pressure=%g' % (ret))

        
