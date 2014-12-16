# #
## ADD NETWORK VLAN TO TRUNK PORTS
## Place APIKEY & Username in config.ini
## or pass via commandline  (example: addNetworkVlanTrunk.py -u=userid -k=apikey)
##

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
        filename=args.configresou
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

# ADD LISTS OF Hosts to add VLAN TRUNKS TO
hosts = ["resourcehost01.par01.bourso.net",
         "resourcehost02.par01.bourso.net",
         "resourcehost03.par01.bourso.net",
         "resourcehost04.par01.bourso.net",
         "resourcehost05.par01.bourso.net",
         "resourcehost06.par01.bourso.net",
         "resourcehost07.par01.bourso.net",
         "resourcehost08.par01.bourso.net",
         "resourcehost09.par01.bourso.net",
         "resourcehost10.par01.bourso.net"]


# Add Bulk List of VLAN numbers to add to above hosts
vlanNumber=[{"vlanNumber": 764}, {"vlanNumber": 765}, {"vlanNumber": 766}, {"vlanNumber": 767}]

# Lookup Hostname
for host in hosts:
    fullyQualifiedDomainName = host
    print("Adding vlan trunk(s) for device %s." % (fullyQualifiedDomainName))


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


        result = client['Network_Component'].addNetworkVlanTrunks(vlanNumber, id=networkcomponentid)
        print(json.dumps(result, indent=4))


    except SoftLayer.SoftLayerAPIError as e:
        print("Error: %s, %s" % (e.faultCode, e.faultString))

