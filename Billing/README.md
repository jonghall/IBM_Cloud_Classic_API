**IBM Cloud Classic Infrastructure Billing API Scripts**

Script | Description
------ | -----------
invoiceAnalysis.py | Analyzes all invoices between two dates and creates excel reports.
requirements.txt | Package requirements
logging.json | LOGGER config used by script
Dockerfile | Docker Build file used by code engine to build container.

*invoiceAnalysis.py* analyzes IBM Cloud Classic Infrastructure invoices between two dates and consolidates billing data into an
Excel worksheet for review.  Each tab has a breakdown based on:

   - ***Detail*** tab has every invoice item for analyzed invoices represented as one row each.  All invoice types are included, including CREDIT invoices.  This data is summarized on the following tabs.
   - ***InvoiceSummary*** tab is a pivot table of all the charges by product category & month for analyzed invoices. It also breaks out oneTime amounts vs Recurring invoices.
   - ***CategorySummary*** tab is another pivot of all recurring charges broken down by Category, sub category (for example specific VSI sizes)
   - The following excel tabs will only exist if there are servers of these types on the analyzed invoices
        - ***HrlyVirtualServerPivot*** tab is a pivot of just Hourly Classic VSI's
        - ***MnthlyVirtualServerPivot*** tab is a pivot of just monthly Classic VSI's
        - ***HrlyBareMetalServerPivot*** tab is a pivot of Hourly Bare Metal Servers
        - ***MnthlyBareMetalServerPivot*** tab is a pivot table of monthly Bare Metal Server

Instructions:

1. Install required packages.  
````
pip install -r requirements.txt
````
2.  Set environment variables.
```bazaar
export SL_API_USERNAME=IBMxxxxx
export SL_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxx
```

3.  Run Python script.
```bazaar
python invoiceAnalysis.py -s 01/01/2021 -e 05/31/2021 --output analysis_JanToMay.XLSX
```

```bazaar
usage: invoiceAnalysis.py [-h] [-u USERNAME] [-k APIKEY] [-s STARTDATE] [-e ENDDATE] [--kyndryl] [-o OUTPUT]

Export detail from invoices between dates sorted by Hourly vs Monthly between Start and End date.

optional arguments:
  -h, --help            show this help message and exit
  -u USERNAME, --username USERNAME
                        IBM Cloud Classic API Key Username
  -k APIKEY, --apikey APIKEY
                        IBM Cloud Classic API Key
  -s STARTDATE, --startdate STARTDATE
                        Start date mm/dd/yy
  -e ENDDATE, --enddate ENDDATE
                        End date mm/dd/yyyy
  -o OUTPUT, --output OUTPUT
                        Filename .xlsx for output.

```
