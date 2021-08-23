import SoftLayer, json, configparser, os, argparse, csv
from datetime import datetime, timedelta, tzinfo
import pytz


def initializeSoftLayerAPI():
    ## READ CommandLine Arguments and load configuration file
    parser = argparse.ArgumentParser(description="Check Audit Log for VSI.")
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


filename=input("Filename of servers: ")
#filename="servers.csv"
outputname=input("Output filename: ")
#outputname="output.csv"
fieldnames = ['ID', 'Hostname', 'Create date', 'Power on date', 'Power on delta', 'Provision date', "Provision delta"]

outfile = open(outputname, 'w')
csvwriter = csv.DictWriter(outfile, delimiter=',', fieldnames=fieldnames)
csvwriter.writerow(dict((fn, fn) for fn in fieldnames))
## OPEN CSV FILE TO READ LIST OF SERVERS


with open(filename, 'r') as csvfile:
    serverlist = csv.DictReader(csvfile, delimiter=',', quotechar='"')
    for server in serverlist:
        if server["Made Miss"]=="Miss":
            instance_id = server['ID']
            events = client['Event_Log'].getAllObjects(filter={'objectId': {'operation': instance_id},
                                        'eventName': {'operation': 'Power On'}})
            eventdate = datetime.now(pytz.UTC)
            powerOnDate = datetime.now(pytz.UTC)
            found=0
            for event in events:
                if event['eventName']=="Power On":
                    eventdate = event["eventCreateDate"]
                    eventdate = eventdate[0:29]+eventdate[-2:]
                    eventdate = datetime.strptime(eventdate, "%Y-%m-%dT%H:%M:%S.%f%z")

                    if eventdate<powerOnDate:
                        powerOnDate = eventdate
                        found=1
            if found==1:
                createDate = server['Create date']
                createDate = createDate[0:22]+createDate[-2:]
                createDate = datetime.strptime(createDate, "%Y-%m-%dT%H:%M:%S%z")

                provisionDate = server['Provision date']
                provisionDate = provisionDate[0:22]+provisionDate[-2:]
                provisionDate = datetime.strptime(provisionDate, "%Y-%m-%dT%H:%M:%S%z")


                #powerOnDate = timezone(powerOnDate, timezone('America/Chicago'))
                #print (powerOnDate)
                row = {'ID': server['ID'],
                   'Hostname': server['Hostname'],
                   'Create date': datetime.strftime(createDate,"%Y-%m-%dT%H:%M:%S%z"),
                   'Power on date': datetime.strftime(powerOnDate,"%Y-%m-%dT%H:%M:%S%z"),
                   'Power on delta': str(powerOnDate-createDate),
                   'Provision date': datetime.strftime(provisionDate,"%Y-%m-%dT%H:%M:%S%z"),
                   'Provision delta': str(provisionDate-createDate)
                   }
                print (json.dumps(row,indent=4))
                csvwriter.writerow(row)
            else:
                row = {'ID': server['ID'],
                   'Hostname': server['Hostname'],
                   'Create date': datetime.strftime(createDate,"%Y-%m-%dT%H:%M:%S%z"),
                   'Power on date': 'Not Available',
                   'Power on delta': 'Not Available',
                   'Provision date': datetime.strftime(provisionDate,"%Y-%m-%dT%H:%M:%S%z"),
                   'Provision delta': str(provisionDate-createDate)
                   }
                print (json.dumps(row,indent=4))
                csvwriter.writerow(row)
