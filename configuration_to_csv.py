# #
## write configuration data to CSV files
## Place APIKEY & Username in config.ini
## or pass via commandline  (example: configuration_to_csv.py -u=userid -k=apikey)
##

import SoftLayer, socket, os, sys, json, string, csv, sys, codecs, configparser, argparse

def initializeSoftLayerAPI():
    ## READ CommandLine Arguments and load configuration file
    parser = argparse.ArgumentParser()
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
