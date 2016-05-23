__author__ = 'jonhall'
## Reload & PowerOff list of Virtual Servers


import SoftLayer, configparser, argparse, csv, json, pytz, logging,time
from datetime import datetime, timedelta, tzinfo

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
parser.add_argument("-l", "--list", help="List of GuestId's to rebuilt and PowerOff", nargs='*', required=True)


args = parser.parse_args()

client = initializeSoftLayerAPI(args.username, args.apikey, args.config)

## Configure Log
#logging.basicConfig(filename="powerOn.log", format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %I:%M:%S %p',level=logging.WARNING)
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %I:%M:%S %p',level=logging.WARNING)


## Add parameters to filter
if args.list != None:
    guestIdList = args.list
else:
    print ("List of guestID's required.")
    quit()


## STEPS
# 1. SoftLayer_Virtual_Guest::verifyReloadOperatingSystem to verify reload is possible
# 2. SoftLayer_Virtual_Guest::reloadCurrentOperatingSystemConfiguration
# 3. Monitor for complete by getting SoftLayer_Virtual_Guest::getActiveTransaction
# 4. SoftLayer_Virtual_Guest:PowerOffsoft if reload complete
poweredoff=0
reloaded=0

# Verify and reload VSIs
for guestId in guestIdList:
     # Verify guestId can be reloaded.
     logging.warning("Verifying reload possible for guestId %s" % (guestId))
     try:
         verifyReloadOperatingSystem = client['Virtual_Guest'].verifyReloadOperatingSystem(id=guestId)
     except SoftLayer.SoftLayerAPIError as e:
         logging.warning("Virtual_Guest::verifyReloadOperatingSystem(id=%s): %s" % (guestId, e.faultString))
         verifyReloadOperatingSystem = False

     # If verified, start reload process using current configuration including templateImage
     if verifyReloadOperatingSystem == True:
         logging.warning("Succesfully verified guestId %s" % (guestId))
         logging.warning("Issuing Reload command for guestId %s" % (guestId))
         try:
            reloadCurrentOperatingSystem = client['Virtual_Guest'].reloadCurrentOperatingSystemConfiguration(id=guestId)
         except SoftLayer.SoftLayerAPIError as e:
            logging.warning("Virtual_Guest::reloadCurrentOperatingSystemConfiguration(id=%s): %s" % (guestId, e.faultString))
         else:
            logging.warning("Reload of guestId %s started at %s" % (guestId, reloadCurrentOperatingSystem['modifyDate']))
     else:
         logging.warning("Reload not possible for GuestId %s." % (guestId))
         guestIdList.remove(guestId)



# Monitor for reload complete % poweroff
while len(guestIdList)>0:
    time.sleep(60)
    for guestId in guestIdList:
        logging.warning("Checking status of active transaction for guestId %s" % (guestId))

        # Get activeTransaction to see if reload in progress.
        try:
            activeTransaction = client['Virtual_Guest'].getActiveTransaction(id=guestId)
        except SoftLayer.SoftLayerAPIError as e:
            logging.warning("Virtual_Guest::getActiveTransaction(id=%s): %s" % (guestId, e.faultString))
            activeTransaction=""
            continue

        # If no active Transaction, Power Off VSI to leave in HALTED status for next use.  Remove guestID from list
        if activeTransaction =="":
            logging.warning("Reload complete, Powering off guestId %s" % (guestId))
            try:
                poweroff = client['Virtual_Guest'].powerOffsoft(id=guestId)
            except SoftLayer.SoftLayerAPIError as e:
                logging.warning("Virtual_Guest::powerOffsoft(id=%s): %s" % (guestId, e.faultString))
                continue
            else:
                guestIdList.remove(guestId)
                poweredoff=poweredoff+1
        else:
            # Reload still in progress, log transacation detail.
            logging.warning("Current transaction is %s, elapsed time %s for guestId %s." % (activeTransaction['transactionStatus']['name'],activeTransaction['elapsedSeconds'], guestId))

## All requested servers have been powered off.
logging.warning("All servers have been reloaded and powered off.")

