**Jon-SL-scripts**
==============

Script | Description
------ | -----------
ConfigurationReport.py | Print's detailed information about bare metal servers in account.
OrderFromQuote.py | Order bare metal servers from saved quote.  Assign hostname, domain, and VLAN
addNetworkVlanTrunk.py | Add existing VLAN to server's list of trunked vlans to enable VLAN tagging on switch port
removeNetworkVlanTrunk.py | Remove VLAN from server's list of trunked vlans to remove VLAN tagging on switch port
configuration_to_csv.py | Write configuration report to CSV file for import into Excel

**Installation of SL API**

Install via pip:
```
$ pip install softlayer
```
Or you can install from source. Download source and run:

```
$ python setup.py install
```
The most up to date version of this library can be found on the SoftLayer GitHub public repositories: http://github.com/softlayer. Please post to the SoftLayer forums http://forums.softlayer.com/ or open a support ticket in the SoftLayer customer portal if you have any questions regarding use of this library.

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
