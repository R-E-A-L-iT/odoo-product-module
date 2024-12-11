# -*- coding: utf-8 -*-

from .utilities import utilities
from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo.tools.translate import _
from odoo import models

from .product_common import product_sync_common

_logger = logging.getLogger(__name__)

class sync_pricelist:

    def __init__(self, name, sheet, database):
        self.name = name
        self.sheet = sheet
        self.database = database
        self.sync_report = []



    # add error to sync report function
    # sync report sent on sync end
    def add_to_report(self, level, message):
        entry = f"{level.upper()}: {message}"
        self.sync_report.append(entry)



    # utility function
    # in odoo, booleans are "True" or "False"
    # in sheets, booleans are "TRUE" or "FALSE"
    # this function normalizes those values
    def normalize_bools(self, field, value):
        if field in ["publish", "expire"]:
            if value.strip().upper() in ["TRUE", "1"]:
                return True
            elif value.strip().upper() in ["FALSE", "0", ""]:
                return False
        return value.strip()



    # utility function
    # in odoo, dates are in this format: 2024-01-01
    # in sheets, dates are in this format: 2024-1-1
    # this function normalizes those values
    # also handles dates being blank or "FALSE"
    def normalize_date(self, value):
        try:
            
            # handle none or false values
            if not value or (isinstance(value, str) and value.strip().upper() == "FALSE"):
                return ""

            # convert datetime object to string
            if isinstance(value, (datetime, date)):
                return value.strftime("%Y-%m-%d")

            # normalize string date values
            if isinstance(value, str):
                return datetime.strptime(value.strip(), "%Y-%m-%d").strftime("%Y-%m-%d")

            # fallback
            _logger.warning("normalize_date: Unexpected type for value '%s'. Returning as-is.", value)
            return str(value)

        except ValueError:
            _logger.warning("normalize_date: Invalid date value '%s'. Returning as-is.", value)
            return str(value)


    
    # this function will be called to start the synchronization process for ccp.
    # it delegates the function of actually updating or creating the ccp item to the other two functions
    def syncPricelist(self):
        _logger.info("syncPricelist: Starting synchronization process for pricelist")

        # variables to verify format
        # if you need to add more columns for new sync data, add them here
        expected_width = 24
        expected_columns = {
            "SKU": "sku",
            "EN-Name": "name_en",
            "EN-Description": "desc_en",
            "FR-Name": "name_fr",
            "FR-Description": "desc_fr",
            "PriceCAD": "price_cad",
            "PriceUSD": "price_usd",
            "Can Rental": "rental_can",
            "US Rental": "rental_usd",
            "Store Image": "store_image",
            "Store Title": "store_title",
            "Store Description": "store_desc",
            "Publish_CA": "publish_can",
            "Publish_USA": "publish_usa",
            "Can_Be_Sold": "can_be_sold",
            "Can_Be_Rented": "can_be_rented",
            "isSoftware": "is_software",
            "Type": "type",
            "ProductCategory": "category",
            "Product Type": "product_type",
            "ECOM-FOLDER": "folder",
            "ECOM-MEDIA": "media",
            "Valid": "valid",
            "Continue": "continue",
        }

        sheet_width = len(self.sheet[1]) if len(self.sheet) > 1 else 0
        sheet_columns = self.sheet[0] if len(self.sheet) > 0 else []
        
        # variables that will contain a list of any missing or extra columns in the sheet
        missing_columns = [header for header in expected_columns.keys() if header not in sheet_columns]
        extra_columns = [header for header in sheet_columns if header not in expected_columns]
        
        # initialize list of warnings/errors for report
        sync_report = []
        
        # verify that sheet format is as expected
        if sheet_width != expected_width:
            error_msg = f"Sheet width mismatch. Expected: {expected_width}, Actual: {sheet_width}."
            _logger.error(f"syncPricelist: {error_msg}")
            self.add_to_report("ERROR", f"{error_msg}")
            return True, error_msg
        elif missing_columns:
            error_msg = f"Missing columns: {missing_columns}."
            _logger.error(f"syncPricelist: {error_msg}")
            self.add_to_report("ERROR", f"{error_msg}")
            return True, error_msg
        elif extra_columns:
            error_msg = f"Extra columns: {extra_columns}."
            _logger.error(f"syncPricelist: {error_msg}")
            self.add_to_report("ERROR", f"{error_msg}")
            return True, error_msg
        
        _logger.info("syncPricelist: Sheet validated. Proceeding with Pricelist synchronization.")

        return False, "syncCCP: CCP synchronization completed successfully."








