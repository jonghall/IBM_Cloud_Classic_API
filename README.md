**Jon-SL-scripts**
==============

Folder| Description
----- | -----------
Billing| Scripts associated with SoftLayer billing data
Misc| Miscelaneous Scripts
Network| Scripts associated with manipulating SoftLayer Network
Storage| Scripts used to report on or manipulate Storage Services
Provisioning| Provisioning Scripts
Ticketing| Scripts associated with accessing and creating SoftLayer Tickets
VirtualServers| Scripts associated with managing SoftLayer Virtual Servers

**Installation of SL API**

Install via pip:
```
$ pip install softlayer
```
Or you can install from source. Download source and run:

```
$ python setup.py install
```
The most up to date version of this library can be found on the SoftLayer GitHub public repositories: hhttps://github.com/softlayer/softlayer-python. Please post to the SoftLayer forums http://forums.softlayer.com/ or open a support ticket in the SoftLayer customer portal if you have any questions regarding use of this library.

**Installation of Jon-SL-scripts**

Download scripts into directory.

**Configuration of Jon-SL-scripts**
There are two methods to configure the USERNAME and API key to use with these scripts.


Create a config.ini file with your username and API key.  If you have not already generated a SoftLayer APIKEY log into http://control.softlayer.com, select Account - Users, click on Generate, then click View to view the API Key.  This value along with your username should be included in the config.ini file.  By default the script will read the config.ini file in the same directory as the script.   You can specify and alternate file or location with the -c argument.
```
[api]
username=  <== SoftLayer Username goes here.
apikey=   <== Softlayer APIKEY goes here.
```

Pass your username and APIKEY via command line argument
```
usage: script.py [-h] [-u USERNAME] [-k APIKEY] [-c CONFIG]

optional arguments:
  -h, --help            show this help message and exit
  -u USERNAME, --username USERNAME
                        SoftLayer API Username
  -k APIKEY, --apikey APIKEY
                        SoftLayer APIKEY
  -c CONFIG, --config CONFIG
                        config.ini file to load
```
