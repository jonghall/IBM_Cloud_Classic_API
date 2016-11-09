__author__ = 'jonhall'
#
## Get NAS & ISCSI Allocations
## Place APIKEY & Username in config.ini
## or pass via commandline  (example: GetiSCSIAllocations.py -u=userid -k=apikey)

import SoftLayer, configparser, argparse, logging, json

def initializeSoftLayerAPI(user, key, configfile):
    if user == None and key == None:
        if configfile != None:
            filename=args.config
        else:
            filename="config.ini"
        config = configparser.ConfigParser()
        config.read(filename)
        client = SoftLayer.Client(username=config['api']['username'], api_key=config['api']['apikey'],timeout=240)
    else:
        client = SoftLayer.Client(username=user, api_key=key,timeout=120)
    return client


## READ CommandLine Arguments and load configuration file
parser = argparse.ArgumentParser(description="Report of iSCSI allocations.")
parser.add_argument("-u", "--username", help="SoftLayer API Username")
parser.add_argument("-k", "--apikey", help="SoftLayer APIKEY")
parser.add_argument("-c", "--config", help="config.ini file to load")

args = parser.parse_args()

client = initializeSoftLayerAPI(args.username, args.apikey, args.config)

## Setup Logging
logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %I:%M:%S %p',level=logging.WARNING)

logging.warning("Retreiving all current NAS storage allocations.")

# get list of iSCSI Allocations in Account
try:
    volumes = client['Account'].getNetworkStorage(mask="id,username,capacityGb,nasType,serviceResource,billingItemCategory," \
            "serviceResource.datacenter,serviceResourceBackendIpAddress,bytesUsed,totalBytesUsed,storageType,storageTierLevel",
            filter={
                'networkStorage': {
                        'nasType': {
                            'operation': 'in',
                            'options': [
                                {'name': 'data',
                                 'value': [
                                     'NAS',
                                     'ISCSI']}
                            ]}}})
except SoftLayer.SoftLayerAPIError as e:
    logging.warning("Account:getNetworkStorage: %s, %s" % ( e.faultCode, e.faultString))
    quit()

print ("=======================================================================================================================")

for volume in volumes:
    # If Endurance storage check if Snapshots or Schedules Exist
    if volume['billingItemCategory']['categoryCode'] == "storage_service_enterprise":
        try:
            schedules=client['Network_Storage'].getSchedules(id=volume['id'], mask="id,name,retentionCount")
        except SoftLayer.SoftLayerAPIError as e:
            logging.warning("Network_Storage::getSchedules: %s, %s" % (e.faultCode, e.faultString))
            quit()

        try:
            snapshots=client['Network_Storage'].getSnapshots(id=volume['id'], mask="id, creationScheduleId, notes, snapshotSizeBytes,createDate")
        except SoftLayer.SoftLayerAPIError as e:
            logging.warning("Network_Storage::getSnapshots: %s, %s" % (e.faultCode, e.faultString))
            quit()
    else:
        schedules=[]
        snapshots=[]

    if 'bytesUsed' in volume:
        bytes=float(volume['bytesUsed'])
    elif 'totalBytesUsed' in volume:
        bytes=float(volume['totalBytesUsed'])
    else:
        bytes=0
    usedGb = "{:6,.2f}".format(bytes/1024/1024/1024)

    if 'storageTierLevel' in volume:
        storageType=volume['storageType']['description']+" "+volume['storageTierLevel']['description']
    else:
        storageType=volume['storageType']['description']
    print()
    print ("{:<10}{:<20}{:<45}{:<40}{:<15}{:<12}{:<12}".format("StorageId", "LUN Name","Type", "Target", "CapacityGb", "UsedGb", "Location"))
    print ("{:<10}{:<20}{:<45}{:<40}{:<15}{:<12}{:<12}".format(volume['id'],volume['username'], storageType[:44], volume['serviceResourceBackendIpAddress'][:39], volume['capacityGb'],usedGb, volume['serviceResource']['datacenter']['name']))

    ## PRINT Schedules
    if len(schedules) > 0:
        print()
        print("     Schedules")
        print("     ---------")
        print("     {:<15}{:<30}{:<10}".format("ScheduleId", "Schedule", "Retention"))
        for schedule in schedules:
            print("     {:<15}{:<30}{:<10}".format(schedule['id'], schedule['name'],schedule['retentionCount']))
    else:
        print ()
        print ("No Schedules")
    ## PRINT Snapshot stats
    if len(snapshots) > 0:
        print()
        print("     Snapshots")
        print("     ---------")
        print("     {:<15}{:<30}{:<40}{:<10}{:<20}".format("SnapshotId", "Schedule", "Name", "Size", "Created"))
        for snap in snapshots:
            if 'notes' in snap:
                notes=snap['notes']
            else:
                notes=''
            if 'creationScheduleId' in snap:
                creationScheduleId=snap['creationScheduleId']
            else:
                creationScheduleId="Manual"
            print("     {:<15}{:<30}{:<40}{:<10}{:<20}".format(snap['id'], creationScheduleId, notes[0:39], snap['snapshotSizeBytes'],snap['createDate'][:10]))
    else:
        print()
        print("No Snapshots")
    print()
    print ("=======================================================================================================================")

