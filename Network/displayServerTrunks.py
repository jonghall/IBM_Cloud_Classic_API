##
## Displays servers and the vlans that are trunked to the server
## Place APIKEY & Username in config.ini
## or pass via commandline  (example: displayServerTrunks.py -u=userid -k=apikey)
## 
## Based off of AddNetworkVlanTrunk.py 
##
##  Version: 1.0
##  Date: 2016-11-02
##  Author: Jim Cook - jcook@us.ibm.com
##
import SoftLayer, os, re, random, string, json, sys, configparser, argparse
from itertools import chain

filter=''
displayCsv=False
displayName=False

def initializeSoftLayerAPI():
    ## READ CommandLine Arguments and load configuration file
    global filter, displayCsv, displayName
    parser = argparse.ArgumentParser(description="This script is used to display existing host vlan trunking.")
    parser.add_argument("-u", "--username", help="SoftLayer API Username")
    parser.add_argument("-k", "--apikey", help="SoftLayer APIKEY")
    parser.add_argument("-c", "--config", help="config.ini file to load")
    parser.add_argument("-f", "--filter", help="host name filter (regular expression) to select a subset of the hosts in the report")
    parser.add_argument("-v", "--csv", help="display output as csv file",action='store_true',default=False)
    parser.add_argument("-n", "--name", help="display vlan name",action='store_true',default=False)

    args = parser.parse_args()

    if args.config != None:
        filename=args.configresou
    else:
        filename="config.ini"

    if args.filter == None:
        filter='.*'
    else:
        filter=args.filter

    displayCsv=args.csv
    displayName=args.name

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

def displayTrunks(name,hardwareid):
    global displayCsv, displayName	
    mask_object = "backendRouters,networkVlans,uplinkNetworkComponents"
    hardware = client['Hardware'].getObject(mask=mask_object, id=hardwareid)
    backendRouter = hardware['backendRouters'][0]['fullyQualifiedDomainName']
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
    output=name
    trunkList=[]
    for trunk in trunks:
        vlanName="NONAME"
        if 'name' in trunk['networkVlan']:
              vlanName=trunk['networkVlan']['name']
        e = "%s" % trunk['networkVlan']['vlanNumber']
        if displayName:
           e += " %s" % vlanName
        trunkList.append(e)
    trunkList=sorted(trunkList)
    for trunk in trunkList:
        if displayCsv:
           output += ","
        else:
           output += " "
        output += trunk	
    print (output)
    return

client = initializeSoftLayerAPI()
try:
     prog=re.compile(filter)
except:
     print("Oops...  Filter regular expression is not correct syntax, filter="+filter)
     exit() 
hardwarelist = client['Account'].getHardware()
for hardware in hardwarelist:
    if prog.match(hardware['fullyQualifiedDomainName']):
          displayTrunks(hardware['fullyQualifiedDomainName'],hardware['id'])

#            "VLAN Trunk #%s: %s (%s)" % (trunkindex, trunk['networkVlan']['name'], trunk['networkVlan']['vlanNumber']))
