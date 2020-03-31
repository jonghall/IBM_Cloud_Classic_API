#!/usr/bin/env python3
# invoiceAnalysis.py - A script to export IBM Cloud Classic Infrastructure Invoices
# Author: Jon Hall
# Copyright (c) 2020
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

import SoftLayer, argparse, time, os
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

def getDescription(categoryCode, detail):
    for item in detail:
        if 'categoryCode' in item:
            if item['categoryCode'] == categoryCode:
                return item['product']['description'].strip()
    return ""

def getibminvoicedate(invoice_date):

    # Determine IBM GTS Invoice (20th - 19th of month) fro SL invoice date
    year = invoiceDate.year
    month = invoiceDate.month
    day = invoiceDate.day
    if day <= 19:
        month = month + 1
    else:
        month = month + 2

    if month > 12:
        month = month - 12
        year = year + 1
    return datetime(year, month, 1).strftime('%Y-%m')

## READ CommandLine Arguments and load configuration file
parser = argparse.ArgumentParser(description="Export detail from invoices between dates sorted by Hourly vs Monthly "
                                             " between Start and End date.")
parser.add_argument("-u", "--username", default=os.environ.get('SL_USER', None), help="IBM Cloud Classic API Key Username")
parser.add_argument("-k", "--apikey", default=os.environ.get('SL_API_KEY', None), help="IBM Cloud Classic API Key")
parser.add_argument("-s", "--startdate", help="Start date mm/dd/yy")
parser.add_argument("-e", "--enddate", help="End date mm/dd/yyyy")
parser.add_argument("-o", "--output", default="invoices-detail.xlsx", help="Filename .xlsx for output.")

args = parser.parse_args()

if args.username == None or args.apikey == None:
    print ("You must provide a IBM Cloud Classic Username & apiKey")
    quit()

client = SoftLayer.Client(username=args.username, api_key=args.apikey)

if args.startdate == None:
    startdate=input("Report Start Date (MM/DD/YYYY): ")
else:
    startdate=args.startdate

if args.enddate == None:
    enddate=input("Report End Date (MM/DD/YYYY): ")
else:
    enddate=args.enddate


