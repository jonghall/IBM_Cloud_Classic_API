import sys, getopt, socket, time, SoftLayer, json, string, configparser, os, argparse, csv, math, logging, requests
from datetime import datetime, timedelta, tzinfo
import pytz

import sendgrid
from twilio.rest import TwilioRestClient

# put your own credentials here
ACCOUNT_SID = "AC06837c4494699c87dbf6f7e4d80477a3"
AUTH_TOKEN = "bb65f9610c5c7c810dbf311e81e1c1d2"
smsclient = TwilioRestClient(ACCOUNT_SID, AUTH_TOKEN)


def convert_timedelta(duration):
    days, seconds = duration.days, duration.seconds
    hours = days * 24 + seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    totalminutes = round((days * 1440) + (hours * 60) + minutes + (seconds / 60), 1)
    return totalminutes


def convert_timestamp(sldate):
    formatedDate = sldate
    formatedDate = formatedDate[0:19]
    formatedDate = datetime.strptime(formatedDate, "%Y-%m-%dT%H:%M:%S")
    return formatedDate


def getDescription(categoryCode, detail):
    for item in detail:
        if item['categoryCode'] == categoryCode:
            return item['description']
    return "Not Found"


def initializeSoftLayerAPI(user, key, configfile):
    if user == None and key == None:
        if configfile != None:
            filename = args.config
        else:
            filename = "config.ini"
        config = configparser.ConfigParser()
        config.read(filename)
        client = SoftLayer.Client(username=config['api']['username'], api_key=config['api']['apikey'],
                                  endpoint_url=SoftLayer.API_PRIVATE_ENDPOINT)
    else:
        # client = SoftLayer.Client(username=config['api']['username'], api_key=config['api']['apikey'],endpoint_url=SoftLayer.API_PRIVATE_ENDPOINT)
        client = SoftLayer.Client(username=user, api_key=key)
    return client



## READ CommandLine Arguments and load configuration file
parser = argparse.ArgumentParser(description="Check Audit Log for VSI.")
parser.add_argument("-u", "--username", help="SoftLayer API Username")
parser.add_argument("-k", "--apikey", help="SoftLayer APIKEY")
parser.add_argument("-c", "--config", help="config.ini file to load")
args = parser.parse_args()

client = initializeSoftLayerAPI(args.username, args.apikey, args.config)

today = datetime.now()
startdate = datetime.strftime(today, "%m/%d/%Y") + " 0:0:0"
enddate = datetime.strftime(today, "%m/%d/%Y") + " 23:59:59"

# print ('%s Checking Provisioning Events.' % (datetime.strftime(datetime.now(),"%m/%d/%Y %H:%M:%S")))
logging.basicConfig(filename='events.log', format='%(asctime)s %(message)s', level=logging.INFO)

virtualGuests = client['Account'].getHourlyVirtualGuests(
    mask='id, provisionDate, hostname, activeTicketCount, lastTransaction, activeTransaction, activeTransactions,datacenter, serverRoom',
    filter={
        'hourlyVirtualGuests': {
            'provisionDate': {'operation': 'is null'}
        }
    })
logging.info('Found %s VirtualGuests being provisioned.' % (len(virtualGuests)))

# OPEN & WRITE HTML FILE
htmlfile = open("/var/www/html/current.html", "w")
htmlfile.write('<?xml version="1.0" encoding="utf-8"?>')
htmlfile.write('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"')
htmlfile.write('"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">')
htmlfile.write('<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">')
htmlfile.write('<head>')
htmlfile.write('<title>Current Provisioning Jobs</title>')
htmlfile.write('<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />')
htmlfile.write('<meta http-equiv="refresh" content="60" />')
htmlfile.write('</head>')
htmlfile.write('<body>')

htmlfile.write(
    '<p>Provisioning Status Detail at: %s</p>' % (datetime.strftime(datetime.now(), "%m/%d/%Y %H:%M:%S")))


