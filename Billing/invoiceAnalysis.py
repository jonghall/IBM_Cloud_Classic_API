#!/usr/bin/env python3
# invoiceAnalysis.py - A script to export IBM Cloud Classic Infrastructure Invoices
# Author: Jon Hall
# Copyright (c) 2021
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
#   Get RECURRING, NEW, and Onetime Invoices with a invoice amount > 0
#   Return toplevel items and export to excel spreadsheet
__author__ = 'jonhall'

import SoftLayer, argparse, os, logging, logging.config, json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from logdna import LogDNAHandler

def setup_logging(default_path='logging.json', default_level=logging.info, env_key='LOG_CFG'):

    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
        if "handlers" in config:
            if "logdna" in config["handlers"]:
                config["handlers"]["logdna"]["key"] = os.getenv("logdna_ingest_key")
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)

def getDescription(categoryCode, detail):
    for item in detail:
        if 'categoryCode' in item:
            if item['categoryCode'] == categoryCode:
                return item['product']['description'].strip()
    return ""

def getSLIClinvoicedate(invoiceDate):
    # Determine SLIC  Invoice (20th prev month - 19th of month) from portal invoice make current month SLIC invoice.
    year = invoiceDate.year
    month = invoiceDate.month
    day = invoiceDate.day
    if day <= 19:
        month = month + 0
    else:
        month = month + 1

    if month > 12:
        month = month - 12
        year = year + 1
    return datetime(year, month, 1).strftime('%Y-%m')

def getInvoices(startdate, enddate):
    #
    # GET LIST OF INVOICES BETWEEN DATES
    #
    logging.info("Looking up invoices....")

    # Build Filter for Invoices
    invoiceList = client['Account'].getInvoices(mask='id,createDate,typeCode,invoiceTotalAmount,invoiceTotalRecurringAmount,invoiceTopLevelItemCount', filter={
            'invoices': {
                'createDate': {
                    'operation': 'betweenDate',
                    'options': [
                         {'name': 'startDate', 'value': [startdate+" 0:0:0"]},
                         {'name': 'endDate', 'value': [enddate+" 23:59:59"]}
                    ]
                }
            }
    })
    return invoiceList

def getInvoiceDetail(invoiceList):
    #
    # GET InvoiceDetail
    #
    global df, invoicePivot
    for invoice in invoiceList:
        if float(invoice['invoiceTotalAmount']) == 0:
            #Skip because zero balance
            continue

        invoiceID = invoice['id']
        invoiceDate = datetime.strptime(invoice['createDate'][:10], "%Y-%m-%d")
        invoiceTotalAmount = float(invoice['invoiceTotalAmount'])

        SLICInvoiceDate = getSLIClinvoicedate(invoiceDate)

        invoiceTotalRecurringAmount = float(invoice['invoiceTotalRecurringAmount'])
        invoiceType = invoice['typeCode']
        totalItems = invoice['invoiceTopLevelItemCount']

        # PRINT INVOICE SUMMARY LINE
        logging.info('Invoice: {} Date: {} Type:{} Items: {} Amount: ${:,.2f}'.format(invoiceID, datetime.strftime(invoiceDate, "%Y-%m-%d"),invoiceType, totalItems, invoiceTotalRecurringAmount))

        limit = 250 ## set limit of record returned
        for offset in range(0, totalItems, limit):
            if ( totalItems - offset - limit ) < 0:
                remaining = totalItems - offset
            logging.info("Retrieving %s invoice line items for Invoice %s at Offset %s of %s" % (limit, invoiceID, offset, totalItems))

            Billing_Invoice = client['Billing_Invoice'].getInvoiceTopLevelItems(id=invoiceID, limit=limit, offset=offset,
                                    mask='id, billingItemId, categoryCode, category.name, hourlyFlag, hostName, domainName, product.description, createDate, totalRecurringAmount, totalOneTimeAmount, usageChargeFlag, hourlyRecurringFee, children.description, children.categoryCode, children.product, children.hourlyRecurringFee')
            count = 0
            # ITERATE THROUGH DETAIL
            for item in Billing_Invoice:
                totalOneTimeAmount = float(item['totalOneTimeAmount'])
                billingItemId = item['billingItemId']
                category = item["categoryCode"]
                categoryName = item["category"]["name"]
                description = item['product']['description']
                memory = getDescription("ram", item["children"])
                os = getDescription("os", item["children"])

                if 'hostName' in item:
                    if 'domainName' in item:
                        hostName = item['hostName']+"."+item['domainName']
                    else:
                        hostName = item['hostName']
                else:
                    hostName = ""

                recurringFee = float(item['totalRecurringAmount'])

                # If Hourly calculate hourly rate and total hours
                if item["hourlyFlag"]:
                    if float(item["hourlyRecurringFee"]) > 0:

                        hourlyRecurringFee = float(item['hourlyRecurringFee']) + sum(
                            float(child['hourlyRecurringFee']) for child in item["children"])
                        hours = round(float(recurringFee) / hourlyRecurringFee)
                    else:
                        hourlyRecurringFee = 0
                        hours = 0
                # Not an hourly billing item
                else:
                    hourlyRecurringFee = 0
                    hours = 0

                # Special handling for storage
                if category == "storage_service_enterprise" or category == "performance_storage_iscsi":

                    if category == "storage_service_enterprise":
                        iops = getDescription("storage_tier_level", item["children"])
                        storage = getDescription("performance_storage_space", item["children"])
                        snapshot = getDescription("storage_snapshot_space", item["children"])
                        if snapshot == "":
                            description = storage + " " + iops + " "
                        else:
                            description = storage+" " + iops + " with " + snapshot
                    else:
                        iops = getDescription("performance_storage_iops", item["children"])
                        storage = getDescription("performance_storage_space", item["children"])
                        description = storage + " " + iops
                else:
                    description = description.replace('\n', " ")

                # Append record to dataframe
                row = {'Portal_Invoice_Date': invoiceDate.strftime("%Y-%m-%d"),
                       'IBM_Invoice_Month': SLICInvoiceDate,
                       'Portal_Invoice_Number': invoiceID,
                       'BillingItemId': billingItemId,
                       'hostName': hostName,
                       'Category': categoryName,
                       'Description': description,
                       'Memory': memory,
                       'OS': os,
                       'Hourly': item["hourlyFlag"],
                       'Usage': item["usageChargeFlag"],
                       'Hours': hours,
                       'HourlyRate': round(hourlyRecurringFee,3),
                       'totalRecurringCharge': round(recurringFee,3),
                       'totalOneTimeAmount': float(totalOneTimeAmount),
                       'InvoiceTotal': float(invoiceTotalAmount),
                       'InvoiceRecurring': float(invoiceTotalRecurringAmount),
                       'Type': invoiceType
                        }


                df = df.append(row, ignore_index=True)