# Create dataframe to work with
df=pd.DataFrame(columns=['SL_Invoice',
                   'IBM_Invoice',
                   'Invoice_Number',
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

#
# GET LIST OF INVOICES
#

print()
print("Looking up invoices....")

# Build Filter for Invoices
InvoiceList = client['Account'].getInvoices(mask='id,createDate,typeCode,invoiceTotalAmount,invoiceTotalRecurringAmount,invoiceTopLevelItemCount',filter={
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


for invoice in InvoiceList:
    if float(invoice['invoiceTotalAmount']) == 0:
        #Skip because zero balance
        continue

    invoiceID = invoice['id']
    invoiceDate = datetime.strptime(invoice['createDate'][:10], "%Y-%m-%d")
    invoiceTotalAmount = float(invoice['invoiceTotalAmount'])
    ibmInvoiceDate= getibminvoicedate(invoiceDate)

    invoiceTotalRecurringAmount = float(invoice['invoiceTotalRecurringAmount'])
    invoiceType = invoice['typeCode']
    totalItems = invoice['invoiceTopLevelItemCount']

    # PRINT INVOICE SUMMARY LINE
    print()
    print('{:<20} {:<20}  {:>16} {:>16} {:>16} {:<15}'.format("Invoice Date", "Invoice Number", "Items",
                                                                   "Recurring Charge", "Invoice Amount", "Type"))
    print('{:<20} {:<20}  {:>16} {:>16} {:>16} {:<15}'.format("==============", "================", "=====",
                                                                   "================", "==============", "===="))
    print('{:20} {:<20}  {:>16} {:>16,.2f} {:>16,.2f} {:<15}'.format(datetime.strftime(invoiceDate, "%Y-%m-%d"),
                                                                          invoiceID,
                                                                          totalItems,
                                                                          invoiceTotalAmount,
                                                                          invoiceTotalRecurringAmount, invoiceType))

    limit = 200 ## set limit of record returned
    for offset in range(0, totalItems, limit):
        print("Retrieving %s invoice line items for Invoice %s at Offset %s of %s" % (limit, invoiceID, offset, totalItems))
        #nonZeroAssociatedChildren.description, nonZeroAssociatedChildren.categoryCode, nonZeroAssociatedChildren.hourlyRecurringFee
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
                hostName = item['hostName']+"."+item['domainName']
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
            row = {'SL_Invoice': invoiceDate,
                   'IBM_Invoice': ibmInvoiceDate,
                   'Invoice_Number': invoiceID,
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


# Write dataframe to excel
print("Creating Pivots File.")
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
                        columns=["IBM_Invoice"],
                        aggfunc={'totalOneTimeAmount': np.sum, 'totalRecurringCharge': np.sum}, fill_value=0).\
                                rename(columns={'totalRecurringCharge': 'TotalRecurring'})
invoiceSummary.to_excel(writer, 'InvoiceSummary')
worksheet = writer.sheets['InvoiceSummary']

#
# Build a pivot table by Category with totalRecurringCharges
#
categorySummary = pd.pivot_table(df, index=["Category", "Description"],
                        values=["totalRecurringCharge"],
                        columns=["IBM_Invoice"],
                        aggfunc={'totalRecurringCharge': np.sum}, fill_value=0).\
                                rename(columns={'totalRecurringCharge': 'TotalRecurring'})
categorySummary.to_excel(writer, 'CategorySummary')
format1 = workbook.add_format({'num_format': '$#,##0.00'})
format2 = workbook.add_format({'align': 'left'})
worksheet = writer.sheets['CategorySummary']


#
# Build a pivot table for Hourly VSI's with totalRecurringCharges
#
virtualServers = df.query('Category == ["Computing Instance"] and Hourly == [True]')
virtualServerPivot = pd.pivot_table(virtualServers, index=["Description", "OS"],
                        values=["Hours", "totalRecurringCharge"],
                        columns=["IBM_Invoice"],
                        aggfunc={'Description': len, 'Hours': np.sum, 'totalRecurringCharge': np.sum}, fill_value=0).\
                                rename(columns={"Description": 'qty', 'Hours': 'Total Hours', 'totalRecurringCharge': 'TotalRecurring'})
virtualServerPivot.to_excel(writer, 'HrlyVirtualServerPivot')
worksheet = writer.sheets['HrlyVirtualServerPivot']


#
# Build a pivot table for Monthly VSI's with totalRecurringCharges
#
monthlyVirtualServers = df.query('Category == ["Computing Instance"] and Hourly == [False]')
virtualServerPivot = pd.pivot_table(monthlyVirtualServers, index=["Description", "OS"],
                        values=["totalRecurringCharge"],
                        columns=["IBM_Invoice"],
                        aggfunc={'Description': len, 'totalRecurringCharge': np.sum}, fill_value=0).\
                                rename(columns={"Description": 'qty', 'totalRecurringCharge': 'TotalRecurring'})
virtualServerPivot.to_excel(writer, 'MnthlyVirtualServerPivot')
worksheet = writer.sheets['MnthlyVirtualServerPivot']


#
# Build a pivot table for Hourly Bare Metal with totalRecurringCharges
#
bareMetalServers = df.query('Category == ["Server"]and Hourly == [True]')
bareMetalServerPivot = pd.pivot_table(bareMetalServers, index=["Description", "OS"],
                        values=["Hours", "totalRecurringCharge"],
                        columns=["IBM_Invoice"],
                        aggfunc={'Description': len,  'totalRecurringCharge': np.sum}, fill_value=0).\
                                rename(columns={"Description": 'qty', 'Hours': np.sum, 'totalRecurringCharge': 'TotalRecurring'})
bareMetalServerPivot.to_excel(writer, 'HrlyBaremetalServerPivot')
worksheet = writer.sheets['HrlyBaremetalServerPivot']

#
# Build a pivot table for Monthly Bare Metal with totalRecurringCharges
#
monthlyBareMetalServers = df.query('Category == ["Server"] and Hourly == [False]')
monthlyBareMetalServerPivot = pd.pivot_table(monthlyBareMetalServers, index=["Description", "OS"],
                        values=["totalRecurringCharge"],
                        columns=["IBM_Invoice"],
                        aggfunc={'Description': len,  'totalRecurringCharge': np.sum}, fill_value=0).\
                                rename(columns={"Description": 'qty', 'totalRecurringCharge': 'TotalRecurring'})
monthlyBareMetalServerPivot.to_excel(writer, 'MthlyBaremetalServerPivot')
worksheet = writer.sheets['MthlyBaremetalServerPivot']


writer.save()
