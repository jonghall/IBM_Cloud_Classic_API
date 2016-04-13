##
## Check status of VSI provisioning jobs & send alert message if outside of normal parameters
##

import SoftLayer, json, configparser, argparse, logging,sendgrid, pytz
from datetime import datetime

def convert_timedelta(duration):
    days, seconds = duration.days, duration.seconds
    hours = days * 24 + seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    totalminutes = round((days * 1440) + (hours * 60) + minutes + (seconds / 60), 1)
    return totalminutes

def convert_timestamp(sldate):
    formatedDate = sldate
    formatedDate = formatedDate[0:22]+formatedDate[23:26]
    formatedDate = datetime.strptime(formatedDate, "%Y-%m-%dT%H:%M:%S%z")
    return formatedDate.astimezone(central)

def getDescription(categoryCode, detail):
    for item in detail:
        if item['categoryCode'] == categoryCode:
            return item['description']
    return "Not Found"

def initializeSoftLayerAPI(user, key, configfile):
    global client
    if user == None and key == None:
        if configfile != None:
            filename = args.config
        else:
            filename = "config.ini"
        config = configparser.ConfigParser()
        config.read(filename)
        #client = SoftLayer.Client(username=config['api']['username'], api_key=config['api']['apikey'], endpoint_url=SoftLayer.API_PRIVATE_ENDPOINT)
        client = SoftLayer.Client(username=config['api']['username'], api_key=config['api']['apikey'])
    else:
        client = SoftLayer.Client(username=user, api_key=key)
    return client


## READ CommandLine Arguments and load configuration file
parser = argparse.ArgumentParser(description="Check Audit Log for VSI.")
parser.add_argument("-u", "--username", help="SoftLayer API Username")
parser.add_argument("-k", "--apikey", help="SoftLayer APIKEY")
parser.add_argument("-c", "--config", help="config.ini file to load")
args = parser.parse_args()

central = pytz.timezone("US/Central")

if args.config != None:
    filename = args.config
else:
    filename = "config.ini"

config = configparser.ConfigParser()
config.read(filename)

## Get SendGrid parameters from config.ini
sendgridKey = config["sendgrid"]["sendgridKey"]
distributionList = config["sendgrid"]["distributionList"]
fromEmail = config["sendgrid"]["fromEmail"]
subject = config["sendgrid"]["subject"]