htmlfile.write(
    '<table width="100%"><tr><th>guestId</th><th>hostName</th><th>datacenter</th><th>tickets</th><th>createDate</th><th>PowerOn</th><th>ElapsedTime</th><th>transactionStatus</th><th>statusDuration</th><th>Status</th></tr>')

countVirtualGuestslt30 = 0
countVirtualGuestsgt30 = 0
countVirtualGuestsgt60 = 0
countVirtualGuestsgt120 = 0
ontrack = 0
critical = 0
watching = 0
stalled = 0
ticket = []

for virtualGuest in virtualGuests:
    Id = virtualGuest['id']
    guestId = virtualGuest['activeTransaction']['guestId']
    createDate = virtualGuest['activeTransaction']['createDate']
    createDateStamp = convert_timestamp(createDate)
    currentDateStamp = datetime.now()
    delta = convert_timedelta(currentDateStamp - createDateStamp)
    hostName = virtualGuest['hostname']
    datacenter = virtualGuest['datacenter']['name']
    tickets = virtualGuest['activeTicketCount']
    if guestId not in ticket:
        ticket.append({guestId: {'count': 0, 'previouscount': 0}})
    else:
        ticket[guestId]['count'] = tickets
    transactionStatus = virtualGuest['activeTransaction']['transactionStatus']['name']
    statusDuration = virtualGuest['activeTransaction']['elapsedSeconds']

    if tickets > 0:
        message = ("%s Tickets open on guestID %s." % (tickets, guestId))
        smsclient.messages.create(
            to="14025988805",
            from_="+14025908566",
            body=message,
        )
        logging.info("Sending SMS message due to ticket status of GuestId %s." % (guestId))

    events = ""
    logging.info('Searching eventlog for POWERON detail for guestId %s.' % (guestId))
    while events is "":
        try:
            events = client['Event_Log'].getAllObjects(filter={'objectId': {'operation': guestId},
                                                               'eventName': {'operation': 'Power On'}})
        except SoftLayer.SoftLayerAPIError as e:
            logging.warning("Error: %s, %s" % (e.faultCode, e.faultString))
            time.sleep(5)
    found = 0
    powerOnDateStamp = datetime.now()
    for event in events:
        if event['eventName'] == "Power On":

            eventdate = event["eventCreateDate"]
            # eventdate = eventdate[0:29] + eventdate[-2:]
            # Strip TZ off
            eventdate = eventdate[0:26]
            eventdate = datetime.strptime(eventdate, "%Y-%m-%dT%H:%M:%S.%f")

            if eventdate < powerOnDateStamp:
                powerOnDateStamp = eventdate
                found = 1

    if found == 1:
        logging.info('POWERON detail for guestId %s FOUND.' % (guestId))
        powerOnDelta = convert_timedelta(powerOnDateStamp - createDateStamp)
    else:
        logging.info('POWERON detail for guestId %s NOT FOUND.' % (guestId))
        powerOnDelta = 0

    status = "unknown"
    logging.info('Classifying provisioning status for guestId %s.' % (guestId))
    if powerOnDelta == 0:
        # IF LESS THAN 30 MINUTES NO PROBLEM ON TRACK
        if delta <= 30:
            status = "ONTRACK/NOPWR"
            ontrack = ontrack + 1
        # IF NO POWERON AFTER 30 MINUTES MARK CRITICAL
        if delta > 30:
            status = "CRITICAL/NOPWR"
            critical = critical + 1
        if delta > 120:
            status = "STALLED/NOPWR"
            stalled = stalled + 1
    else:
        # IF LESS THAN 30 MINUTES NO PROBLEM ON TRACK
        if (delta - powerOnDelta) <= 30:
            status = "ONTRACK/PWR"
            ontrack = ontrack + 1
        # IF TOTAL TIME MINUS POWERON BETWEEN 30-60 MINUTES WERE GOOD BUT WATCH.
        if (delta - powerOnDelta) > 30 and (delta - powerOnDelta) < 60:
            status = "ATRISK/PWR"
            watching = watching + 1
        # IF TOTAL TIME MINUS POWERON LONGER THAN AN HOUR BUT LESS THAN 2 MARK CRITICAL.
        if (delta - powerOnDelta) > 60 and (delta - powerOnDelta) < 120:
            status = "CRITICAL/PWR"
            critical = critical + 1
        # ANything over 2 hours cosnider stalled.
        if delta > 120:
            status = "STALLED/PWR"
            stalled = stalled + 1

    htmlfile.write(
        '<tr><td style="text-align: center;">%s</td><td style="text-align: center;">%s</td><td style="text-align: center;">%s</td><td style="text-align: center;">'
        '%s</td><td style="text-align: center;">%s</td><td style="text-align: center;">%s</td><<td style="text-align: center;">%s</td><td style="text-align: center;">'
        '%s</td><td style="text-align: center;">%s</td><td style="text-align: center;">%s</td></tr>' % (
        guestId, hostName, datacenter, tickets, createDate, powerOnDelta, delta,
        transactionStatus, statusDuration, status))

    if delta < 30:
        countVirtualGuestslt30 = countVirtualGuestslt30 + 1
    if delta >= 30 and delta < 60:
        countVirtualGuestsgt30 = countVirtualGuestsgt30 + 1
    if delta >= 60 and delta < 120:
        countVirtualGuestsgt60 = countVirtualGuestsgt60 + 1
    if delta >= 120:
        countVirtualGuestsgt120 = countVirtualGuestsgt120 + 1



