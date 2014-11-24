# #
## write configuration data to CSV files
##

import SoftLayer, socket
from pprint import pprint as pp
import sys, json, string, csv, sys, codecs

client = SoftLayer.Client(username=sys.argv[1], api_key=sys.argv[2])

## PROMPT FOR Files to use
outputname = input("Filename to output: ")

## OPEN CSV FILE FOR OUTPUT
fieldnames = ['datacenter', 'hostname', 'frontendvlan', 'frontendip', 'frontendmac', 'frontendspeed', 'frontendstatus',
              'backendvlan', 'backendip', 'backendmac', 'backendspeed', 'backendstatus', 'backendrouter',
              'trunkedvlans', 'mgmtip', 'mgmtmac']

outfile = open(outputname, 'w')
csvwriter = csv.writer(outfile, delimiter='\t', quotechar='"', quoting=csv.QUOTE_ALL)

csvwriter = csv.DictWriter(outfile, delimiter=',', fieldnames=fieldnames)
csvwriter.writerow(dict((fn, fn) for fn in fieldnames))


#
# GET LIST OF ALL DEDICATED HARDWARE IN ACCOUNT
#

hardwarelist = client['Account'].getHardware(mask='datacenterName')

for hardware in hardwarelist:
    #    if hardware['datacenterName'] != 'Paris 1':
    #        continue

    hardwareid = hardware['id']

    #
    # LOOKUP HARDWARE INFORMATION BY HARDWARE ID
    #

    mask_object = "backendRouters,datacenterName,networkVlans,backendNetworkComponentCount,backendNetworkComponents,frontendNetworkComponentCount,frontendNetworkComponents,uplinkNetworkComponents"
    hardware = client['Hardware'].getObject(mask=mask_object, id=hardwareid)


    # FIND uplink network Index Number
    index = 0
    for uplink in hardware['uplinkNetworkComponents']:
        if uplink['name'] == "eth" and 'primaryIpAddress' in uplink.keys():
            uplinkid = uplink['id']
            ethindex = index
        if uplink['name'] == "mgmt": mgmtindex = index
        index = index + 1

    # Get Network Component ID for Uplink
    network = client['Network_Component'].getObject(mask='uplinkComponent', id=uplinkid)
    networkcomponentid = network['uplinkComponent']['id']

    # Get VLAN Trunks for network_compondent ID
    trunks = client['Network_Component'].getNetworkVlanTrunks(mask='networkVlan', id=networkcomponentid)
    #print (json.dumps(trunks, indent=4))

    # FIND Mgmt Index Number
    index = 0
    for backend in hardware['backendNetworkComponents']:
        if backend['name'] == "mgmt":
            mgmtindex = index
            continue
        index = index + 1


    # create list of trunked vlans

    trunkedvlans = ''
    for trunk in trunks: trunkedvlans = trunkedvlans + str(trunk['networkVlan']['vlanNumber']) + " "

    if 'primaryIpAddress' in hardware.keys():
        row = {
            'datacenter': hardware['datacenterName'],
            'hostname': hardware['fullyQualifiedDomainName'],
            'frontendvlan': hardware['networkVlans'][1]['vlanNumber'],
            'frontendip': hardware['primaryIpAddress'],
            'frontendmac': hardware['frontendNetworkComponents'][0]['macAddress'],
            'frontendspeed': hardware['frontendNetworkComponents'][0]['speed'],
            'frontendstatus': hardware['frontendNetworkComponents'][0]['status'],
            'backendvlan': hardware['networkVlans'][0]['vlanNumber'],
            'backendip': hardware['uplinkNetworkComponents'][ethindex]['primaryIpAddress'],
            'backendmac': hardware['uplinkNetworkComponents'][ethindex]['macAddress'],
            'backendspeed': hardware['uplinkNetworkComponents'][ethindex]['speed'],
            'backendstatus': hardware['uplinkNetworkComponents'][ethindex]['status'],
            'backendrouter': hardware['backendRouters'][0]['fullyQualifiedDomainName'],
            'trunkedvlans': trunkedvlans,
            'mgmtip': hardware['networkManagementIpAddress'],
            'mgmtmac': hardware['backendNetworkComponents'][mgmtindex]['ipmiMacAddress']
        }
    else:
        row = {
            'datacenter': hardware['datacenterName'],
            'hostname': hardware['fullyQualifiedDomainName'],
            'frontendvlan': '',
            'frontendip': '',
            'frontendmac': '',
            'frontendspeed': '',
            'frontendstatus': '',
            'backendvlan': hardware['networkVlans'][0]['vlanNumber'],
            'backendip': hardware['uplinkNetworkComponents'][ethindex]['primaryIpAddress'],
            'backendmac': hardware['uplinkNetworkComponents'][ethindex]['macAddress'],
            'backendspeed': hardware['uplinkNetworkComponents'][ethindex]['speed'],
            'backendstatus': hardware['uplinkNetworkComponents'][ethindex]['status'],
            'backendrouter': hardware['backendRouters'][0]['fullyQualifiedDomainName'],
            'trunkedvlans': trunkedvlans,
            'mgmtip': hardware['networkManagementIpAddress'],
            'mgmtmac': hardware['backendNetworkComponents'][mgmtindex]['ipmiMacAddress']
        }

    print(row)
    csvwriter.writerow(row)

##close CSV File
outfile.close()
