#
# Remove a Trunked VLAN from Server
#
import SoftLayer, os, random, string, json, sys, configparser, argparse
from itertools import chain


def initializeSoftLayerAPI():
    ## READ CommandLine Arguments and load configuration file
    parser = argparse.ArgumentParser(description="This script is used to trunk existing VLANs to a host.   This is often used to associate VLANs to a hypervisor host.")
    parser.add_argument("-u", "--username", help="SoftLayer API Username")
    parser.add_argument("-k", "--apikey", help="SoftLayer APIKEY")
    parser.add_argument("-c", "--config", help="config.ini file to load")

    args = parser.parse_args()

    if args.config != None:
        filename=args.config
    else:
        filename="config.ini"

    if (os.path.isfile(filename) is True) and (args.username == None and args.apikey == None):
        ## Read APIKEY from configuration file
        config = configparser.ConfigParser()
        config.read(filename)
        client = SoftLayer.Client(username=config['api']['username'], api_key=config['api']['apikey'])
    else:
        ## Read APIKEY from commandline arguments
        if args.username == None and args.apikey == None:
            print ("You must specify a username and APIkey to use.")
            quit()
        if args.username == None:
            print ("You must specify a username with your APIKEY.")
            quit()
        if args.apikey == None:
            print("You must specify a APIKEY with the username.")
            quit()
        client = SoftLayer.Client(username=args.username, api_key=args.apikey)
    return client

#
# Get APIKEY from config.ini & initialize SoftLayer API
#

client = initializeSoftLayerAPI()

# Lookup Hostname
fullyQualifiedDomainName = input("Fully qualified Domain name to remove VLAN trunk from: ")
hardwarelist = client['Account'].getHardware()

for hardware in hardwarelist:
    if hardware['fullyQualifiedDomainName'] == fullyQualifiedDomainName:
        hardwareid = hardware['id']
        continue

mask_object = "networkVlans,uplinkNetworkComponents"
hardware = client['Hardware'].getObject(mask=mask_object, id=hardwareid)

# Get Tunked VLAN details & remove

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

    vlantrunknum = int(input("VLAN Trunk # to remove: "))

    vlanid = [trunks[vlantrunknum - 1]['networkVlan']]
    vlanNumber = [trunks[vlantrunknum - 1]['networkVlan']['vlanNumber']]

    print("Removing vlan %s trunk for device %s." % (vlanNumber, fullyQualifiedDomainName))

    # Remove Selected VLAN from trunk using network component.  Trunk is actually removed from uplink
    result = client['Network_Component'].removeNetworkVlanTrunks(vlanid, id=networkcomponentid)
    print(json.dumps(result, indent=4))


except SoftLayer.SoftLayerAPIError as e:
    print("Error: %s, %s" % (e.faultCode, e.faultString))

