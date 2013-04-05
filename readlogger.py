import threading
import serial
import struct
import time
import base64
import requests
import logging

import settings
import sms

CONVERT_CRLF = 2
CONVERT_CR = 1
CONVERT_LF = 0
NEWLINE_CONVERISON_MAP = (b'\n', b'\r', b'\r\n')
LF_MODES = ('LF', 'CR', 'CR/LF')

REPR_MODES = ('raw', 'some control', 'all control', 'hex')

numeric_level = getattr(logging, settings.LOGLEVEL.upper(), None)
if not isinstance(numeric_level, int):
    raise ValueError('Invalid log level: %s' % settings.LOGLEVEL)
FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(filename=settings.LOGFILE, level=numeric_level, format=FORMAT)

logging.getLogger("meteorolopi").debug("Alive.")

class ReadLogger:
    def __init__(self):
        self.convert_outgoing = CONVERT_LF
        self.newline = NEWLINE_CONVERISON_MAP[self.convert_outgoing]
        self.dtr_state = True
        self.rts_state = True
        self.break_state = False
        self.datalock = threading.RLock()
        self.writelock = threading.RLock()
        if not self._autoprobe():
            logging.getLogger("meteorolopi").debug("No logger found")
            raise Exception("No logger found")
        
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
            if self.command_test():
                success = True
                break
        return success
        
    def command_baud(self, baud):
        """
        The manual says the BAUD command should return OK, but it does not, best solution: do not use at all, 9600
        Baud seems to be the only working baud rate anyway
        """
        b = "BAUD {0}".format(int(baud)).encode('utf-8')
        # self.sendokcommand(b, 0)
        d = self.sendcommand(b, 10)
        return d
    
    def command_test(self):
        t = self.sendcommand(b"TEST", 8)
        if t == b"\n\rTEST\n\r":
            return True
        else:
            return False
        
    def command_ver(self):
        t = self.sendokcommand(b"VER", 100)
        return t
    
    def command_nver(self):
        t = self.sendokcommand(b"NVER", 100)
        return t
    
    def command_loop(self):
        data = []
        t = self.sendackcommand(b"LOOP 1", 99)
        if len(t) == 99:
            fmt = "<cccbBHHhBhBBH7B4B4BB7BHbHHHHHHHHH4B4BBBH8B4BBHBBHHBBH"
            data = struct.unpack(fmt, t)
            # print(data)
            data = {
                # data[0:3] = 'LOO' - 3 bytes
                'bartrend': data[3],  # or 'P' for old firmwares - 1 byte
                # packet type : data[4] (=0) - 1 byte
                # next record : data[5] - 2 bytes
                'barometer': data[6],  # - 2 bytes
                'insidetemperature': data[7],  # - 2 bytes
                'insidehumidity': data[8],  # - 1 byte
                'outsidetemperature': data[9],  # - 2 bytes
                'windspeed': data[10],  # - 1 byte
                '10mavgwindspeed': data[11] * 10,  # - 1 byte -> convert to format of loop2 packet
                'winddirection': data[12],  # - 2 bytes
                # extra temperature 1 : data[13] - 1 byte
                # extra temperature 2 : data[14] - 1 byte
                # extra temperature 3 : data[15] - 1 byte
                # extra temperature 4 : data[16] - 1 byte
                # extra temperature 5 : data[17] - 1 byte
                # extra temperature 6 : data[18] - 1 byte
                # extra temperature 7 : data[19] - 1 byte
                # soil temperature 1 : data[20] - 1 byte
                # soil temperature 2 : data[21] - 1 byte
                # soil temperature 3 : data[22] - 1 byte
                # soil temperature 4 : data[23] - 1 byte
                # leaf temperature 1 : data[24] - 1 byte
                # leaf temperature 2 : data[25] - 1 byte
                # leaf temperature 3 : data[26] - 1 byte
                # leaf temperature 4 : data[27] - 1 byte
                'outsidehumidity': data[28],  # - 1 byte
                # extra humidity 1 : data[29] - 1 byte
                # extra humidity 2 : data[30] - 1 byte
                # extra humidity 3 : data[31] - 1 byte
                # extra humidity 4 : data[32] - 1 byte
                # extra humidity 5 : data[33] - 1 byte
                # extra humidity 6 : data[34] - 1 byte
                # extra humidity 7 : data[35] - 1 byte
                'rainrate': data[36],  # - 2 bytes
                'uvindex': data[37],  # - 1 byte
                'solarradiation': data[38],  # - 2 bytes
                'stormrain': data[39],  # - 2 bytes
                'startdateofcurrentstorm': data[40],  # - 2 bytes
                'dailyrain': data[41],  # - 2 bytes
                'monthlyrain': data[42],  # - 2 bytes
                'yearlyrain': data[43],  # - 2 bytes
                # ET: Evapotranspiration
                'dailyet': data[44],  # - 2 bytes
                'monthlyet': data[45],  # - 2 bytes
                'yearlyet': data[46],  # - 2 bytes
                # soil moisture 1 : data[47] - 1 byte
                # soil moisture 2 : data[48] - 1 byte
                # soil moisture 3 : data[49] - 1 byte
                # soil moisture 4 : data[50] - 1 byte
                # leaf wetness 1 : data[51] - 1 byte
                # leaf wetness 2 : data[52] - 1 byte
                # leaf wetness 3 : data[53] - 1 byte
                # leaf wetness 4 : data[54] - 1 byte
                # inside alarms : data[55] - 1 byte
                # rain alarms : data[56] - 1 byte
                # outside alarms : data[57] - 2 bytes
                # extra temperature/humidity alarms 1 : data[58] - 1 byte
                # extra temperature/humidity alarms 2 : data[59] - 1 byte
                # extra temperature/humidity alarms 3 : data[60] - 1 byte
                # extra temperature/humidity alarms 4 : data[61] - 1 byte
                # extra temperature/humidity alarms 5 : data[62] - 1 byte
                # extra temperature/humidity alarms 6 : data[63] - 1 byte
                # extra temperature/humidity alarms 7 : data[64] - 1 byte
                # extra temperature/humidity alarms 8 : data[65] - 1 byte
                # soil and leaf alarms 1 : data[66] - 1 byte
                # soil and leaf alarms 2 : data[67] - 1 byte
                # soil and leaf alarms 3 : data[68] - 1 byte
                # soil and leaf alarms 4 : data[69] - 1 byte
                'transmitterbatterystatus': data[70],  # - 1 byte
                'consolebatteryvoltage': data[71],  # - 2 bytes
                # forecast icons : data[72] - 1 byte
                # forecast rule number : data[73] - 1 byte
                'timeofsunrise': data[74],  # - 2 bytes
                'timeofsunset': data[75],  # - 2 bytes
                # "\n" : data[76] - 1 byte
                # "\r" : data[77] - 1 byte
                # 'crc': data[78], - 2 bytes
                }
        return data
    
    def command_loop2(self):
        data = []
        t = self.sendackcommand(b"LPS 2 1", 99)
        if len(t) == 99:
            fmt = "<cccbBHHhBhBBHHHHHHHhBBBhhhHbHHHHHHHHBhhhhhBBBBBBBBBBBBHHHHHHBBH"
            data = struct.unpack(fmt, t)
            # print(data)
            data = {
                # data[0:3] = "LOO" - 3 bytes
                'bartrend': data[3],  # or 'P' for old firmware - 1 byte
                # packet type : data[4] (=1) - 1 byte
                # unused data[5] - 2 bytes
                'barometer': data[6],  # - 2 bytes
                'insidetemperature': data[7],  # - 2 bytes
                'insidehumidity': data[8],  # - 1 byte
                'outsidetemperature': data[9],  # - 2 bytes
                'windspeed': data[10],  # - 1 byte
                # unused data[11] # - 1 byte
                'winddirection': data[12],  # - 2 bytes
                '10mavgwindspeed': data[13],  # - 2 bytes
                '2mavgwindspeed': data[14],  # - 2 bytes
                '10mwindgust': data[15],  # - 2 bytes
                'winddirectionfor10mwindgust': data[16],  # - 2 bytes
                # unused data[17] # - 2 bytes
                # unused data[18] # - 2 bytes
                'dewpoint': data[19],  # - 2 bytes
                # unused data[20] # - 1 byte
                'outsidehumidity': data[21],  # - 1 byte
                # unused data[22] # - 1 byte
                'heatindex': data[23],  # - 2 bytes
                'windchill': data[24],  # - 2 bytes
                # THSW index : data[25] - Vantage Pro2 only # - 2 bytes
                'rainrate': data[26],  # - 2 bytes
                'uvindex': data[27],  # - 1 byte
                'solarradiation': data[28],  # - 2 bytes
                'stormrain': data[29],  # - 2 bytes
                'startdateofcurrentstorm': data[30],  # - 2 bytes
                'dailyrain': data[31],  # - 2 bytes
                'last15mrain': data[32],  # - 2 bytes
                'lasthourrain': data[33],  # - 2 bytes
                'dailyet': data[34],  # - 2 bytes
                'last24hrain': data[35],  # - 2 bytes
                # 'barometricreductionmethod': data[36], # - 1 byte
                # 'userenteredbarometricoffset': data[37], # - 2 bytes
                # barometric calibration number : data[38] # - 2 bytes
                # barometric sensor raw reading: data[39] # - 2 bytes
                # absolute barometric pressure: data[40] # - 2 bytes
                # altimeter setting : data[41] # - 2 bytes
                # unused data[42] # - 1 byte
                # unused data[43] # - 1 byte
                # next 10min wind speed graph pointer : data[44] # - 1 byte
                # next 15min wind speed graph pointer : data[45] # - 1 byte
                # next hourly wind speed graph pointer : data[46] # - 1 byte
                # next daily wind speed graph pointer : data[47] # - 1 byte
                # next minute rain graph pointer : data[48] # - 1 byte
                # next rain storm graph pointer : data[49] # - 1 byte
                # index to the minute within an hour : data[50] # - 1 byte
                # next monthly rain : data[51] # - 1 byte
                # next yearly rain : data[52] # - 1 byte
                # next seasonal rain : data[53] # - 1 byte
                # unused data[54] # - 2 bytes
                # unused data[55] # - 2 bytes
                # unused data[56] # - 2 bytes
                # unused data[57] # - 2 bytes
                # unused data[58] # - 2 bytes
                # unused data[59] # - 2 bytes
                # "\n" : data[60] # - 1 byte
                # "\r" : data[61] # - 1 byte
                # 'crc': data[62], # - 2 bytes
                }
            
        return data
    
    def preparemessage(self, lp, cleartext=False):
        fmt = ""
        cv = ""
        vs = []
        for v in settings.VALUES:
            if not v in lp:
                lp[v] = 0
            fmt += settings.VALUEFORMAT[v]
            if settings.VALUEFORMAT[v].lower() == "b":
                cv += "%03d" % lp[v]
            elif settings.VALUEFORMAT[v].lower() == "h":
                cv += "%05d" % lp[v]
            vs.append(lp[v])
        v = struct.pack(fmt, *vs)
        u = base64.b64encode(v)
        if cleartext:
            return cv
        else:
            return u
    
    def sendokcommand(self, commandstring, replybytes):
        d = self.sendcommand(commandstring, replybytes, self.okreader)
        return d
    
    def sendackcommand(self, commandstring, replybytes):
        d = self.sendcommand(commandstring, replybytes, self.ackreader)
        return d
    
    def sendcommand(self, commandstring, replybytes, reader=None):
        self.alive = True
        self.datalock.acquire()
        self.data = b""
        self.datalock.release()
        if reader is None:
            reader = self.reader
        self.receiver_thread = threading.Thread(target=reader, args=(replybytes,))
        # self.receiver_thread.setDaemon(1)
        self.receiver_thread.start()
        self.transmitter_thread = threading.Thread(target=self.writer, args=(commandstring,))
        # self.transmitter_thread.setDaemon(1)
        self.transmitter_thread.start()
        self.transmitter_thread.join()
        self.receiver_thread.join()
        self.serial.flushInput()
        return self.data

    def okreader(self, nobytes=0, waitfordone=False):
        pos = 0
        first = True
        try:
            while self.alive:
                if first:
                    data = self.serial.read(6)
                    if data != b'\n\rOK\n\r':
                        self.alive = False
                        break
                    first = False
                else:
                    if pos >= nobytes:
                        self.alive = False
                        break
                    data = self.serial.read(1)
                    if data == b'\n':
                        data = self.serial.read(1)
                        if data == b'\r':
                            self.alive = False
                            break
                    self.datalock.acquire()
                    self.data += data
                    self.datalock.release()
                    pos += 1
        except serial.SerialException as e:
            self.alive = False
            # would be nice if the console reader could be interruptted at this
            # point...
            raise

    def ackreader(self, nobytes=0, waitfordone=False):
        try:
            data = self.serial.read(1)
            if data != b'\x06':
                self.alive = False
                return
            if nobytes > 0:
                data = self.serial.read(nobytes)
                self.datalock.acquire()
                self.data += data
                self.datalock.release()
        except serial.SerialException as e:
            self.alive = False
            # would be nice if the console reader could be interruptted at this
            # point...
            raise

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

def main():
    r = ReadLogger()
    v1 = r.command_loop()
    time.sleep(1)
    v2 = r.command_loop2()
    v1.update(v2)
    m = r.preparemessage(v1, False)
    logging.getLogger("meteorolopi").debug("Read and prepared message")
    
    url = settings.SEND_TO_URL
    if url:
        params = {"text": m, "from": settings.SMS_FROM_NUMBER}
        requests.get(url, params=params)
        logging.getLogger("meteorolopi").debug("Sent to URL")
    
    if settings.SMS_TO_NUMBER:
        s = sms.SMS(settings.SMS_TO_NUMBER, settings.SMS_FROM_NUMBER, settings.SMS_COMMAND_FROM_NUMBER)
        logging.getLogger("meteorolopi").debug("About to send message")
        s.send(m)

if __name__ == '__main__':
    main()
