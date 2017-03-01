#################################################################################################
# Script runs periodically (Recommend every 5 minutes) to collects Hourly VSI Provisioning Data
# Alerts are generated based on status of provsioning jobs, and tickets opened if needed
#################################################################################################


import SoftLayer, json, configparser, argparse, logging,sendgrid, time, pytz
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from cloudant.client import Cloudant

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

def openTicket(guestId, hostname, requestedTime, transaction, delay):
    ########################
    # OPEN SOFTLAYER TICKET
    ########################
    ## Open SoftLayer ticket when provisioning takes too long if one doesn't already exist

    title = "Private VSI provisioning request stuck"
    content = "Provisioning request %s for virtual hostname %s was submitted at %s and has been in stuck in transaction %s for %s minutes and it not progressing.   Please investigate and provide ETA on provisioning completion." % (guestId, hostname, requestedTime, transaction, delay )
    subjectId = 1021 # hardware issue
    assignedUserId = 292280 #"IBM409582"

    SoftLayerTicket =  {
        'subjectId': subjectId,
        'title': title,
        'assignedUserId': assignedUserId
        }

    try:
        ticket = client['Ticket'].createStandardTicket(SoftLayerTicket, content)
        ticketId = ticket['firstUpdate']['ticketId']
        logging.warning("Ticket ID %s for Guest %s created." % (ticketId, guestId))

    except SoftLayer.SoftLayerAPIError as e:
        ticket = e.faultCode
        ticketId = 0
        logging.warning("Ticket:createStandardTicket(): %s, %s" % (e.faultCode, e.faultString))

    if ticketId != 0:
        try:
            attachedVirtualGuest = client['Ticket'].addAttachedVirtualGuest(guestId, id=ticketId)
            logging.warning("Attached VSI %s to ticket %s." % (guestId, ticketId))
        except SoftLayer.SoftLayerAPIError as e:
            ticket = e.faultCode
            logging.warning("Ticket:addAttachedVirtualGuest: %s, %s" % (e.faultCode, e.faultString))

    return ticketId


##########################################################
## READ CommandLine Arguments and load configuration file
##########################################################

parser = argparse.ArgumentParser(description="Check Audit Log for VSI.")
parser.add_argument("-u", "--username", help="SoftLayer API Username")
parser.add_argument("-k", "--apikey", help="SoftLayer APIKEY")
parser.add_argument("-c", "--config", help="config.ini file to load")
args = parser.parse_args()

# Read Config File
if args.config != None:
        filename = args.config
else:
        filename = "config.ini"

config = configparser.ConfigParser()
config.read(filename)

# Use username/apikey passed if available, otherwise use config file.
if args.username != None:
    username=args.username
else:
    username=config['api']['username']

if args.apikey != None:
    apikey=args.apikey
else:
    apikey=config['api']['apikey']


######################################
# Connect to SoftLayer API
######################################
client = SoftLayer.Client(username=username, api_key=apikey, endpoint_url=SoftLayer.API_PRIVATE_ENDPOINT)

######################################
# Notification Variables
######################################

if config['sendGrid']['apiKey'] == None:
    sendEmails = False
    sendGridApi = ""
    sendGridTo = []
    sendGridFrom = ""
    sendGridSubject = ""
else:
    sendEmails = True
    sendGridApi = config['sendGrid']['apiKey']
    sendGridTo = config['sendGrid']['to'].split(",")
    sendGridFrom = config['sendGrid']['from']
    sendGridSubject = config['sendGrid']['subject']


###########################################################
# define cloudant database in bluemix to hold daily results
###########################################################

if config['cloudant']['username'] == None:
    createDB = False
    queryDB = False
else:
    createDB = True
    queryDB = True
    cloudant = Cloudant(config['cloudant']['username'], config['cloudant']['password'], url=config['cloudant']['url'])
    cloudant.connect()
    vsistatsDb = cloudant["vsistats"]

######################################
## Flags to control script logic
######################################
creatTickets=True

######################################
# Enable Logging
######################################

central = pytz.timezone("US/Central")
today = central.localize(datetime.now())
logging.basicConfig( filename='events.log', format='%(asctime)s %(message)s', datefmt='%Y-%m-%d %I:%M:%S %p',level=logging.WARNING)

###########################################################
# Get details on all hourlyVirtualGuests being provisioned
###########################################################

try:
    virtualGuests = client['Account'].getHourlyVirtualGuests(
        mask='id, provisionDate, hostname, maxMemory, maxCpu, activeTicketCount, activeTickets, fullyQualifiedDomainName, lastTransaction, activeTransaction, activeTransactions,datacenter, datacenter.name,serverRoom, primaryBackendIpAddress, networkVlans, backendRouters,blockDeviceTemplateGroup')
