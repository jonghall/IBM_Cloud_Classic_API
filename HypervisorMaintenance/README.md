**Jon-SL-scripts/HypervisorMaintenance**
==============
The following collection of scripts can be used to systematically power off SoftLayer Virtual Servers in
preparation for hypervisor maintenance.   The *PowerOffVirtualServers.py* script executes an OS soft shutdown, then 
when completed, powers off the VSI, leaving it permenently in the poweroff state in preparation for the maintenance
window. The *PowerOnVirtualServers.py* script can then be used to systematically power back on the VSI's after
the maintenance window is complete.


Script | Description
------ | -----------
PowerOffVirtualServers.py| Soft Shutdown, then power off virtual servers listed in order contained in CSV file
PowerOnVirtualServers.py| Power on virtual server in controlled fasion listed in order contained in CSV file
ShowVirtualServerPowerState.py| Show power state for all Virtual Server in specified datacenter
BuildServerListbyDC.py| Build CSV list from currently running servers in specified datacenter


Both scripts require a CSV input file with the list of VSI's to be powered on or off,  their order and any required
wait time between servers.   The CSV filename should be passed as a paramenter using the follwing format:
```
python PowerOffVirtualServers --input=filename.csv
```

To build a CSV for a maintenance window automatically use the *BuildServerListbyDC.py* script.  This script will build
a sequential list of servers with correct VSI ID numbers.  CSV file can then be modified to change order of servers to
be included.  Wait times between servers are set to 0 by default, but should be modified to suit your needs
particularily for the *PowerOnVirtualServers.py* script.  

To filter by a specfic datacenter specify the *--datecenter=* parameter.
```
python BuildServerListbyDC.py --datecenter=dal09 --output=serverlist.csv
```

*CSV Requirements*

Field | Required |Field Description
----- | -------- |-----------------
Order | Optional |field for tracking or sorting.  Not used by script
ID    | Optional |VSI ID (found via SLCLI VS LIST). If specified it will used instead of fullyQualifiedDomainName which may not be unique in SL (prefered). 
fullyQualifiedDomainName|Required|SL fullyQualifiedDomainName. Must be unique if you don't specify the correct VSI ID.  Script will it look up.
WAIT  | Required |Number of seconds to wait after powering on or off VM before moving to next VSI

Example CSV file
```
Order,id,fullyQualifiedDomainName,wait
1,13405579,centos02.ibmsldemo.com,60
2,13405577,centos01.ibmsldemo.com,30
3,13405581,centos03.ibmsldemo.com,30
```

The *ShowVirtualServerPowerState.py* script should be used to verify status after running scripts.  This script does not
require input and instead lists all VSI's and their power status in a Datacenter. 


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