def createReport():
    # Write dataframe to excel
    global df
    logging.info("Creating Pivots File.")
    writer = pd.ExcelWriter(args.output, engine='xlsxwriter')
    workbook = writer.book

    #
    # Write detail tab
    #
    df.to_excel(writer, 'Detail')
    usdollar = workbook.add_format({'num_format': '$#,##0.00'})

    worksheet = writer.sheets['Detail']
    worksheet.set_column('P:S', 18, usdollar)

    #
    # Build a pivot table by Invoice Type
    #
    invoiceSummary = pd.pivot_table(df, index=["Type", "Category"],
                            values=["totalOneTimeAmount", "totalRecurringCharge"],
                            columns=['IBM_Invoice_Month'],
                            aggfunc={'totalOneTimeAmount': np.sum, 'totalRecurringCharge': np.sum}, fill_value=0).\
                                    rename(columns={'totalRecurringCharge': 'TotalRecurring'})
    invoiceSummary.to_excel(writer, 'InvoiceSummary')
    worksheet = writer.sheets['InvoiceSummary']
    format1 = workbook.add_format({'num_format': '$#,##0.00'})
    format2 = workbook.add_format({'align': 'left'})
    worksheet.set_column("A:A", 20, format2)
    worksheet.set_column("B:B", 40, format2)
    worksheet.set_column("C:ZZ", 18, format1)
    #
    # Map Portal Invoices to SLIC Invoices
    #

    invoicedf = df
    invoicedf['Invoice_Amount'] = invoicedf['totalOneTimeAmount'] + invoicedf['totalRecurringCharge']
    SLICInvoice = pd.pivot_table(invoicedf,
                                 index=["IBM_Invoice_Month", "Portal_Invoice_Date", "Portal_Invoice_Number", "Type"],
                                 values=["Invoice_Amount"],
                                 aggfunc={'Invoice_Amount': np.sum}, fill_value=0)
    SLICInvoice.to_excel(writer, 'InvoiceMap')
    worksheet = writer.sheets['InvoiceMap']
    format1 = workbook.add_format({'num_format': '$#,##0.00'})
    format2 = workbook.add_format({'align': 'left'})
    worksheet.set_column("A:D", 20, format2)
    worksheet.set_column("E:ZZ", 18, format1)


    #
    # Build a pivot table by Category with totalRecurringCharges
    #
    categorySummary = pd.pivot_table(df, index=["Category", "Description"],
                            values=["totalRecurringCharge"],
                            columns=['IBM_Invoice_Month'],
                            aggfunc={'totalRecurringCharge': np.sum}, fill_value=0).\
                                    rename(columns={'totalRecurringCharge': 'TotalRecurring'})
    categorySummary.to_excel(writer, 'CategorySummary')
    worksheet = writer.sheets['CategorySummary']
    format1 = workbook.add_format({'num_format': '$#,##0.00'})
    format2 = workbook.add_format({'align': 'left'})
    worksheet.set_column("A:A", 40, format2)
    worksheet.set_column("B:B", 40, format2)
    worksheet.set_column("C:ZZ", 18, format1)

    #
    # Build a pivot table for Hourly VSI's with totalRecurringCharges
    #
    virtualServers = df.query('Category == ["Computing Instance"] and Hourly == [True]')
    if len(virtualServers) > 0:
        virtualServerPivot = pd.pivot_table(virtualServers, index=["Description", "OS"],
                                values=["Hours", "totalRecurringCharge"],
                                columns=['IBM_Invoice_Month'],
                                aggfunc={'Description': len, 'Hours': np.sum, 'totalRecurringCharge': np.sum}, fill_value=0).\
                                        rename(columns={"Description": 'qty', 'Hours': 'Total Hours', 'totalRecurringCharge': 'TotalRecurring'})
        virtualServerPivot.to_excel(writer, 'HrlyVirtualServerPivot')
        worksheet = writer.sheets['HrlyVirtualServerPivot']

    #
    # Build a pivot table for Monthly VSI's with totalRecurringCharges
    #
    monthlyVirtualServers = df.query('Category == ["Computing Instance"] and Hourly == [False]')
    if len(monthlyVirtualServers) > 0:
        virtualServerPivot = pd.pivot_table(monthlyVirtualServers, index=["Description", "OS"],
                                values=["totalRecurringCharge"],
                                columns=['IBM_Invoice_Month'],
                                aggfunc={'Description': len, 'totalRecurringCharge': np.sum}, fill_value=0).\
                                        rename(columns={"Description": 'qty', 'totalRecurringCharge': 'TotalRecurring'})
        virtualServerPivot.to_excel(writer, 'MnthlyVirtualServerPivot')
        worksheet = writer.sheets['MnthlyVirtualServerPivot']


    #
    # Build a pivot table for Hourly Bare Metal with totalRecurringCharges
    #
    bareMetalServers = df.query('Category == ["Server"]and Hourly == [True]')
    if len(bareMetalServers) > 0:
        bareMetalServerPivot = pd.pivot_table(bareMetalServers, index=["Description", "OS"],
                                values=["Hours", "totalRecurringCharge"],
                                columns=['IBM_Invoice_Month'],
                                aggfunc={'Description': len,  'totalRecurringCharge': np.sum}, fill_value=0).\
                                        rename(columns={"Description": 'qty', 'Hours': np.sum, 'totalRecurringCharge': 'TotalRecurring'})
        bareMetalServerPivot.to_excel(writer, 'HrlyBaremetalServerPivot')
        worksheet = writer.sheets['HrlyBaremetalServerPivot']

    #
    # Build a pivot table for Monthly Bare Metal with totalRecurringCharges
    #
    monthlyBareMetalServers = df.query('Category == ["Server"] and Hourly == [False]')
    if len(monthlyBareMetalServers) > 0:
        monthlyBareMetalServerPivot = pd.pivot_table(monthlyBareMetalServers, index=["Description", "OS"],
                                values=["totalRecurringCharge"],
                                columns=['IBM_Invoice_Month'],
                                aggfunc={'Description': len,  'totalRecurringCharge': np.sum}, fill_value=0).\
                                        rename(columns={"Description": 'qty', 'totalRecurringCharge': 'TotalRecurring'})
        monthlyBareMetalServerPivot.to_excel(writer, 'MthlyBaremetalServerPivot')
        worksheet = writer.sheets['MthlyBaremetalServerPivot']

    writer.save()

