__author__ = 'jonhall'
#
## Get Current Invoices
## Place APIKEY & Username in config.ini
## or pass via commandline  (example: GetNewInvoices.py -u=userid -k=apikey)
##

import sys, getopt, socket, SoftLayer, json, string, configparser, os, argparse

def initializeSoftLayerAPI():
    ## READ CommandLine Arguments and load configuration file
    parser = argparse.ArgumentParser(description="Show powerstate of Virtual Servers.")
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

datacenter = input ("Datacenter? ")

virtualServers = client['Account'].getVirtualGuests(mask='id,hostname,datacenter.name,powerState',
                                filter={'virtualGuests': {'datacenter': {'name': {'operation': datacenter}}}})

print ('{:<10} {:<20} {:<15}'.format("ID", "Hostname", "PowerState"))
print ('{:<10} {:<20} {:<15}'.format("==========", "================", "================="))

for server in virtualServers:
    print("{:<10} {:<20} {:<15}".format(server['id'], server['hostname'], server['powerState']['name']))


