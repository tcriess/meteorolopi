MeteoroloPi
===========

MeteoroloPi is a small set of python scripts that read data from a weather station and send it away via SMS.

Disclaimer
----------

This project is released under the MIT License, see the LICENSE file. Some part of the serial communication code is heavily inspired by the python-serial demo-application miniterm by Chris Liechti.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.


Prerequisites
-------------

Hardware:
Raspberry Pi with debian, linux supported USB 3G dongle, weather station/logger with USB connection (currently supported: Davis Vantage VUE)
Software:
Make sure that python and necessary modules are installed:
```
apt-get install python-messaging python-requests python-serial
```

In some cases, the 3G dongle is not automatically set up correctly when booting the raspberry with the dongle plugged in. If this is the case for your setup, one solution is to include the following line in /etc/rc.local:
```
service udev stop ; service udev start
```


Installation
------------

Clone the repository somewhere, for example in /home/pi
```
git clone https://github.com/tcriess/meteorolopi.git
```

Copy the settings.py.dist file to settings.py
```
cd meteorolopi
cp settings.py.dist settings.py
```

Edit the settings:
```
nano settings.py
```


Settings
--------

TYPE - the type of the weather station logger. Currently only the Davis Vantage VUE is supported, so set TYPE="vue"
SMS_TO_NUMBER - The phone number to send the text message to
SMS_FROM_NUMBER - The phone number of the 3g dongle (this is actually only used for the GET request, see below)
SMS_COMMAND_FROM_NUMBER - Allow the given number to send commands via SMS (not used yet)
SEND_TO_URL - Perform a GET request containing the message on the given URL (this can be used for debugging the message) - set this to None
LOGLEVEL - Standard log levels, f.e. "DEBUG" or "INFO"
LOGFILE - the filename of the log file. Make sure that the current user has write access to this file, f.e. 
```
sudo touch /var/log/meteorolopi; sudo chown pi /var/log/meteorolopi
```

Note that the device names for the logging device and for the 3G dongle are determined by auto-probing the /dev/ttyUSB? device files. Depending on the reliability of the autoprobing this may change in the future.


Cron job
--------

To test the script, run the main script manually:
```
python readlogger.py
```
Watch for error messages, also check the log file. If only a subset of the supported message types are required, add the message type numbers as arguments, f.e.
```
python readlogger.py 0
```
would send only messages of type 0.

To set up a cron job:
```
crontab -e
```

Then append the following line:
```
0,15,30,45 * * * *  python -u /home/pi/meteorolopi/readlogger.py
```
(adjust the path if you have cloned the repository somewhere else)

*BIG FAT WARNING NOTICE:*
This will send one SMS every 15 minutes! That sums up to almost 3000 SMS per month, so make sure your mobile plan supports that amount of SMS.


Extending
---------

For other weather station logger types, create a new subdirectory just like the "vue" subdirectory:
```
mkdir newlogger
```
and create 3 files: __init__.py, reader.py and values.py.

- __init__.py can be empty.
- reader.py should import the values file and implement a class Reader which has at least the method getData, which reads and returns the data from the logger.
- values.py contains the definition of the supported data.

The format of definition in values.py is:
```
# The format of all possible measurements in python struct format (usually "B"/"b" for unsigned/signed bytes or "H"/"h" for unsigned/signed words)
VALUEFORMAT = {
    'measurement1': 'B',
    'measurement2': 'h',
}
# The structure of messages
VALUES = [ # array of message types that can be sent
    {       # first message type
            # type of message (0-255)
            # 0 - Davis Vantage Vue Loop/Loop2 data
            # 1 - new type
            'type': 1,
            # which measurements are included in this message, this also defines the order
            'values': (
                'mesaurement1',
                )
        },
        # add other message types here
    ]
```

Make sure that the message type is unique among all possible loggers! Currently, only message type 0 is reserved for the Davis Vantage VUE LOOP/LOOP2 message.

The implementation of the method getData in the Reader class expects a list of types (or None) and returns a list of dicts holding the data.