if __name__ == "__main__":
    setup_logging()
    parser = argparse.ArgumentParser(
        description="Export detail from invoices between dates sorted by Hourly vs Monthly "
                    " between Start and End date.")
    parser.add_argument("-u", "--username", default=os.environ.get('SL_USER', None),
                        help="IBM Cloud Classic API Key Username")
    parser.add_argument("-k", "--apikey", default=os.environ.get('SL_API_KEY', None), help="IBM Cloud Classic API Key")
    parser.add_argument("-s", "--startdate", help="Start date mm/dd/yy")
    parser.add_argument("-e", "--enddate", help="End date mm/dd/yyyy")
    parser.add_argument("-o", "--output", default="invoices-detail.xlsx", help="Filename .xlsx for output.")

    args = parser.parse_args()

    if args.username == None or args.apikey == None:
        logging.warning("IBM Cloud Classic Username & apiKey not specified and not set via environment variables, using default API keys.")
        client = SoftLayer.Client()
    else:
        client = SoftLayer.Client(username=args.username, api_key=args.apikey)

    if args.startdate == None:
        logging.error("You must provide a start date in the format of MM/DD/YYYY.")
        quit()
    else:
        startdate = args.startdate

    if args.enddate == None:
        logging.error("You must provide an end date in the format of MM/DD/YYYY.")
        quit()
    else:
        enddate = args.enddate

    # Create dataframe to work with

    df = pd.DataFrame(columns=['Portal_Invoice_Date',
                               'IBM_Invoice_Month',
                               'Portal_Invoice_Number',
                               'Type',
                               'BillingItemId',
                               'hostName',
                               'Category',
                               'Description',
                               'Memory',
                               'OS',
                               'Hourly',
                               'Usage',
                               'Hours',
                               'HourlyRate',
                               'totalRecurringCharge',
                               'totalOneTimeAmount',
                               'InvoiceTotal',
                               'InvoiceRecurring'])

    invoiceList = getInvoices(startdate, enddate)
    getInvoiceDetail(invoiceList)
    createReport()
