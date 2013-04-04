import serial
import threading

from messaging.sms import SmsSubmit, SmsDeliver

import settings

CONVERT_CRLF = 2
CONVERT_CR = 1
CONVERT_LF = 0
NEWLINE_CONVERISON_MAP = (b'\n', b'\r', b'\r\n')

class SMS:
    # def __init__(self, number, port, baudrate, parity, rtscts, xonxoff, convert_outgoing=CONVERT_CRLF, repr_mode=0):
    def __init__(self, tonumber, fromnumber):
        self.tonumber = tonumber
        self.fromnumber = fromnumber
        convert_outgoing = CONVERT_CR
        self.convert_outgoing = convert_outgoing
        self.newline = NEWLINE_CONVERISON_MAP[self.convert_outgoing]
        self.dtr_state = True
        self.rts_state = True
        self.break_state = False
        self.datalock = threading.RLock()
        self.writelock = threading.RLock()
        if not self._autoprobe():
            raise Exception("No modem found")
        
    def _autoprobe(self):
        success = False
        baudrate = 9600
        parity = 'N'
        rtscts = False
        xonxoff = False
        timeout = 2
        for i in range(20):
            port = "/dev/ttyUSB{0}".format(i)
            try:
                self.serial = serial.serial_for_url(port, baudrate, parity=parity, rtscts=rtscts, xonxoff=xonxoff, timeout=timeout)
            except AttributeError:
                # happens when the installed pyserial is older than 2.5. use the
                # Serial class directly then.
                try:
                    self.serial = serial.Serial(port, baudrate, parity=parity, rtscts=rtscts, xonxoff=xonxoff, timeout=timeout)
                except:
                    continue
            except:
                continue
            d = self._sendcommand(b"ATE0", 10)
            if d == b"ATE0\r\nOK\r\n" or d == b"\r\nOK\r\n":
                success = True
                break
        return success

    def _sendcommand(self, commandstring, replybytes):
        self.alive = True
        self.datalock.acquire()
        self.data = b""
        self.datalock.release()
        self.receiver_thread = threading.Thread(target=self.reader, args=(replybytes,))
        # self.receiver_thread.setDaemon(1)
        self.receiver_thread.start()
        self.transmitter_thread = threading.Thread(target=self.writer, args=(commandstring,))
        # self.transmitter_thread.setDaemon(1)
        self.transmitter_thread.start()
        self.transmitter_thread.join()
        self.receiver_thread.join()
        self.serial.flushInput()
        return self.data
    
    def reader(self, nobytes=0, waitfordone=False):
        try:
            data = self.serial.read(nobytes)
            self.datalock.acquire()
            self.data = data
            self.datalock.release()
        except serial.SerialException as e:
            self.alive = False
            # would be nice if the console reader could be interruptted at this
            # point...
            raise

    def writer(self, data):
        try:
            self.writelock.acquire()
            self.serial.write(data)
            self.serial.write(self.newline)
            self.writelock.release()
        except:
            self.alive = False
            raise

    def send(self, message):
        # d = self.sendcommand(b"AT+CMGF=1", 10)
        # if d == b"\r\nOK\r\n":
        #    c = 'AT+CMGS="{0}"'.format(self.number).encode('utf-8')
        #    d = self.sendcommand(c, 10)
        #    if d == b"\r\n> ":
        #        message += "\x1a"
        #        d = self.sendcommand(message.encode('utf-8'), 10)
        d = self._sendcommand(b"AT+CMGF=0", 6)
        if d == b"\r\nOK\r\n":
            s = SmsSubmit(self.tonumber, message)
            pdus = s.to_pdu()
            for pdu in pdus:
                c = 'AT+CMGS={0}'.format(pdu.length).encode('utf-8')
                d = self._sendcommand(c, 4)
                if d == b"\r\n> ":
                    data = pdu.pdu[:]
                    data += "\x1a"
                    d = self._sendcommand(data.encode('utf-8'), 10)
                else:
                    self._sendcommand(b'\x1b', 10)
                    self._sendcommand(b'\x1a', 10)
        return d
    
    def check(self):
        d = self._sendcommand(b"AT+CMGF=0", 6)
        if d == b"\r\nOK\r\n":
            d = self._sendcommand(b"AT+CMGL=4", 10000)
            d = d.decode('utf-8').split("\r\n")
            i = 0
            while i < len(d):
                i += 1
                if d[i] == "OK":
                    break
                if d[i][0:7] == "+CMGL: ":
                    cmgl = d[i][7:].split(',')
                    ind = cmgl[0]
                    status = cmgl[1]
                    address_text = cmgl[2]
                    tpdu_length = cmgl[3]
                    i += 1
                    pdu = d[i]
                    s = SmsDeliver(pdu)
                    msg = s.data
                    if msg['number'] == settings.SMS_COMMAND_FROM_NUMBER:
                        # valid command
                        command = msg["text"]
                        print("Command: " + command)
                    else:
                        # not a valid from number - delete
                        pass
                    print(msg)
                i += 1
            # delete all stored SMS
            d = self._sendcommand(b"AT+CMGD=0,4", 10)
        return d
        
def main():
    # sms = SMS(settings.SMS_NUMBER, settings.GSM_DEVICE, 9600, 'N', False, False, CONVERT_CR)
    # s = sms.send("Test from stick to phone")
    # print(s)
    sms = SMS(settings.SMS_TO_NUMBER, settings.SMS_FROM_NUMBER)
    m = sms.check()
    print(m)
    
if __name__ == "__main__":
    main()
