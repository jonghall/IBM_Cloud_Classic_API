# #
## ADD NETWORK VLAN TO TRUNK PORTS
##
##

import SoftLayer, os, random, string, json, sys, configparser
from itertools import chain


def initializeSoftLayerAPI(filename):
    # # READ configuration file
    if os.path.isfile(filename) is True:
        config = configparser.ConfigParser()
        config.read(filename)
        client = SoftLayer.Client(username=config['api']['username'], api_key=config['api']['apikey'])
    else:
        print("config.ini file missing.  Using command line arguments")
        client = SoftLayer.Client(username=sys.argv[1], api_key=sys.argv[2])
        quit()
    return client

#
# Get APIKEY from config.ini & initialize SoftLayer API
#

client = initializeSoftLayerAPI("config.ini")


# Lookup Hostname
fullyQualifiedDomainName = input("fully qualified Domain name: ")
hardwarelist = client['Account'].getHardware()

for hardware in hardwarelist:
    if hardware['fullyQualifiedDomainName'] == fullyQualifiedDomainName:
        hardwareid = hardware['id']
        continue

mask_object = "backendRouters,networkVlans,uplinkNetworkComponents"
hardware = client['Hardware'].getObject(mask=mask_object, id=hardwareid)
backendRouter = hardware['backendRouters'][0]['fullyQualifiedDomainName']

# Get Tunked VLAN details

try:
    # FIND uplink network Index Number
    index = 0
    for uplink in hardware['uplinkNetworkComponents']:
        if uplink['name'] == "eth" and 'primaryIpAddress' in uplink.keys():
            uplinkid = uplink['id']
            continue

    # Get Network Component ID for Uplink
    network = client['Network_Component'].getObject(mask='uplinkComponent', id=uplinkid)
    networkcomponentid = network['id']
    uplinkcomponentid = network['uplinkComponent']['id']

    # Get VLAN Trunks for network_compondent ID
    trunks = client['Network_Component'].getNetworkVlanTrunks(mask='networkVlan', id=uplinkcomponentid)

    trunkindex = 0
    for trunk in trunks:
        trunkindex = trunkindex + 1
        print(
            "VLAN Trunk #%s: %s (%s)" % (trunkindex, trunk['networkVlan']['name'], trunk['networkVlan']['vlanNumber']))

    print()
    print("Available VLANS (vlans may already be added)")
    vlans = client['Account'].getPrivateNetworkVlans(mask='primaryRouter')
    for vlan in vlans:
        if vlan['primaryRouter']['fullyQualifiedDomainName'] == backendRouter: print("%s" % (vlan['vlanNumber']))

    vlanNumber = int(input("VLAN to add to device: "))

    print("Adding vlan %s trunk for device %s." % (vlanNumber, fullyQualifiedDomainName))

    # Remove Selected VLAN from trunk using network component.  Trunk is actually removed from uplink

    vlanNumber = [{"vlanNumber": vlanNumber}]
    result = client['Network_Component'].addNetworkVlanTrunks(vlanNumber, id=networkcomponentid)
    print(json.dumps(result, indent=4))


except SoftLayer.SoftLayerAPIError as e:
    print("Error: %s, %s" % (e.faultCode, e.faultString))

