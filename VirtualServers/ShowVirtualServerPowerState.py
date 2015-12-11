__author__ = 'jonhall'
## List powerstate for VirtualServers in Datacenter

import sys, getopt, socket, SoftLayer, json, string, configparser, os, argparse,csv, time
import pandas as pd

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

args = parser.parse_args()

client = initializeSoftLayerAPI(args.username, args.apikey, args.config)

if args.datacenter == None:
    datacenter=input("Datacenter: ")
else:
    datacenter=args.datacenter


virtualServers = client['Account'].getVirtualGuests(mask='id,hostname,datacenter.name,powerState',
                                filter={'virtualGuests': {'datacenter': {'name': {'operation': datacenter}}}})

print ('{:<10} {:<20} {:<15}'.format("ID", "Hostname", "PowerState"))
print ('{:<10} {:<20} {:<15}'.format("==========", "================", "================="))

for server in virtualServers:
    print("{:<10} {:<20} {:<15}".format(server['id'], server['hostname'], server['powerState']['name']))


