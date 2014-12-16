import sys, getopt, socket, SoftLayer, json, string, configparser, os, argparse


def initializeSoftLayerAPI():
    ## READ CommandLine Arguments and load configuration file
    parser = argparse.ArgumentParser(description="DeprovisionCCI requests permision to submit deprovision requests for CCIs")
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

result = client['Account'].getVirtualGuests()

for child in result:
    vmid=child['id']
    vguest = client['Virtual_Guest'].getObject(id=vmid)
    prompt = input("Would you like to submit deprovisiokn request for %s [Y/N]?" % vguest['fullyQualifiedDomainName'])
    if (prompt == "Y" or prompt == "y"):
        print ("Deprovisioning CCI %s." % (vguest['fullyQualifiedDomainName']))
        try:
            delete = client['Virtual_Guest'].deleteObject(id=vmid)
        except SoftLayer.SoftLayerAPIError as e:
            print("Error: %s, %s"
                  % (e.faultCode, e.faultString))