except SoftLayer.SoftLayerAPIError as e:
    logging.warning("Account::getHourlyVirtualGuests(): %s, %s" % (e.faultCode, e.faultString))
    quit()

logging.warning('Found %s VirtualGuests.' % (len(virtualGuests)))


##############################
# Initiatlize Variables
#############################
provisioningDF=pd.DataFrame()
ontrack = 0
critical = 0
watching = 0
stalled = 0
ticketCount = 0

##############################
## Define EmailBody
##############################
emailbody = (
    '<table width="100%"><tr><th>guestId</th><th>hostName</th><th>TemplateImage</th><th>BCR</th><th>Vlan</th><th>createDate</th><th>ElapsedTime</th><th>transaction</th><th>Duration</th><th>Status</th><th>Ticket</th></tr>')


for virtualGuest in virtualGuests:
    if virtualGuest['provisionDate'] == "":  ## Null indicates a job being provisioned
        Id = virtualGuest['id']
        numTransactions=len(virtualGuest['activeTransactions'])
        guestId = virtualGuest['activeTransaction']['guestId']
        # GET TIME STAMP FOR REQUEST FROM OLDEST ACTIVE TRANSACTION
        createDate = virtualGuest['activeTransactions'][numTransactions-1]['createDate']
        createDateStamp = convert_timestamp(createDate)
        currentDateStamp = central.localize(datetime.now())
        delta = convert_timedelta(currentDateStamp - createDateStamp)
        hostName = virtualGuest['hostname']
        fullyQualifiedDomainName = virtualGuest['fullyQualifiedDomainName']
        activeTicketCount = virtualGuest['activeTicketCount']
        activeTickets = virtualGuest['activeTickets']
        maxCpu = virtualGuest['maxCpu']
        maxMemory = virtualGuest['maxMemory']

        if 'blockDeviceTemplateGroup' in virtualGuest:
            templateImage=virtualGuest['blockDeviceTemplateGroup']['name']
        else:
            templateImage="Stock Image"

        if "networkVlans" in virtualGuest:
            vlan = virtualGuest['networkVlans'][0]['vlanNumber']
        else:
            vlan=""

        if "backendRouters" in virtualGuest:
            if len(virtualGuest['backendRouters']) > 1:
                router=virtualGuest['backendRouters'][0]['hostname']
            else:
                router = virtualGuest['backendRouters']['hostname']
        else:
            router=""

        if "datacenter" in virtualGuest:
            datacenter=virtualGuest['datacenter']['name']
        else:
            datacenter=""

        if "serverRoom" in virtualGuest:
            serverRoom=virtualGuest['serverRoom']['longName']
        else:
            serverRoom=""

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
        if activeTicketCount > 0:
            ticketId = activeTickets[0]['id']
        else:
            ticketId=""


        ######################################################################
        # DETERMINE JOB STATUS BY LOOKING AT DURATION AND TIME IN TRANSACTION
        ######################################################################

        # IF DURATION PROGRESSING < 45 THEN ON TRACK
        if (delta) < 45:
            status = "ONTRACK"
            ontrack = ontrack + 1

        # IF DURATION BETWEEN 45 & 75 & PROGRESSING < 45 THEN ON AT RISK
        elif (delta >= 45) and (delta < 75):
            status = "ATRISK"
            watching = watching + 1

        # IF DURATION > 75 & PROGRESSING THEN ON TRACK MARK AS CRITICAL ONLY
        elif (delta) >= 75 and (statusDuration < 15):
            status = "CRITICAL"
            critical = critical + 1

        # IF DURATION > 60 & NOT PROGRESSING STEP >=15 THEN MARK STALLED & OPEN TICKET.
        elif (delta) >= 60 and (statusDuration >= 15):
            status = "STALLED"
            stalled = stalled + 1
            ## OPEN TICKET IF NOT PREVIOUSLY OPENED FOR THIS GUEST
            logging.warning("VSI stalled, active ticket count for GuestId = %s, is %s." % (guestId, activeTicketCount))
            if activeTicketCount == 0 and createTickets == True:
                logging.warning("Ticket not found for GuestId = %s, opening new ticket." % (guestId))
                ticketId = openTicket(guestId, fullyQualifiedDomainName, createDate, transactionStatus, delta)
                ticketCount=ticketCount + 1
            else:
                logging.warning("Ticket %s found for GuestId = %s." % (ticketId, guestId))


        logging.warning('VSI %s using %s image behind %s on vlan %s is %s. (delta=%s, duration=%s, request=%s).' % (guestId,templateImage,router, vlan, status,delta,statusDuration,datetime.strftime(createDateStamp, "%H:%M:%S%z")))

        #add or update guestId in dictionary for historical view
        docid=str(guestId)
        provisioning_detail = {"_id": docid,
                                  "docType": "vsidata",
                                  "hostName": hostName,
                                  "templateImage": templateImage,
                                  "datacenter": datacenter,
                                  "serverRoom": serverRoom,
                                  "router": router,
                                  "vlan": vlan,
                                  "maxMemory": maxMemory,
                                  "maxCpu": maxCpu,
                                  "primaryBackendIpAddress": primaryBackendIpAddress,
                                  "createDateStamp": str(createDateStamp),
                                  "delta": delta,
                                  "transactionStatus": transactionStatus,
                                  "statusDuration": statusDuration,
                                  "ticketId": ticketId}

        # add row to dataframe to calculate stats
        provisioningDF = provisioningDF.append(provisioning_detail, ignore_index=True)
        # Store VSI detail in table, update if already exists
        time.sleep(1)


        try:
            doc = vsistatsDb.create_document(provisioning_detail)
            logging.warning("Wrote new vsi detail record for guestId %s to database." % (docid))
        except:
            doc = vsistatsDb[docid]
            doc["hostName"] = hostName
            doc["templateImage"] = templateImage
            doc["datacenter"] = datacenter
            doc["serverRoom"] = serverRoom
            doc["router"] = router
            doc["vlan"] =  vlan
            doc["maxMemory"] = maxMemory
            doc["maxCpu"] = maxCpu
            doc["primaryBackendIpAddress"] = primaryBackendIpAddress
            doc["createDateStamp"] = str(createDateStamp)
            doc["delta"] = delta
            doc["transactionStatus"] = transactionStatus
            doc["statusDuration"] = statusDuration
            doc["ticketId"] = ticketId
            doc["alertStatus"] = status
            try:
                doc.save()
                logging.warning("Updating vsi detail record for guestId %s to database." % (docid))
            except:
                logging.warning("Error adding detail record for guestId %s to database." % (docid))


        # BUILD ROWS OF TABLE FOR EXCEPTION JOBS.
        # URL FOR TICKETS https://control.softlayer.com/support/tickets/34064689
        if status=="CRITICAL" or status=="STALLED":
            if statusDuration>(10*float(averageDuration)):
                emailbody=emailbody+(
                '<tr><td style="text-align: center;"><a href="https://internal.softlayer.com/HardwareTransaction/automatedManagement/cloudlayer/%s">%s</a></td><td style="text-align: center;">%s</td><td style="text-align: center;">%s</td>'
                '<td style="text-align: center;">%s</td><td style="text-align: center;">%s</td><td style="text-align: center;">%s</td><td style="text-align: center;background-color:#FF0000">%s</td><td style="text-align: center;">'
                '%s</td><td style="text-align: center;">%s</td><td style="text-align: center;background-color:#FF0000">%s</td><td style="text-align: center;"><a href="https://control.softlayer.com/support/tickets/%s">%s</a></td></tr>' % (
                guestId, guestId, hostName, templateImage, router, vlan, str(createDateStamp), delta,transactionStatus, statusDuration, status, ticketId, ticketId))
            else:
                emailbody=emailbody+('<tr><td style="text-align: center;"><a href="https://internal.softlayer.com/HardwareTransaction/automatedManagement/cloudlayer/%s">%s</a></td><td style="text-align: center;">%s</td><td style="text-align: center;">%s</td>'
                '<td style="text-align: center;">%s</td><td style="text-align: center;">%s</td><td style="text-align: center;">%s</td><td style="text-align: center;background-color:#FF0000">%s</td><td style="text-align: center;">'
                '%s</td><td style="text-align: center;">%s</td><td style="text-align: center;">%s</td><td style="text-align: center;"><a href="https://control.softlayer.com/support/tickets/%s">%s</a></td></tr>' % (
                guestId, guestId, hostName, templateImage, router, vlan, str(createDateStamp), delta,transactionStatus, statusDuration, status, ticketId,ticketId))


