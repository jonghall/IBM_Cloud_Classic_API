__author__ = 'jonhall'
#
## Get iSCSI Allocations
## Place APIKEY & Username in config.ini
## or pass via commandline  (example: GetiSCSIAllocations.py -u=userid -k=apikey)

import SoftLayer, configparser, argparse, logging

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

logging.warning("Retreiving all current iSCSI storage allocations.")

# get list of iSCSI Allocations in Account
try:
    volumes = client['Account'].getIscsiNetworkStorage(mask="id,username,capacityGb,nasType,snapshots,snapshots.snapshotCreationTimestamp,snapshots.snapshotSizeBytes,snapshots.creationScheduleId,schedules,schedules.retentionCount," \
                                "billingItem.description,serviceResource,serviceResource.datacenter,serviceResourceName,serviceResourceBackendIpAddress,totalBytesUsed")
except SoftLayer.SoftLayerAPIError as e:
    logging.warning("Account:getNetworkStorage: %s, %s" % ( e.faultCode, e.faultString))
    quit()

for volume in volumes:
    schedules=volume['schedules']
    snapshots=volume['snapshots']
    print ("{:<10}{:<20}{:<20}{:<20}{:<20}{:<20}".format("StorageId", "LUN Name","Type", "Target", "Capacity", "Location"))
    print ("{:<10}{:<20}{:<20}{:<20}{:<20}{:<20}".format(volume['id'],volume['username'], volume['billingItem']['description'], volume['serviceResourceBackendIpAddress'], volume['capacityGb'], volume['serviceResource']['datacenter']['name']))

    ## PRINT Schedules
    print()
    print("Schedules")
    print("{:<15}{:<30}{:<10}".format("ScheduleId", "Schedule", "Retention"))
    for schedule in schedules:
        print("{:<15}{:<30}{:<10}".format(schedule['id'], schedule['name'],schedule['retentionCount']))

    ## PRINT Snapshot stats
    print()
    print("Snapshots")
    print("{:<15}{:<20}{:<30}{:<20}{:<20}".format("SnapshotId", "Schedule", "Name", "Size", "Created"))
    for snap in snapshots:
        if 'notes' in snap:
            notes=snap['notes']
        else:
            notes=''
        if 'creationScheduleId' in snap:
            creationScheduleId=snap['creationScheduleId']
        else:
            creationScheduleId="Manual"
        print("{:<15}{:<20}{:<30}{:<20}{:<20}".format(snap['id'], creationScheduleId, notes, snap['snapshotSizeBytes'],snap['createDate'][:10]))