logging.basicConfig(filename='events.log', format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %I:%M:%S %p',level=logging.WARNING)

client = initializeSoftLayerAPI(args.username, args.apikey, args.config)

try:
    virtualGuests = client['Account'].getVirtualGuests(
        mask='id, provisionDate, hostname, lastTransaction, activeTransaction, dedicatedAccountHostOnlyFlag, activeTransactions,datacenter, datacenter.name,serverRoom, primaryBackendIpAddress, networkVlans, backendRouters,blockDeviceTemplateGroup',
        filter={
            'virtualGuests': {
                'provisionDate': {'operation': 'is null'}
            }
        })

except SoftLayer.SoftLayerAPIError as e:
    logging.warning("Account::getHourlyVirtualGuests(): %s, %s" % (e.faultCode, e.faultString))
    quit()

logging.warning('Found %s VirtualGuests being provisioned.' % (len(virtualGuests)))


countVirtualGuestslt30 = 0
countVirtualGuestsgt30 = 0
countVirtualGuestsgt60 = 0
countVirtualGuestsgt120 = 0
ontrack = 0
critical = 0
watching = 0
stalled = 0

# READ PREVIOUS DATA FOR ALERTING
try:
    stats = json.loads(open('stats.json').read())
except:
    stats = {"virtualGuests": 0,
         "ontrack": 0,
         "watching": 0,
         "critical": 0,
         "stalled": 0}


emailbody = (
    '<table width="100%"><tr><th>guestId</th><th>hostName</th><th>TemplateImage</th><th>BCR</th><th>Vlan</th><th>createDate</th><th>ElapsedTime</th><th>transaction</th><th>AvgDuration</th><th>Duration</th><th>Status</th></tr>')
for virtualGuest in virtualGuests:
    Id = virtualGuest['id']
    numTransactions=len(virtualGuest['activeTransactions'])
    guestId = virtualGuest['activeTransaction']['guestId']

    # GET TIME STAMP FOR REQUEST FROM OLDEST ACTIVE TRANSACTION
    createDate = virtualGuest['activeTransactions'][numTransactions-1]['createDate']
    createDateStamp = convert_timestamp(createDate)
    currentDateStamp = central.localize(datetime.now())
    delta = convert_timedelta(currentDateStamp - createDateStamp)
    hostName = virtualGuest['hostname']

    # Whcih Template Image is being used if any.
    if 'blockDeviceTemplateGroup' in virtualGuest:
        templateImage=virtualGuest['blockDeviceTemplateGroup']['name']
    else:
        templateImage="none"

    # if the VSI is a privateVSI (True) or public VSI (False)
    if 'dedicatedAccountHostOnlyFlag' in virtualGuest:
        dedicatedAccountHostOnlyFlag = virtualGuest['dedicatedAccountHostOnlyFlag']
    else:
        dedicatedAccountHostOnlyFlag = False

    # VLAN information
    if "networkVlans" in virtualGuest:
        vlan=virtualGuest['networkVlans'][0]['vlanNumber']
    else:
        vlan=""

    # Backend Router
    if "backendRouters" in virtualGuest:
        if len(virtualGuest['backendRouters']) > 1:
            router=virtualGuest['backendRouters'][0]['hostname']
        else:
            router = virtualGuest['backendRouters']['hostname']
    else:
        router=""

    # Which Datacenter
    if "datacenter" in virtualGuest:
        datacenter=virtualGuest['datacenter']['name']
    else:
        datacenter=""

    # Which Server Room
    if "serverRoom" in virtualGuest:
        serverRoom=virtualGuest['serverRoom']['longName']
    else:
        serverRoom=""

    # Backend IP address assigned
    if "primaryBackendIpAddress" in virtualGuest:
        primaryBackendIpAddress=virtualGuest['primaryBackendIpAddress']
    else:
        primaryBackendIpAddress=""

    # Look at active transaction to get stats on current status of provisioning job
    transactionStatus = virtualGuest['activeTransaction']['transactionStatus']['name']
    statusDuration = round(virtualGuest['activeTransaction']['elapsedSeconds']/60,1)
    if 'averageDuration' in virtualGuest['activeTransaction']['transactionStatus']:
        averageDuration=virtualGuest['activeTransaction']['transactionStatus']['averageDuration']
    else:
        averageDuration=1

    status = "unknown"

    # IF DURATION PROGRESSING < 45 THEN ON TRACK
    if (delta) < 45:
        status = "ONTRACK"
        ontrack = ontrack + 1
    # IF DURATION BETWEEN 45 & 75 & PROGRESSING < 45 THEN ON AT RISK
    if (delta >= 45) and (delta < 75):
        status = "ATRISK"
        watching = watching + 1
    # IF DURATION > 75 & PROGRESSING THEN ON TRACK MARK AS CRITICAL ONLY
    if (delta) >= 75 and (statusDuration < 15):
        status = "CRITICAL"
        critical = critical + 1
    # IF DURATION > 75 & NOT PROGRESSING THEN MARK STALLED.
    if (delta) >= 60 and (statusDuration >= 15):
        status = "STALLED"
        stalled = stalled + 1

    logging.warning('%s using %s image behind %s on vlan %s is %s. (delta=%s, average=%s, duration=%s, request=%s).' % (guestId,templateImage,router, vlan, status,delta,averageDuration,statusDuration,datetime.strftime(createDateStamp, "%H:%M:%S%z")))

    # BUILD ROWS OF TABLE FOR EXCEPTION JOBS.
    if status=="CRITICAL" or status=="STALLED":
        if statusDuration>(10*float(averageDuration)):
            emailbody=emailbody+(
            '<tr><td style="text-align: center;"><a href="https://internal.softlayer.com/HardwareTransaction/automatedManagement/cloudlayer/%s">%s</a></td><td style="text-align: center;">%s</td><td style="text-align: center;">%s</td>'
            '<td style="text-align: center;">%s</td><td style="text-align: center;">%s</td><td style="text-align: center;">%s</td><td style="text-align: center;background-color:#FF0000">%s</td><td style="text-align: center;">'
            '%s</td><td style="text-align: center;">%s</td><td style="text-align: center;background-color:#FF0000">%s</td><td style="text-align: center;">%s</td></tr>' % (
            guestId, guestId, hostName, templateImage, router, vlan, str(createDateStamp), delta,transactionStatus, averageDuration, statusDuration, status))
        else:
            emailbody=emailbody+('<tr><td style="text-align: center;"><a href="https://internal.softlayer.com/HardwareTransaction/automatedManagement/cloudlayer/%s">%s</a></td><td style="text-align: center;">%s</td><td style="text-align: center;">%s</td>'
            '<td style="text-align: center;">%s</td><td style="text-align: center;">%s</td><td style="text-align: center;">%s</td><td style="text-align: center;background-color:#FF0000">%s</td><td style="text-align: center;">'
            '%s</td><td style="text-align: center;">%s</td><td style="text-align: center;">%s</td><td style="text-align: center;">%s</td></tr>' % (
            guestId, guestId, hostName, templateImage, router, vlan, str(createDateStamp), delta,transactionStatus, averageDuration, statusDuration, status))


    if delta < 30:
        countVirtualGuestslt30 = countVirtualGuestslt30 + 1
    if delta >= 30 and delta < 60:
        countVirtualGuestsgt30 = countVirtualGuestsgt30 + 1
    if delta >= 60 and delta < 120:
        countVirtualGuestsgt60 = countVirtualGuestsgt60 + 1
    if delta >= 120:
        countVirtualGuestsgt120 = countVirtualGuestsgt120 + 1


## IF CRITICAL OR STALLED JOBS INCREASE SEND EMAIL ALERT WITH TABLE
if (critical + stalled > stats['critical'] + stats['stalled']) or (stalled > stats['stalled']):
    logging.warning('Sending email alert: %s critical requests, a change from %s. %s stalled requests, a change from %s.' % (
                   critical, stats['critical'], stalled, stats['stalled']))

    sg = sendgrid.SendGridClient(sendgridKey)
    message = sendgrid.Mail()
    message.add_to(distributionList)
    message.set_subject(subject)
    body = (
               '<p<b>%s total provisioning requests.<br>%s critical requests, a change from %s.<br>%s stalled requests, a change from %s. <br></b> View current requests at <a href="http://provisionstatus.mybluemix.net">http://provisionstatus.mybluemix.net</a></p><br><br><b>Exception Requests</b> <br>' % (
                   len(virtualGuests), critical, stats['critical'], stalled, stats['stalled'])) + emailbody + "</tr></table>"
    message.set_html(body)
    message.set_from(fromEmail)
    status, msg = sg.send(message)


logging.warning("Summary: T:%s | <30:%s | >30:%s | >60:%s | >120:%s | OnTrack: %s | Watching: %s | Critical:%s | Stalled:%s" % (
    len(virtualGuests), countVirtualGuestslt30, countVirtualGuestsgt30, countVirtualGuestsgt60,
    countVirtualGuestsgt120,
    ontrack, watching, critical, stalled))

# UPDATE STATS FOR NEXT RUN
stats = {"virtualGuests": len(virtualGuests),
         "ontrack": ontrack,
         "watching": watching,
         "critical": critical,
         "stalled": stalled}

# WRITE NEW STATS
with open('stats.json', 'w') as fp:
    json.dump(stats, fp)