# SKIP_NO_CHANGE = True


# class sync_pricelist:
#     def __init__(self, name, sheet, database):
#         self.name = name
#         self.sheet = sheet
#         self.database = database


#     ##################################################
#     def syncPricelist(self):
#         # Confirm GS Tab is in the correct Format
#         sheetWidth = 34
#         # pricelistHeaderDict["ProductCategory"] = "productCategory"
#         columns = dict()
#         columnsMissing = False
#         msg = ""
#         i = 1
        
#         # Debugging: Starting the header check process
#         _logger.debug("PRICELIST.PY: Initializing header dictionary for pricelist sync.")

#         # Check if the header match the appropriate format
#         pricelistHeaderDict = dict()
#         pricelistHeaderDict["SKU"]              = "sku"         
#         pricelistHeaderDict["EN-Name"]          = "eName"       
#         pricelistHeaderDict["EN-Description"]   = "eDisc"           # Optionnal     
#         pricelistHeaderDict["FR-Name"]          = "fName"       
#         pricelistHeaderDict["FR-Description"]   = "fDisc"            # Optionnal 
#         pricelistHeaderDict["isSoftware"]       = "isSoftware"  
#         pricelistHeaderDict["Type"]             = "type"        
#         pricelistHeaderDict["ProductCategory"]  = "productCategory"
#         pricelistHeaderDict["PriceCAD"]         = "cadSale"     
#         pricelistHeaderDict["PriceUSD"]         = "usdSale"     
#         pricelistHeaderDict["Can Rental"]       = "cadRental"   
#         pricelistHeaderDict["US Rental"]        = "usdRental"   
#         pricelistHeaderDict["Publish_CA"]       = "canPublish"  
#         pricelistHeaderDict["Publish_USA"]      = "usPublish"   
#         pricelistHeaderDict["Can_Be_Sold"]      = "canBeSold"   
#         pricelistHeaderDict["Can_Be_Rented"]    = "canBeRented" 
#         pricelistHeaderDict["E-Commerce_Website_Code"] = "ecommerceWebsiteCode" # E-Commerce
#         pricelistHeaderDict["CAN PL ID"]        = "canPLID"         # E-Commerce
#         pricelistHeaderDict["US PL ID"]         = "usPLID"          # E-Commerce
#         pricelistHeaderDict["CAN R SEL"]        = "canrPricelist"   # E-Commerce
#         pricelistHeaderDict["CAN R ID"]         = "canRID"          # E-Commerce
#         pricelistHeaderDict["US R SEL"]         = "usrPricelist"    # E-Commerce
#         pricelistHeaderDict["US R ID"]          = "usRID"           # E-Commerce
#         pricelistHeaderDict["ECOM-FOLDER"]      = "folder"          # E-Commerce
#         pricelistHeaderDict["ECOM-MEDIA"]       = "media"           # E-Commerce
#         pricelistHeaderDict["Continue"]         = "continue"
#         pricelistHeaderDict["Valid"]            = "valid"     
#         _logger.debug("PRICELIST.PY: Checking sheet header against defined dictionary.")  
#         columns, msg, columnsMissing = utilities.checkSheetHeader(pricelistHeaderDict, self.sheet, self.name)  

#         if len(self.sheet[i]) != sheetWidth or columnsMissing:
#             msg = (
#                 "<h1>Pricelist page Invalid</h1>\n<p>"
#                 + str(self.name)
#                 + " width is: "
#                 + str(len(self.sheet[i]))
#                 + " Expected "
#                 + str(sheetWidth)
#                 + "</p>\n"
#                 + msg
#             )
#             self.database.sendSyncReport(msg)
#             _logger.warning("PRICELIST.PY: Pricelist sheet validation failed. Report sent.")
#             return True, msg