##
## Create Stats Pivot Table for current Provisioning Jobs
##

if len(provisioningDF)>0:
    # Create Pivot by Datacenter
    provisioningPivot = pd.pivot_table(provisioningDF,index=['datacenter'], values=['_id','maxMemory', 'maxCpu'], aggfunc={"_id":len,"maxMemory":np.sum, "maxCpu":np.sum}, fill_value=0, margins=True)
    provisioningPivot.columns = ['count', 'totalCPU', 'totalMemory' ]
    provisioning_json=provisioningPivot.to_json()
    # Calculate Distribution
    distribution0 = len(provisioningDF[provisioningDF.delta.between(0, 30, inclusive=True)])
    distribution30 = len(provisioningDF[provisioningDF.delta.between(31, 60, inclusive=True)])
    distribution60 = len(provisioningDF[provisioningDF.delta.between(61, 90, inclusive=True)])
    distribution90 = len(provisioningDF[provisioningDF.delta.between(91, 120, inclusive=True)])
    distribution120 = len(provisioningDF[provisioningDF.delta.between(121, 360, inclusive=True)])
    distribution360 = len(provisioningDF[provisioningDF.delta.between(361, 999999, inclusive=True)])
    logging.warning(
        "Summary: T:%s | <30:%s | >30:%s | >60:%s | >90:%s | >120:%s | >360:%s | OnTrack: %s | Watching: %s | Critical:%s | Stalled:%s" % (
            len(provisioningDF), distribution0, distribution30, distribution60, distribution90, distribution120,
            distribution360, ontrack, watching, critical, stalled))

