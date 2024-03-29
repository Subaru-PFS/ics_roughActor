import logging
import socket

from opscore.utility.qstr import qstr

class pump(object):
    def __init__(self, actor, name,
                 loglevel=logging.INFO):

        self.actor = actor
        self.name = name
        self.logger = logging.getLogger(self.name)
        self.logger.setLevel(loglevel)

        self.EOL = b'\r'

        self.host = self.actor.actorConfig[self.name]['host']
        self.port = self.actor.actorConfig[self.name]['port']

    def start(self, cmd=None):
        pass

    def stop(self, cmd=None):
        pass

    def sendOneCommand(self, cmdStr, cmd=None):
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
            cmd.warn('text="failed to create socket to rough: %s"' % (e))
            raise
 
        try:
            s.connect((self.host, self.port))
            s.sendall(fullCmd)
        except socket.error as e:
            cmd.warn('text="failed to create connect or send to rough: %s"' % (e))
            raise

        try:
            ret = s.recv(1024)
        except socket.error as e:
            cmd.warn('text="failed to read response from rough: %s"' % (e))
            raise

        self.logger.info('received %r', ret)
        cmd.diag('text="received %r"' % ret)
        s.close()

        return ret.decode('latin-1')

    def parseReply(self, cmdStr, reply, cmd=None):
        cmdType = cmdStr[:1]

        if cmdType == '?':
            replyFlag = '='
        elif cmdType == '!':
            replyFlag = '*'

        replyStart = reply[:5]
        replyCheck = replyFlag + cmdStr[1:5]
        if not reply.startswith(replyCheck):
            cmd.warn('text=%s' % qstr('reply to command %r is the unexpected %r (vs %r)' % (cmdStr,
                                                                                            replyStart,
                                                                                            replyCheck)))
        return reply[5:].strip().split(';')

    def ident(self, cmd=None):
        cmdStr = '?S801'

        ret = self.sendOneCommand(cmdStr, cmd=cmd)
        reply = self.parseReply(cmdStr, ret, cmd=cmd)

        return reply

    def startPump(self, cmd=None):
        cmdStr = '!C802 1'

        ret = self.sendOneCommand(cmdStr, cmd=cmd)
        reply = self.parseReply(cmdStr, ret, cmd=cmd)

        return reply

    def stopPump(self, cmd=None):
        cmdStr = '!C802 0'

        ret = self.sendOneCommand(cmdStr, cmd=cmd)
        reply = self.parseReply(cmdStr, ret, cmd=cmd)

        return reply

    def startStandby(self, percent=90, cmd=None):
        cmdStr = "!S805 %d" % (percent)
        ret = self.sendOneCommand(cmdStr, cmd=cmd)

        cmdStr = "!C803 1"
        ret = self.sendOneCommand(cmdStr, cmd=cmd)
        return ret

    def stopStandby(self, cmd=None):
        cmdStr = "!C803 0"
        ret = self.sendOneCommand(cmdStr, cmd=cmd)
        return ret

    def errorString(self, errorMask):
        errorFlags = ('bit 0',
                      'Over voltage trip',
                      'Over current trip',
                      'Over temperature trip',
                      'Under temperature trip',
                      'Power stage fault',
                      'bit 6',
                      'bit 7',
                      'H/W fault latched',
                      'EEPROM fault',
                      'bit10',
                      'Parameters not loaded',
                      'Self test fault',
                      'Serial mode interlock',
                      'Overload timeout',
                      'Acceleration timeout')
                      
        errors = []
        for i in range(16):
            if errorMask & (1 << i):
                errors.append(errorFlags[i])

        return errors
    
    def statusWord(self, status, cmd=None):
        flags = ('Decelerating',
                 'Running/Accelerating',
                 'Standby speed',
                 'Normal speed',
                 'Above ramp speed',
                 'Above overload speed',
                 'Control mode bit 0',
                 'Control mode bit 1',
                 'bit 8',
                 'bit 9',
                 'Serial enable',
                 'bit 11',
                 'bit 12',
                 'Control mode bit 2',
                 'bit 14',
                 'bit 15',
                 
                 'Power limit active',
                 'Acceleration limited',
                 'Deceleration limited',
                 'bit 19',
                 'Service due!',
                 'bit 21',
                 'Warning active',
                 'Alarm active',
                 'bit 24',
                 'bit 25',
                 'bit 26',
                 'bit 27',
                 'bit 28',
                 'bit 39',
                 'bit 30',
                 'bit 31')

        warningFlags = ('bit 0',
                        'Pump temperature low',
                        'bit 2',
                        'bit 3',
                        'bit 4',
                        'bit 5',
                        'Pump temperature high',
                        'bit 7',
                        'bit 8',
                        'bit 9',
                        'Pump temperature above max',
                        'bit 11',
                        'bit 12',
                        'bit 13',
                        'bit 14',
                        'Self-test warning')

        allFlags = []
        statusWord = status[0]
        for i in range(32):
            if statusWord & (1 << i):
                allFlags.append(flags[i])

        warnings = []
        warningWord = status[1]
        for i in range(16):
            if warningWord & (1 << i):
                warnings.append(warningFlags[i])

        errorWord = status[2]
        errors = self.errorString(errorWord)
        
        if cmd is not None:
            cmd.inform('%sStatus=0x%04x,%r' % (self.name,
                                               statusWord, ', '.join(allFlags)))
            if len(warnings) > 0:
                cmd.warn('%sWarnings=0x%02x,%r' % (self.name,
                                                   warningWord, ','.join(warnings)))
            else:
                cmd.inform('%sWarnings=0x%02x,%r' % (self.name,
                                                     warningWord, 'OK'))
            if len(errors) > 0:
                cmd.warn('%sErrors=0x%02x,%r' % (self.name,
                                                 errorWord, ','.join(errors)))
            else:
                cmd.inform('%sErrors=0x%02x,%r' % (self.name,
                                                   errorWord, 'OK'))
            return allFlags

    def quickStatus(self, cmd):
        cmdStr = '?V802'

        ret = self.sendOneCommand(cmdStr, cmd=cmd)
        reply = self.parseReply(cmdStr, ret, cmd=cmd)

        hz = int(reply[0])
        errorWord = int(reply[4], base=16)
        
        if errorWord == 0:
            status = "OK"
        else:
            status = self.errorString(errorWord)

        return hz, errorWord, status
    
    def speed(self, cmd=None):
        cmdStr = '?V802'

        ret = self.sendOneCommand(cmdStr, cmd=cmd)
        reply = self.parseReply(cmdStr, ret, cmd=cmd)

        hz = int(reply[0])
        status = ((int(reply[1], base=16) | (int(reply[2], base=16) << 16)),
                  int(reply[3], base=16),
                  int(reply[4], base=16))
        

        cmd.inform('pumpSpeed=%d' % (hz))
        self.statusWord(status, cmd=cmd)

        return hz, status

    def pumpTemp(self, cmd=None):
        cmdStr = '?V808'

        ret = self.sendOneCommand(cmdStr, cmd=cmd)
        temps = self.parseReply(cmdStr, ret, cmd=cmd)

        cmd.inform('pumpTemps=%d,%d' % (int(temps[0], base=10),
                                        int(temps[1], base=10)))

        return temps

    def pumpLifetimes(self, cmd=None):

        past = []
        left = []
        for q in 811, 810, 813:
            cmdStr = f'?V{q}'

            ret = self.sendOneCommand(cmdStr, cmd=cmd)
            reply = self.parseReply(cmdStr, ret, cmd=cmd)

            past.append(int(reply[0], base=10))
            if q == 813:
                left.append(int(reply[1], base=10))
        
        for q in 814, 815:
            cmdStr = f'?V{q}'

            ret = self.sendOneCommand(cmdStr, cmd=cmd)
            reply = self.parseReply(cmdStr, ret, cmd=cmd)

            left.append(int(reply[1], base=10))

        cmd.inform('pumpTimes=%d,%d,%d' % tuple(past))
        cmd.inform('pumpLife=%d,%d,%d' % tuple(left))

        return past, left
    
    def status(self, cmd=None):
        reply = []

        speeds = self.speed(cmd=cmd)
        # VAW = self.pumpVAW(cmd=cmd)
        temps = self.pumpTemp(cmd=cmd)
        reply.extend(speeds)
        # reply.extend(VAW)
        reply.extend(temps)

        ret = self.pumpLifetimes(cmd)
        return reply

    def pumpCmd(self, cmdStr, cmd=None):
        if cmd is None:
            cmd = self.actor.bcast

        ret = self.sendOneCommand(cmdStr, cmd)
        return ret

