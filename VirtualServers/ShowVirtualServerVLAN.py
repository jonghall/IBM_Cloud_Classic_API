__author__ = 'jonhall'
## List powerstate for VirtualServers in Datacenter

import SoftLayer,  configparser,  argparse


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
parser = argparse.ArgumentParser(description="List BCR and VLANs of VirtualServers in Datacenter")
parser.add_argument("-u", "--username", help="SoftLayer API Username")
parser.add_argument("-k", "--apikey", help="SoftLayer APIKEY")
parser.add_argument("-c", "--config", help="config.ini file to load")
parser.add_argument("-d", "--datacenter", help="Filter by Datacenter")

args = parser.parse_args()

client = initializeSoftLayerAPI(args.username, args.apikey, args.config)

if args.datacenter == None:
    datacenter=input("Datacenter: ")
else:
    datacenter=args.datacenter


virtualServers = client['Account'].getVirtualGuests(mask='id,fullyQualifiedDomainName,datacenter.name,backendRouters.hostname,networkVlanCount,networkVlans',
                                filter={'virtualGuests': {'datacenter': {'name': {'operation': datacenter}}}})

print ('{:<10} {:<40} {:<15} {:<10}'.format("ID        ", "fullyQualifiedDomainName", "BCR","VLAN"))
print ('{:<10} {:<40} {:<15} {:<10}'.format("==========", "========================", "===","===="))

for server in virtualServers:
    # Determine Index based on whether private only interface
    if server['networkVlanCount'] > 1:
        vlanIndex=1
    else:
        vlanIndex=0
    print("{:<10} {:<40} {:<15} {:<10}".format(server['id'], server['fullyQualifiedDomainName'], server['backendRouters'][0]['hostname'],server['networkVlans'][vlanIndex]['vlanNumber']))