# CREATE HTML TABLES
htmlfile.write('</tr></table><br /><br /><b>Provisioning Summary</b><br>')
htmlfile.write(
    '<table width="200"><tr><th style="text-align: left;">Total</th><td style="text-align: center;">%s</td></tr><tr><th style="text-align: left;">LT 30</th><td style="text-align: center;">%s</td></tr>' % (
    len(virtualGuests), countVirtualGuestslt30))
htmlfile.write(
    '<tr><th style="text-align: left;">GT 30</th><td style="text-align: center;">%s</td></tr><tr><th style="text-align: left;">GT 60</th><td style="text-align: center;">%s</td></tr>' % (
    countVirtualGuestsgt30, countVirtualGuestsgt60))
htmlfile.write(
    '<tr><th style="text-align: left;">GT 120</th><td style="text-align: center;">%s</td></tr>' % (countVirtualGuestsgt120))
htmlfile.write(
    '<tr><th style="text-align: left;">OnTrack</th><td style="text-align: center;">%s</td></tr><tr><th style="text-align: left;">Watching</th><td style="text-align: center;">%s</td></tr>' % (
    ontrack, watching))
htmlfile.write(
    '<tr><th style="text-align: left;">Critical</th><td style="text-align: center;">%s</td></tr><tr><th style="text-align: left;">Stalled</th><td style="text-align: center;">%s</td></tr></table>' % (
    critical, stalled))

logging.info("T:%s | <30:%s | >30:%s | >60:%s | >120:%s | OnTrack: %s | Watching: %s | Critical:%s | Stalled:%s" % (
    len(virtualGuests), countVirtualGuestslt30, countVirtualGuestsgt30, countVirtualGuestsgt60,
    countVirtualGuestsgt120,
    ontrack, watching, critical, stalled))

if critical > 0:
    # Send SMS message
    message = (
        "%s Critical Jobs.  View at http://web01.ibmsldemo.com/current.html" % (
            critical))
    smsclient.messages.create(
        to="14025988805",
        from_="+14025908566",
        body=message,
    )
    # Trigger Maker Receipe with details
    url = 'https://maker.ifttt.com/trigger/aficritical/with/key/jehAniL4SfD0glj5AR4IZ5EJKkDJ5uwYfsyEkL7r4_L'
    data = {'value1': len(virtualGuests),
            'value2': critical,
            'value3': stalled}
    req = requests.post(url, json=data)
    logging.info("Sending SMS message due to increase in critical change.")

