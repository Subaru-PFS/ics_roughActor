from importlib import reload

import logging
import socket

from . import pfeiffer
reload(pfeiffer)

class gauge(pfeiffer.Pfeiffer):
    def __init__(self, actor, name,
                 loglevel=logging.INFO):

        self.actor = actor
        self.name = name
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(loglevel)

        self.EOL = b'\r'

        self.host = self.actor.actorConfig[self.name]['host']
        self.port = self.actor.actorConfig[self.name]['port']

        pfeiffer.Pfeiffer.__init__(self)

    def start(self, cmd=None):
        pass

    def stop(self, cmd=None):
        pass

    def sendOneCommand(self, cmdStr, cmd=None):
        """ Send a single line command and return response.

        Args
        ----
        cmdStr : str/bytes
           The string to send. bytes are OK and EOL is appended.

        Returns
        -------
        response : bytes

        """
        if cmd is None:
            cmd = self.actor.bcast

        try:
            cmdStr = cmdStr.encode('latin-1')
        except AttributeError:
            pass

        fullCmd = b"%s%s" % (cmdStr, self.EOL)
        self.logger.info('sending %r', fullCmd)
        cmd.diag('text="sending %r"' % fullCmd)

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
        except socket.error as e:
            cmd.warn('text="failed to create socket to %s: %s"' % (self.name, e))
            raise

        try:
            s.connect((self.host, self.port))
            s.sendall(fullCmd)
        except socket.error as e:
            cmd.warn('text="failed to create connect or send to %s: %s"' % (self.name, e))
            raise

        try:
            ret = s.recv(1024)
        except socket.error as e:
            cmd.warn('text="failed to read response from %s: %s"' % (self.name, e))
            raise

        self.logger.info('received %r', ret)
        cmd.diag('text="received %r"' % ret)
        s.close()

        return ret

    def gaugeRawCmd(self, cmdStr, cmd=None):
        gaugeStr = self.gaugeMakeRawCmd(cmdStr, cmd=cmd)
        ret = self.sendOneCommand(gaugeStr, cmd=cmd)

        return ret

    def gaugeCmd(self, cmdStr, cmd=None):
        if cmd is None:
            cmd = self.actor.bcast

        # ret = self.sendOneCommand(cmdStr, cmd)
        ret = self.gaugeRawCmd(cmdStr, cmd=cmd)
        return ret