#         # loop through all the rows
#         _logger.debug("PRICELIST.PY: Starting row processing.")
#         while True:
#             # check if should continue
#             if (
#                 i == len(self.sheet)
#                 or str(self.sheet[i][columns["continue"]]) != "TRUE"
#             ):
#                 _logger.debug(f"PRICELIST.PY: Stopping row processing at index {i}.")
#                 break

#             # validation checks
#             if str(self.sheet[i][columns["valid"]]) != "TRUE":
#                 i = i + 1
#                 _logger.debug(f"PRICELIST.PY: Row {i} marked invalid. Skipping.")
#                 continue

#             key = self.sheet[i][columns["sku"]]
#             if not utilities.check_id(str(key)):
#                 _logger.warning(f"PRICELIST.PY: Invalid SKU at row {i}: {key}")
#                 msg = utilities.buildMSG(msg, self.name, key, "Key Error")
#                 i = i + 1
#                 continue

#             if not utilities.check_id(str(self.sheet[i][columns["canPLID"]])):
#                 _logger.warning(f"PRICELIST.PY: Invalid Canada Pricelist ID at row {i}.")
#                 msg = utilities.buildMSG(
#                     msg, self.name, key, "Canada Pricelist ID Invalid"
#                 )
#                 i = i + 1
#                 continue

#             if not utilities.check_id(str(self.sheet[i][columns["usPLID"]])):
#                 _logger.warning(f"PRICELIST.PY: Invalid US Pricelist ID at row {i}.")
#                 msg = utilities.buildMSG(msg, self.name, key, "US Pricelist ID Invalid")
#                 i = i + 1
#                 continue

#             if not utilities.check_price(self.sheet[i][columns["cadSale"]]):
#                 _logger.warning(f"PRICELIST.PY: Invalid Canada price at row {i}.")
#                 msg = utilities.buildMSG(msg, self.name, key, "Canada Price Invalid")
#                 i = i + 1
#                 continue

#             if not utilities.check_price(self.sheet[i][columns["usdSale"]]):
#                 _logger.warning(f"PRICELIST.PY: Invalid US price at row {i}.")
#                 msg = utilities.buildMSG(msg, self.name, key, "US Price Invalid")
#                 i = i + 1
#                 continue

#             # if it gets here data should be valid
#             try:
#                 # Debugging: Creating or fetching product record
#                 _logger.debug(f"PRICELIST.PY: Processing SKU {key} at row {i}.")
#                 product, new = self.pricelistProduct(sheetWidth, i, columns)
#                 if product.stringRep == str(self.sheet[i][:]) and SKIP_NO_CHANGE:
#                     _logger.debug(f"PRICELIST.PY: No changes for product {key} at row {i}. Skipping.")
#                     i = i + 1
#                     continue
#                 # Add Prices to the 4 pricelists
#                 self.pricelist(product, "cadSale", "🇨🇦", i, columns)
#                 self.pricelist(product, "cadRental", "CAD RENTAL", i, columns)
#                 self.pricelist(product, "usdSale", "🇺🇸", i, columns)
#                 self.pricelist(product, "usdRental", "USD RENTAL", i, columns)

#                 if new:
#                     # _loggerPRICELIST.PY: Setting stringRep for new product {key}.")
#                     product.stringRep = ""
#                 else:
#                     product.stringRep = str(self.sheet[i][:])
#             except Exception as e:
#                 _logger.error(f"PRICELIST.PY: Exception at row {i} for SKU {key}: {str(e)}", exc_info=True)
#                 msg = utilities.buildMSG(msg, self.name, key, str(e))
#                 return True, msg                   

#             i = i + 1           
#         _logger.info("PRICELIST.PY: Row processing completed successfully.")
#         return False, msg

#     def pricelistProduct(self, sheetWidth, i, columns):
#         # attempts to access existing item (item/row)
#         external_id = str(self.sheet[i][columns["sku"]])
#         product_ids = self.database.env["ir.model.data"].search(
#             [("name", "=", external_id), ("model", "=", "product.template")]
#         )
#         if len(product_ids) > 0:
#             return (
#                 self.updatePricelistProducts(
#                     self.database.env["product.template"].browse(product_ids[len(product_ids) - 1].res_id),
#                     i,
#                     columns,
#                 ),
#                 False,
#             )
#         else:
#             product = self.createPricelistProducts(
#                 external_id,
#                 self.sheet[i][columns["eName"]]
#             )
#             product = self.updatePricelistProducts(product, i, columns)
#             return product, True

