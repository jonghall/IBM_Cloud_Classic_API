__author__ = 'jonhall'
#
## Get Current Invoices
## Place APIKEY & Username in config.ini
## or pass via commandline  (example: PowerOnVirtualServers.py -u=userid -k=apikey)
##

import sys, getopt, socket, SoftLayer, json, string, configparser, os, argparse, csv, time


def initializeSoftLayerAPI():
    ## READ CommandLine Arguments and load configuration file
    parser = argparse.ArgumentParser(description="Power-on Virtual Servers.")
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

## READ CSV FILE INTO PYTHON DICTIONARY
## FIELDS REQUIRED: ID, HOSTNAME, WAIT
## ID = VM ID (found via SLCLI VS LIST)
## HOSTNAME = SL Hostname (used for display only)
## WAIT = # of second to wait after powering on VM before moving to next VM
## Example csv file
## Order,id,hostname,wait
## 1,13405579,  centos02 ,60
## 2,13405577,  centos01 ,30
## 3,13405581,  centos03 ,30


filename=input("Filename of servers: ")

## OPEN CSV FILE TO READ LIST OF SERVERS
with open(filename, 'r') as csvfile:
    serverlist = csv.DictReader(csvfile, delimiter=',', quotechar='"')
    for server in serverlist:
        print ("Powering on server %s (%s)" % (server['hostname'], server['id']))
        ## POWER ON VSI's IN ORDER OF CSV
        try:
            poweroff = client['Virtual_Guest'].powerOn(id=server['id'])
        except SoftLayer.SoftLayerAPIError as e:
                print("Error: %s, %s" % (e.faultCode, e.faultString))
        ## SLEEP FOR WAIT PERIOD SPECIFIED
        print ("Sleeping for %s seconds" % server['wait'])
        time.sleep(float(server['wait']))

