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


##############################
# OPEN SOFTLAYER TICKET
##############################

title = "Ticket Subject/Title goes Here"
content = "Ticket Content Goes Here"

# SubjectId's can be returned by calling SoftLayer_Ticket_Subject service.
subjectId = 1021 # hardware issue

SoftLayerTicket =  {
    'subjectId': subjectId,
    'title': title,
    }

try:
    ticket = client['Ticket'].createStandardTicket(SoftLayerTicket, content)
    ticketId = ticket['firstUpdate']['ticketId']
    logging.warning("Ticket ID %s for Guest %s created." % (ticketId, guestId))

except SoftLayer.SoftLayerAPIError as e:
    ticket = e.faultCode
    ticketId = 0
    logging.warning("Ticket:createStandardTicket(): %s, %s" % (e.faultCode, e.faultString))


##############################################################
# ASSOCIATE VIRTUAL GUEST WITH TICKET
# Use addAttachedHardware method to associate hardware instead
##############################################################
if ticketId != 0:
    try:
        attachedVirtualGuest = client['Ticket'].addAttachedVirtualGuest(guestId, id=ticketId)
        logging.warning("Associated ticket guest % with ticket %s." % (guestId, ticketId))
    except SoftLayer.SoftLayerAPIError as e:
        ticket = e.faultCode
        logging.warning("Ticket:addAttachedVirtualGuest: %s, %s" % (e.faultCode, e.faultString))