else:
    provisioning_json = {}
    distribution0 = 0
    distribution30 = 0
    distribution60 = 0
    distribution90 = 0
    distribution120 = 0
    distribution360 = 0
    logging.warning('No active provisioning jobs found.')



##
## Create Stats Table for Hourly Virtual Guests Current State
##

# Create Dataframe from results
totalVirtualGuestsDataFrame=pd.DataFrame.from_dict(virtualGuests)

# simplify column to include just shortname of datacenter
for index, row in totalVirtualGuestsDataFrame.iterrows():
    totalVirtualGuestsDataFrame.loc[index, 'datacenter']  = row.datacenter['name']

# Create Pivot by Datacenter
vsiPivot = pd.pivot_table(totalVirtualGuestsDataFrame,index=['datacenter'], values=['id','maxMemory', 'maxCpu'], aggfunc={"id":len,"maxMemory":np.sum, "maxCpu":np.sum}, fill_value=0, margins=True)
# rename columns
vsiPivot.columns = ['count', 'totalCPU', 'totalMemory' ]

######################################
# Get last vsistat entry from database
######################################

try:
    results = vsistatsDb.get_view_result("_design/vsistats", "vsistats", raw_result=True, descending=True,limit=1,include_docs=True)
    lastProvisioningStats= json.loads(results['rows'][0]['doc']['provisioningStats'])
    lastCritical = lastProvisioningStats['eventsCritical']
    lastStalled = lastProvisioningStats['eventsStalled']
except:
    logging.warning('Unable to retreive previous statsfrom vsistats database')
    quit()


# UPDATE STATS FOR NEXT RUN

provisioningStats = { 'eventsOnTrack': ontrack,
                     'eventsWatching': watching,
                     'eventsCritical': critical,
                     'eventsStalled': stalled,
                     'newTicketsOpened': ticketCount}

record = {'docType': "vsistats",
         'timestamp': today.strftime("%s"),
         'totalVSIs': vsiPivot.to_json(),  # total VSI's active and active by datacenter
         'provisioningVSIs': provisioning_json,  # total provisioning VSI by datacenter
         'provisioningStats': json.dumps(provisioningStats)
         }

doc = vsistatsDb.create_document(record)
logging.warning("VsiStats document %s written to database." % (doc['_id']))


#########################################################################################
## IF CRITICAL OR STALLED JOBS INCREASE SEND EMAIL ALERT WITH TABLE IF NOTIFICATION=TRUE
#########################################################################################

logging.warning("### Send Alert?  if ( %s + %s > %s + %s) or (%s > %s):" % (critical, stalled, lastCritical, lastStalled, stalled, lastStalled))
if (critical + stalled > lastCritical + lastStalled)  or (stalled > lastStalled):
    logging.warning('Sending email alert: %s critical requests, a change from %s.  %s stalled requests, a change from %s.' % (
                   critical, lastCritical, stalled, lastStalled))
    sg = sendgrid.SendGridClient(sendGridApi)
    message = sendgrid.Mail()
    message.add_to(sendGridTo)
    message.set_subject(sendGridSubject)
    body = (
               '<p<b>%s total provisioning requests.<br>%s critical requests, a change from %s.<br>%s stalled requests, a change from %s. <br></b> View current requests at <a href="http://provisionstatus.mybluemix.net">http://provisionstatus.mybluemix.net</a></p><br><br><b>Exception Requests</b> <br>' % (
                   len(virtualGuests), critical, lastCritical, stalled, lastStalled)) + emailbody + "</tr></table>"
    message.set_html(body)
    message.set_from(sendGridSubject)
    status, msg = sg.send(message)
    logging.warning("Sendgrid response status code = %s" % (status))
else:
    logging.warning("Not sending alert messages.")