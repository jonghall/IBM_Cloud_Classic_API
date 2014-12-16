import sys, getopt, socket, SoftLayer, json, string, configparser, os, argparse
def initializeSoftLayerAPI():
    ## READ CommandLine Arguments and load configuration file
    parser = argparse.ArgumentParser(description="DeprovisionBM requests permision to submit deprovision requests for Bare Metal Servers")
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


client = initializeSoftLayerAPI()

########################################################
## GET HARDWARE                                        #
########################################################
hardwarelist = client['Account'].getHardware()

for child in hardwarelist:
    hwid=child['id']
    object_mask="provisionDate,hardwareStatusId,fullyQualifiedDomainName,bareMetalInstanceFlag"
    hguest = client['Hardware_Server'].getObject(mask=object_mask, id=hwid)
    ## VERIFY BareMetalInstance and not already being reclaimed
    if hguest['bareMetalInstanceFlag'] and hguest['hardwareStatusId'] != 8:
        ########################################################
        ## CANCEL BARE METAL INSTANCES OLDER THAN CUTOFF       #
        ########################################################
        prompt = input("Would you like to submit a deprovision request for Hourly BM Server %s [Y/N]?" % hguest['fullyQualifiedDomainName'])
        if prompt == "Y" or prompt == "y":
            print ("Deprovisioning Hourly Bare Metal Server %s. " % (hguest['fullyQualifiedDomainName']))
            try:
                delete = client['Hardware_Server'].deleteObject(id=hwid)
            except SoftLayer.SoftLayerAPIError as e:
                print("Error: %s, %s"
                      % (e.faultCode, e.faultString))
    else:
        ########################################################
        ## CANCEL ALL DEDICATED SERVERS BY OPENING TICKET      #
        ########################################################
        prompt = input("Would you like to submit a deprovision request for Monthly BM Server %s [Y/N]?" % hguest['fullyQualifiedDomainName'])
        if prompt == "Y" or prompt == "y":
            print ("Submitting request to cancel Monthly Bare Metal Server immedietly.  Dedicated Server %s." % (hguest['fullyQualifiedDomainName']))
            cancel_reason="No longer needed"
            comment="Demo Complete, please deprovision and reclaim immedietly"
            id=hwid
            try:
                cancel=client['Ticket'].createCancelServerTicket(id1, cancel_reason,comment, True, 'HARDWARE')
            except SoftLayer.SoftLayerAPIError as e:
                print("%s"
                      % (e.faultString))