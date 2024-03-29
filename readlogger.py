import struct
import time
import base64
import requests
import logging
import sys

import settings
import sms

readertype = settings.TYPE
mod = __import__(readertype + '.reader', fromlist=['Reader'])
Reader = getattr(mod, 'Reader')

mod = __import__(readertype + '.values', fromlist=['VALUEFORMAT', 'VALUES'])
valueformat = getattr(mod, 'VALUEFORMAT')
values = getattr(mod, 'VALUES')

numeric_level = getattr(logging, settings.LOGLEVEL.upper(), None)
if not isinstance(numeric_level, int):
    raise ValueError('Invalid log level: %s' % settings.LOGLEVEL)
FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(filename=settings.LOGFILE, level=numeric_level, format=FORMAT)

logging.getLogger("meteorolopi").debug("Alive.")

def preparemessages(logger, types=None, cleartext=False):
    """
    Prepare the message(s) to be sent
    types is a list of message types to be prepared
    Returns a list of messages
    """
    data = logger.getData(types)
    msgs = []
    for msg in values:
        if (types is None) or (msg["type"] in types): 
            fmt = "B"
            cv = "%03d" % msg["type"]
            vs = [msg["type"], ]
            for v in msg["values"]:
                if not v in data:
                    data[v] = 0
                fmt += valueformat[v]
                if valueformat[v].lower() == "b":
                    cv += "%03d" % data[v]
                elif valueformat[v].lower() == "h":
                    cv += "%05d" % data[v]
                vs.append(data[v])
            v = struct.pack(fmt, *vs)
            u = base64.b64encode(v)
            if cleartext:
                msgs.append(cv)
            else:
                msgs.append(u)
    return msgs

def main():
    logger = Reader()
    types = None
    if len(sys.argv) > 1:
        types = [int(typestr) for typestr in sys.argv[1:]]
    msgs = preparemessages(logger, types)
    logging.getLogger("meteorolopi").debug("Message(s) prepared")
    for msg in msgs:
        if settings.SMS_TO_NUMBER:
            s = sms.SMS(settings.SMS_TO_NUMBER, settings.SMS_FROM_NUMBER, settings.SMS_COMMAND_FROM_NUMBER)
            logging.getLogger("meteorolopi").debug("About to send message")
            s.send(msg)
            logging.getLogger("meteorolopi").debug("Message sent")
        url = settings.SEND_TO_URL
        if url:
            params = {"text": msg, "from": settings.SMS_FROM_NUMBER}
            try:
                logging.getLogger("meteorolopi").debug("About to send message")
                r = requests.get(url, params=params)
                logging.getLogger("meteorolopi").debug("Sent to URL, status: ")
                logging.getLogger("meteorolopi").debug(r.status_code)
                i = 0
                while i < 5 and r.status_code >= 500:
                    # wait 1 minute, try again (max. 5 minutes) if still unsuccessful, give up
                    time.sleep(60)
                    i += 1
                    logging.getLogger("meteorolopi").debug("About to send message, next try")
                    r = requests.get(url, params=params)
                    logging.getLogger("meteorolopi").debug("Sent to URL, status: ")
                    logging.getLogger("meteorolopi").debug(r.status_code)
            except requests.exceptions.ConnectionError:
                logging.getLogger("meteorolopi").warn("Could not send request to url")

if __name__ == '__main__':
    main()
