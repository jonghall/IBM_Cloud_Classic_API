## LOOKUP USER INFO

import SoftLayer, random, string, sys, json, os, configparser, argparse, csv
from itertools import chain


def initializeSoftLayerAPI():
    ## READ CommandLine Arguments and load configuration file
    parser = argparse.ArgumentParser(description="The script is used to place an order using a saved quote.")
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


## Get list of all Open Tickets
result = client['Account'].getOpenTickets()
print ('=======================================')

## iterate through tickets and write ticket info to CSV file
for ticket in result:
    id = ticket['id']
    title = ticket['title']
    createDate = ticket['createDate']
    modifyDate = ticket['modifyDate']
    assigneduserId = ticket['assignedUserId']
    user = client['User_Customer'].getObject(id=assigneduserId)
    username = user['username']
    priority = ticket['priority']
    status = ticket['status']['name']
    print ('id:', id)
    print ('create:', createDate)
    print ('Title:', title)
    print ('User:', username)
    print ('Priority:', priority)
    print ('Status:', status)
    print ('=======================================')
    print

