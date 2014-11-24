__author__ = 'jonhall'
##
## Provision Servers from Stored Quote
##
# #

import SoftLayer, random, string, sys, json, os, configparser
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


def getQuote():
    ## Get Quotes from Account
    quotes = client['Account'].getQuotes()
    count=0
    for quote in quotes:
        count=count+1
        quoteid = quote['id']
        quotename = quote['name']
        print ("%s. %s - %s" % (count, quoteid, quotename))
    print ("")
    x=input ("Select Quote Number: ")
    quote = quotes[int(x)-1]
    quoteid = quote['id']
    return quoteid

def getBCR(datacenter):
    # Display avaialble VLANs in Datacenter
    bcrs = client['Location_Datacenter'].getBackendHardwareRouters(id=datacenter)
    count=0
    print ("")
    print ("Available Backend Control Routers")
    for bcr in bcrs:
        count=count+1
        print ("%s.  %s" % (count, bcr['fullyQualifiedDomainName']))
    print ("")
    x = int(input ("Select Backend Control Router to provision behind: "))
    bcrid = bcrs[x-1]['id']
    return bcrid

def getVlan(bcrid):
    # Display available VLANs in Datacenter
    vlans = client['Account'].getPrivateNetworkVlans(mask="primaryRouter")
    #print (json.dumps(vlans,indent=4))
    print ("")
    print ("Available VLANS for selected BCR")
    count=0
    table=[]
    for vlan in vlans:
        if vlan['primaryRouter']['id'] == bcrid:
            count = count + 1
            row = {'vlanid': vlan['id']}
            table.append(row)
            if 'name' in vlan.keys():
                print ("%s.  %s - %s" % (count, vlan['vlanNumber'],vlan['name']))
            else:
                print ("%s.  %s - no vlan name" % (count, vlan['vlanNumber']))
    print ("")
    x = int(input ("Select Vlan : "))
    vlanid = table[x-1]['vlanid']
    return vlanid

def getHostNames(quantity,vlanid):
    # Build list of host/domain dictionaries
    servernames=[]
    print ("")
    print ("Quote contains %s servers, enter hostname and domain for each.")
    for i in range(1,int(quantity)+1):
        servername={}
        print ("Server",i)
        host = input("Enter Hostname for server: ")
        domain = input("Enter Domain for server: ")
        # Set hostname, domainname, and VLAN of private interface
        servername = [{'hostname': host,
                          'domain': domain,
                          'primaryBackendNetworkComponent': {
                                'networkVlan': { 'id': vlanid},
                                 },
                          }]
        servernames.append(servername)
    return servernames

#
# Get APIKEY from config.ini & initialize SoftLayer API
#

client = initializeSoftLayerAPI("config.ini")

# Get the quote ID to work with
quoteid = getQuote()

# Get Quote Order Container for QuoteID
order = client['Billing_Order_Quote'].getREcalculatedOrderContainer(id=quoteid)
container = order['orderContainers'][0]

# Get VLAN for Quote datacenter & selected BCR
datacenter = container['locationObject']['id']
bcrid=getBCR(datacenter)
vlanid=getVlan(bcrid)

# Prompt for Host & Domain Names
quantity = container['quantity']
servers = getHostNames(quantity,vlanid)

# Modify Order Container with host, domain and VLAN
container['presetId'] = None
container['hardware'] = servers

print (json.dumps(container, indent=4))

verify = client['Billing_Order_Quote'].verifyOrder(container, id=quoteid)

print (json.dumps(verify, indent=4))
