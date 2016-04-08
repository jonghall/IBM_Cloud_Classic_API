__author__ = 'jonhall'
## List powerstate for VirtualServers in Datacenter


import SoftLayer, configparser, argparse, csv, json, pytz
from datetime import datetime, timedelta, tzinfo

def convert_timestamp(sldate):
    formatedDate = sldate
    formatedDate = formatedDate[0:22]+formatedDate[-2:]
    formatedDate = datetime.strptime(formatedDate, "%Y-%m-%dT%H:%M:%S%z")
    return formatedDate.astimezone(central)

def initializeSoftLayerAPI(user, key, configfile):
    if user == None and key == None:
        if configfile != None:
            filename=args.config
        else:
            filename="config.ini"
        config = configparser.ConfigParser()
        config.read(filename)
        client = SoftLayer.Client(username=config['api']['username'], api_key=config['api']['apikey'])
    else:
        #client = SoftLayer.Client(username=config['api']['username'], api_key=config['api']['apikey'],endpoint_url=SoftLayer.API_PRIVATE_ENDPOINT)
        client = SoftLayer.Client(username=user, api_key=key)
    return client


## READ CommandLine Arguments and load configuration file
parser = argparse.ArgumentParser(description="List powerstate for VirtualServers in Datacenter")
parser.add_argument("-u", "--username", help="SoftLayer API Username")
parser.add_argument("-k", "--apikey", help="SoftLayer APIKEY")
parser.add_argument("-c", "--config", help="config.ini file to load")
parser.add_argument("-d", "--datacenter", help="Filter by Datacenter")
parser.add_argument("-o", "--output", help="serverfile to create")
parser.add_argument("-i", "--image", help="TemplateImage name")
parser.add_argument("-v", "--vlan", help="VLAN")


args = parser.parse_args()

client = initializeSoftLayerAPI(args.username, args.apikey, args.config)

virtualServerFilter={'hourlyVirtualGuests': {'powerState': {'keyName': {'operation': 'HALTED'}}}}

if args.datacenter != None:
    virtualServerFilter['hourlyVirtualGuests'].update({'datacenter': {'name': {'operation': args.datacenter}}})
    datacenter=args.datacenter

if args.image != None:
    virtualServerFilter['hourlyVirtualGuests'].update({'blockDeviceTemplateGroup': {'name': {'operation': args.image}}})
    image = args.image

if args.vlan != None:
    virtualServerFilter['hourlyVirtualGuests'].update({'networkVlans': {'vlanNumber': {'operation': args.vlan}}})
    image = args.image


#print (json.dumps(virtualServerFilter,indent=4))
# CREATE API FILTER TO FILTER
central = pytz.timezone("US/Central")
virtualServers = client['Account'].getHourlyVirtualGuests(mask='id,hostname,createDate, powerState, datacenter.name,serverRoom,networkVlans,backendRouters,primaryBackendIpAddress, backendNetworkComponents,blockDeviceTemplateGroup',filter=virtualServerFilter)
#print (json.dumps(virtualServers,indent=4))
print ('{:<10} {:<20} {:<20} {:<10} {:<10} {:<20} {:<20} {:<10} {:<15} {:<20}'.format("ID", "Date", "Hostname", "State", "Datacenter", "ServerRoom", "Router", "Vlan", "IpAddress", "Templateimage"))
print ('{:<10} {:<20} {:<20} {:<10} {:<10} {:<20} {:<20} {:<10} {:<15} {:<20}'.format("==", "====", "========", "=====", "==========", "==========", "======", "====", "=========", "============="))

order=0
for server in virtualServers:
    order=order+1
    if 'blockDeviceTemplateGroup' in server:
        templateimage=server['blockDeviceTemplateGroup']['name']
    else:
        templateimage=""
    if "datacenter" in server:
        datacenter=server['datacenter']['name']
    else:
        datacenter=""

    if "powerState" in server:
        powerState=server['powerState']['keyName']
    else:
        powerState=""

    if "serverRoom" in server:
        serverRoom=server['serverRoom']['longName']
    else:
        serverRoom=""

    if "networkVlans" in server:
        vlan=server['networkVlans'][0]['vlanNumber']
    else:
        vlan=""

    if "backendRouters" in server:
        router=server['backendRouters'][0]['hostname']
    else:
        router=""

    if "primaryBackendIpAddress" in server:
        primaryBackendIpAddress=server['primaryBackendIpAddress']
    else:
        primaryBackendIpAddress=""

    if "createDate" in server:
        createDate=datetime.strftime(convert_timestamp(server['createDate']),"%Y-%m-%d %H:%M")
    else:
        createDate=""

    print("{:<10} {:<20} {:<20} {:<10} {:<10} {:<20} {:<20} {:<10} {:<15} {:<20}".format(server['id'], createDate, server['hostname'], powerState, datacenter, serverRoom, router, vlan, primaryBackendIpAddress, templateimage))
