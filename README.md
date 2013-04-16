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

TYPE - the type of the weather station logger. Currently only the Davis Vantage VUE is supported, so set TYPE=0
SMS_TO_NUMBER - The phone number to send the text message to
SMS_FROM_NUMBER - The phone number of the 3g dongle (this is actually only used for the GET request, see below)
SMS_COMMAND_FROM_NUMBER - Allow the given number to send commands via SMS (not used yet)
SEND_TO_URL - Perform a GET request containing the message on the given URL (this can be used for debugging the message) - set this to None
LOGLEVEL - Standard log levels, f.e. "DEBUG" or "INFO"
LOGFILE - the filename of the log file. Make sure that the current user has write access to this file (f.e. sudo touch /var/log/meteorolopi; sudo chown pi /var/log/meteorolopi)


Cron job
--------

To test the script, run the main script manually:
```
python readlogger.py
```
Watch for error messages, also check the log file.

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
This will send one SMS per 15 minutes! That sums up to almost 3000 SMS per month, so make sure your mobile plan supports that amount of SMS.


Extending
---------

For other weather station logger types, create a new subdirectory:
```
mkdir newtype
```
and create 3 files: __init__.py, readloggernewtype.py and values.py.

- __init__.py can be empty.
- readloggernewtype.py should import the values file and implement a class ReadLoggerNewtype which has at least the methods getValues and getData. The method getValues simply returns values.VALUES, and getData reads and returns the data from the logger.
- values.py contains the definition of the supported data.

The format of definition in values.py is:
```
VALUES = [ # array of message types that can be sent
    {       # first message type
            # type of message (0-255)
            # 0 - Davis Vantage Vue Loop/Loop2 data
            'type': 0,
            # format of individual measurements (signed/unsigned byte/word, see python struct module)
            'valueformat': {
                'bartrend': "b",
                'barometer': "H",
                'insidetemperature': "h",
                'insidehumidity': "B",
                'outsidetemperature': "h",
                'outsidehumidity': "B",
                'windspeed': "B",
                'winddirection': "H",
                '2mavgwindspeed': "H",
                '10mavgwindspeed': "H",
                '10mwindgust': "H",
                'winddirectionfor10mwindgust': "H",
                'dewpoint': "h",
                'heatindex': "h",
                'windchill': "h",
                'rainrate': "H",
                'uvindex': "b",
                'solarradiation': "H",
                'stormrain': "H",
                'startdateofcurrentstorm': "H",
                'dailyrain': "H",
                'monthlyrain': "H",
                'yearlyrain': "H",
                'last15mrain': "H",
                'lasthourrain': "H",
                'last24hrain': "H",
                'dailyet': "H",
                'monthlyet': "H",
                'yearlyet': "H",
                'timeofsunrise': "H",
                'timeofsunset': "H",
                'transmitterbatterystatus': "b",
                'consolebatteryvoltage': "H",
                },
            # which measurements are included in this message, define the order
            'values': (
                'bartrend',
                'barometer',
                'insidetemperature',
                'insidehumidity',
                'outsidetemperature',
                'outsidehumidity',
                'windspeed',
                'winddirection',
                '2mavgwindspeed',
                '10mavgwindspeed',
                '10mwindgust',
                'winddirectionfor10mwindgust',
                'dewpoint',
                'heatindex',
                'windchill',
                'rainrate',
                'uvindex',
                'solarradiation',
                'stormrain',
                'startdateofcurrentstorm',
                'dailyrain',
                'monthlyrain',
                'yearlyrain',
                'last15mrain',
                'lasthourrain',
                'last24hrain',
                'dailyet',
                'monthlyet',
                'yearlyet',
                'timeofsunrise',
                'timeofsunset',
                'transmitterbatterystatus',
                'consolebatteryvoltage',
                )
        },
        # add other data formats here
    ]
```
