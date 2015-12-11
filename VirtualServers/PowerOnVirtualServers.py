__author__ = 'jonhall'
## POWERON VIRtUALGUESTS

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
        client = SoftLayer.Client(username=config['api']['username'], api_key=config['api']['apikey'],endpoint_url=SoftLayer.API_PRIVATE_ENDPOINT)
    else:
        #client = SoftLayer.Client(username=config['api']['username'], api_key=config['api']['apikey'],endpoint_url=SoftLayer.API_PRIVATE_ENDPOINT)
        client = SoftLayer.Client(username=user, api_key=key)
    return client


## READ CommandLine Arguments and load configuration file
parser = argparse.ArgumentParser(description="PowerOnVirtualServers given a list of hostnames.")
parser.add_argument("-u", "--username", help="SoftLayer API Username")
parser.add_argument("-k", "--apikey", help="SoftLayer APIKEY")
parser.add_argument("-c", "--config", help="config.ini file to load")
parser.add_argument("-i", "--input", help="List of Servers")

args = parser.parse_args()

client = initializeSoftLayerAPI(args.username, args.apikey, args.config)

if args.input == None:
    filename=input("Filename of servers: ")
else:
    filename=args.input

## READ CSV FILE INTO PYTHON DICTIONARY
## FIELDS REQUIRED: ID, HOSTNAME, WAIT
## ID = VM ID (found via SLCLI VS LIST) Leave empty to have script lookup by hostname
## HOSTNAME = SL Hostname (must be unique if you don't specify VM ID)
## WAIT = # of second to wait after powering on VM before moving to next VM
## Example csv file
## Order,id,hostname,wait
## 1,13405579,  centos02 ,60
## 2,13405577,  centos01 ,30
## 3,13405581,  centos03 ,30

## READ ACCOUNT LIST OF VIRTUAL GUESTS IN CASE ID ISN'T SPECIFIED
try:
    virtualGuests = client['Account'].getVirtualGuests(mask="id,hostname,powerState.keyName")
except SoftLayer.SoftLayerAPIError as e:
    print("Error: %s, %s" % (e.faultCode, e.faultString))

## OPEN CSV FILE TO READ LIST OF SERVERS
with open(filename, 'r') as csvfile:
    serverlist = csv.DictReader(csvfile, delimiter=',', quotechar='"')
    for server in serverlist:
        # IF ID isn't specified lookup hostname
        print (server['id'])
        if server['id']=="":
            #Lookup ID
            for virtualGuest in virtualGuests:
                if server['hostname']==virtualGuest['hostname']:
                    vsiid=virtualGuest['id']
        else:
            vsiid=server['id']

        ## POWER ON SERVERS IN ORDER OF CSV FILE
        print ("Powering on server %s (%s)" % (server['hostname'],vsiid))

        try:
            poweron = client['Virtual_Guest'].powerOn(id=vsiid)
        except SoftLayer.SoftLayerAPIError as e:
            print("Error: %s, %s" % (e.faultCode, e.faultString))

        ## WAIT FOR PERIOD SPECIFIED BEFORE NEXT VM
        print ("Sleeping for %s seconds" % server['wait'])
        time.sleep(float(server['wait']))