#     def pricelist(self, product, priceName, pricelistName, i, columns):
#         # Adds price to given pricelist
#         price = self.sheet[i][columns[priceName]]
#         product_sync_common.addProductToPricelist(
#             self.database, product, pricelistName, price
#         )

#     def updatePricelistProducts(self, product, i, columns):
#         # check if any update to item is needed and skips if there is none
#         if (
#             product.stringRep == str(self.sheet[i][:])
#             and product.stringRep != ""
#             and SKIP_NO_CHANGE
#         ):
#             return product

#         # reads values and puts them in appropriate fields
#         product.name = self.sheet[i][columns["eName"]]
#         product.description_sale = self.sheet[i][columns["eDisc"]]

#         product.ecom_folder = self.sheet[i][columns["folder"]]
#         product.ecom_media = self.sheet[i][columns["media"]].upper()

#         if str(self.sheet[i][columns["isSoftware"]]) == "TRUE":
#             product.is_software = True
#         else:
#             product.is_software = False

#         if (
#             str(self.sheet[i][columns["cadSale"]]) != " "
#             and str(self.sheet[i][columns["cadSale"]]) != ""
#         ):
#             product.list_price = self.sheet[i][columns["cadSale"]]
#             product.cadVal = self.sheet[i][columns["cadSale"]]

#         if (
#             str(self.sheet[i][columns["usdSale"]]) != " "
#             and str(self.sheet[i][columns["usdSale"]]) != ""
#         ):
#             product.usdVal = self.sheet[i][columns["usdSale"]]

#         if str(self.sheet[i][columns["canPublish"]]) == "TRUE":
#             product.is_published = True
#         else:
#             product.is_published = False
            
#         if str(self.sheet[i][columns["canPublish"]]) == "TRUE":
#             product.is_ca = True
#         else:
#             product.is_ca = False

#         if str(self.sheet[i][columns["usPublish"]]) == "TRUE":
#             product.is_us = True
#         else:
#             product.is_us = False

#         if str(self.sheet[i][columns["canBeSold"]]) == "TRUE":
#             product.sale_ok = True
#         else:
#             product.sale_ok = False
            
#         if str(self.sheet[i][columns["canBeRented"]]) == "TRUE":
#             product.rent_ok = True
#         else:
#             product.rent_ok = False
#         # Product Category
#         catId = self.getProductCategoryId(str(self.sheet[i][columns["productCategory"]]))
#         product.categ_id = catId

#         product.active = True

#         product.storeCode = self.sheet[i][columns["ecommerceWebsiteCode"]]
#         product.type = "product"

#         # Add translations to record
#         product_sync_common.translatePricelist(
#             self.database,
#             product,
#             self.sheet[i][columns["fName"]],
#             self.sheet[i][columns["fDisc"]],
#             "fr_CA",
#         )
#         product_sync_common.translatePricelist(
#             self.database,
#             product,
#             self.sheet[i][columns["eName"]],
#             self.sheet[i][columns["eDisc"]],
#             "en_US",
#         )
#         if str(self.sheet[i][columns["type"]]) == "H":
#             product.type_selection = "H"
#         elif str(self.sheet[i][columns["type"]]) == "S":
#             product.type_selection = "S"
#         elif str(self.sheet[i][columns["type"]]) == "SS":
#             product.type_selection = "SS"
#         elif str(self.sheet[i][columns["type"]]) == "":
#             product.type_selection = False
#         return product

#     def getProductCategoryId(self, category):
#         categoryID = self.database.env["product.category"].search([("name", "=", category)])
#         if (len(categoryID) == 1):
#             return categoryID.id
#         else:
#             return self.database.env["product.category"].search([("name", "=", "All")]).id
        
#     # creates record and updates it
#     def createPricelistProducts(self, external_id, product_name):
#         ext = self.database.env["ir.model.data"].create(
#             {"name": external_id, "model": "product.template"}
#         )[0]
        
#         company_id = self.env.company.id
        
#         product = self.database.env["product.template"].create({"name": product_name, "company_id": company_id,})[0]
#         ext.res_id = product.id

#         product.tracking = "serial"

#         return product