**Jon-SL-scripts**
==============
ConfigurationReport.py    | Print's detailed information about bare metal servers in account.

OrderFromQuote.py         | Order bare metal servers from saved quote.  Assign hostname, domain, and VLAN

addNetworkVlanTrunk.py    | Add existing VLAN to server's list of trunked vlans to enable VLAN tagging on switch port

removeNetworkVlanTrunk.py | Remove VLAN from server's list of trunked vlans to remove VLAN tagging on switch port

configuration_to_csv.py   | Write configuration report to CSV file for import into Excel


**Installation of SL API**

Install via pip:

$ pip install softlayer
Or you can install from source. Download source and run:

$ python setup.py install
The most up to date version of this library can be found on the SoftLayer GitHub public repositories: http://github.com/softlayer. Please post to the SoftLayer forums http://forums.softlayer.com/ or open a support ticket in the SoftLayer customer portal if you have any questions regarding use of this library.

**Installation of Jon-SL-scripts**

Download scripts into directory.

**Configuration of Jon-SL-scripts**

Download config.ini template and configure with your API key.  If user has not already generated a SoftLayer APIKEY log into http://control.softlayer.com, select Account - Users, click on Generate, then click View to viwe the APIKey.

[api]
username=  <== SoftLayer Username goes here.
apikey= <** Softlayer APIKEY found in control (Account - Users)


