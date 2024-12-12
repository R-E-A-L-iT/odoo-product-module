# -*- coding: utf-8 -*-

import base64
import requests

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
    def normalize_bools(self, value):
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



    # this function will be called to start the synchronization process for pricelists.
    # it delegates the function of actually updating or creating the product item to the other two functions
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

        # start processing rows beginning at second row
        for row_index, row in enumerate(self.sheet[1:], start=2):
            try:
                
                # only proceed if the value for continue is marked as true
                continue_column = sheet_columns.index("Continue")
                should_continue = str(row[continue_column]).strip().lower() == "true"
                
                if not should_continue:
                    _logger.info("syncPricelist: Row %d: Continue is set to false. Stopping the sync here.", row_index)
                    break
                
                
                # only proceed if the row is marked as valid
                valid_column = sheet_columns.index("Valid")
                valid = str(row[valid_column]).strip().lower() == "true"
                
                if not valid:
                    warning_msg = f"Row {row_index}: Marked as invalid. Skipping."
                    _logger.info(f"syncPricelist: {warning_msg}")
                    # not sending this to report because intended feature
                    # sync_report.append(f"WARNING: {warning_msg}")
                    continue
    
                
                # get eid/sn and check if it exists in odoo
                sku_column = sheet_columns.index("SKU")
                sku = str(row[sku_column]).strip()
                
                if not sku:
                    warning_msg = f"Row {row_index}: Missing SKU. Skipping."
                    _logger.warning(f"syncPricelist: {warning_msg}")
                    self.add_to_report("WARNING", f"{warning_msg}")
                    continue
                
                existing_product = self.database.env["product.template"].search([("sku", "=", sku)], limit=1)
                
                if existing_product:
                    _logger.info("syncPricelist: Row %d: SKU '%s' found in Odoo. Calling updateProduct.", row_index, sku)
                    self.updateProduct(existing_product.id, row, sheet_columns, row_index)
                else:
                    _logger.info("syncPricelist: Row %d: SKU '%s' not found in Odoo. Calling createProduct.", row_index, sku)
                    self.createProduct(sku, row, sheet_columns, row_index)
            
            except Exception as e:
                error_msg = f"Row {row_index}: Error occurred while processing: {str(e)}"
                _logger.error(f"syncPricelist: {error_msg}", exc_info=True)
                self.add_to_report("ERROR", f"{error_msg}")
                
        if self.sync_report:
            utilities.send_report(self.sync_report, "Pricelist", self.database)

        return True, "syncPricelist: Pricelist synchronization completed successfully."

    # this function is called to update a product that already exists
    # it will attempt to update the product cell by cell, and skip updating any info that generates errors
    # fields that are not updated will be added to a report at the end
    def updateProduct(self, product_id, row, sheet_columns, row_index):
        _logger.info("updateProduct: Searching for any changes for product: %s.", product_id)

        try:
            product = self.database.env["product.template"].browse(product_id)
            
            # map the google sheets cells to odoo fields
            field_mapping = {
                "SKU": "sku",
                "EN-Name": "name",
                "FR-Name": "name",
                "EN-Description": "description_sale",
                "FR-Description": "description_sale",
                "Store Image": "image_1920",
                "PriceCAD": "list_price",
                "PriceUSD": "list_price",
                "Can Rental": "",
                "US Rental": "",
                "Publish_CA": "publish_can",
                "Publish_USA": "publish_usa",
                "Can_Be_Sold": "can_be_sold",
                "Can_Be_Rented": "can_be_rented",
            }

            for column_name, odoo_field in field_mapping.items():
                try:
                    if column_name in sheet_columns:
                        
                        # get new sheets value
                        column_index = sheet_columns.index(column_name)
                        sheet_value = str(row[column_index]).strip()
                        sheet_value_normalized = self.normalize_bools(sheet_value)

                        # update name fields for both languages
                        if column_name in ["EN-Name", "FR-Name"]:
                            
                            name = sheet_value
                            
                            # get lang and normalize odoo name
                            # this is necessary for comparison because odoo adds SKU to beginning of product name
                            lang = "en_US" if column_name == "EN-Name" else "fr_CA"
                            odoo_name = product.with_context(lang=lang).name

                            # compare normalized names and update if necessary
                            if odoo_name != name:
                                _logger.info(
                                    "updateProduct: Field 'name' (%s) changed for Product ID %s. Old Value: '%s', New Value: '%s'.",
                                    "English" if lang == "en_US" else "French", product_id, odoo_name, name
                                )
                                product.with_context(lang=lang).write({"name": name})

                            # double check translation worked
                            updated_name = product.with_context(lang=lang).name
                            if updated_name != name:
                                _logger.error(
                                    "updateProduct: Post-update mismatch for 'name' (%s) on Product ID %s. Expected: '%s', Actual: '%s'.",
                                    "English" if lang == "en_US" else "French", product_id, name, updated_name
                                )
                                self.add_to_report(
                                    "ERROR",
                                    f"Post-update mismatch for 'name' ({'English' if lang == 'en_US' else 'French'}) "
                                    f"on Product ID {product_id}. Expected: '{name}', Actual: '{updated_name}'."
                                )

                        # update description fields for both languages
                        elif column_name in ["EN-Description", "FR-Description"]:
                            
                            # extract description and update
                            lang = "en_US" if column_name == "EN-Description" else "fr_CA"
                            description = sheet_value
                            current_description = product.with_context(lang=lang).description_sale or ""
                            if current_description != description:
                                _logger.info(
                                    "updateProduct: Field 'description_sale' (%s) changed for Product ID %s. Old Value: '%s', New Value: '%s'.",
                                    "English" if lang == "en_US" else "French", product_id, current_description, description
                                )
                                product.with_context(lang=lang).write({"description_sale": description})

                            # double check translation worked
                            updated_description = product.with_context(lang=lang).description_sale or ""
                            if updated_description != description:
                                _logger.error(
                                    "updateProduct: Post-update mismatch for 'description_sale' (%s) on Product ID %s. Expected: '%s', Actual: '%s'.",
                                    "English" if lang == "en_US" else "French", product_id, description, updated_description
                                )
                                self.add_to_report(
                                    "ERROR",
                                    f"Post-update mismatch for 'description_sale' ({'English' if lang == 'en_US' else 'French'}) "
                                    f"on Product ID {product_id}. Expected: '{description}', Actual: '{updated_description}'."
                                )

                        # update price fields for both pricelists
                        elif column_name in ["PriceCAD", "PriceUSD"]:
                            pricelist_name = "🇨🇦" if column_name == "PriceCAD" else "🇺🇸"
                            price = float(sheet_value) if sheet_value else 0.0

                            # default product price is set to cad
                            if pricelist_name == "🇨🇦":
                                product.list_price = price

                            # search for the pricelist
                            pricelist = self.database.env["product.pricelist"].search([("name", "=", pricelist_name)], limit=1)
                            if not pricelist:
                                _logger.error(
                                    "updateProduct: Pricelist '%s' not found for Product ID %s. Skipping price update.",
                                    pricelist_name, product_id
                                )
                                self.add_to_report(
                                    "ERROR",
                                    f"Pricelist '{pricelist_name}' not found for Product ID {product_id}. Skipping price update."
                                )
                                continue

                            # search for existing price within pricelist
                            price_rule = self.database.env["product.pricelist.item"].search([
                                ("pricelist_id", "=", pricelist.id),
                                ("product_tmpl_id", "=", product_id)
                            ], limit=1)

                            if price_rule:

                                # compare and update if necessary
                                if price_rule.fixed_price != price:
                                    _logger.info(
                                        "updateProduct: Updating price for Product ID %s on Pricelist '%s'. Old Value: '%s', New Value: '%s'.",
                                        product_id, pricelist_name, price_rule.fixed_price, price
                                    )
                                    price_rule.write({"fixed_price": price})
                                else:
                                    _logger.info(
                                        "updateProduct: Price for Product ID %s on Pricelist '%s' is unchanged. Value: '%s'.",
                                        product_id, pricelist_name, price
                                    )
                            else:

                                # add price if not already existing
                                _logger.info(
                                    "updateProduct: Creating new price rule for Product ID %s on Pricelist '%s'. Value: '%s'.",
                                    product_id, pricelist_name, price
                                )
                                self.database.env["product.pricelist.item"].create({
                                    "pricelist_id": pricelist.id,
                                    "product_tmpl_id": product_id,
                                    "fixed_price": price,
                                    "applied_on": "0_product_variant",
                                })

                        # update rental prices for both pricelists
                        elif column_name in ["Can Rental", "US Rental"]:
                            pricelist_name = "CAD RENTAL" if column_name == "Can Rental" else "USD RENTAL"
                            rental_price = float(sheet_value) if sheet_value else 0.0

                            # search for the pricelist
                            rental_pricelist = self.database.env["product.pricelist"].search([("name", "=", pricelist_name)], limit=1)
                            if not rental_pricelist:
                                _logger.error(
                                    "updateProduct: Rental pricelist '%s' not found for Product ID %s. Skipping rental price update.",
                                    pricelist_name, product_id
                                )
                                self.add_to_report(
                                    "ERROR",
                                    f"Rental pricelist '{pricelist_name}' not found for Product ID {product_id}. Skipping rental price update."
                                )
                                continue

                            # search for existing price within pricelist
                            rental_price_rule = self.database.env["product.pricelist.item"].search([
                                ("pricelist_id", "=", rental_pricelist.id),
                                ("product_tmpl_id", "=", product_id)
                            ], limit=1)

                            if rental_price_rule:

                                # compare and update if necessary
                                if rental_price_rule.fixed_price != rental_price:
                                    _logger.info(
                                        "updateProduct: Updating rental price for Product ID %s on Rental Pricelist '%s'. Old Value: '%s', New Value: '%s'.",
                                        product_id, pricelist_name, rental_price_rule.fixed_price, rental_price
                                    )
                                    rental_price_rule.write({"fixed_price": rental_price})
                                else:
                                    _logger.info(
                                        "updateProduct: Rental price for Product ID %s on Rental Pricelist '%s' is unchanged. Value: '%s'.",
                                        product_id, pricelist_name, rental_price
                                    )
                            else:

                                # add price if not already existing
                                _logger.info(
                                    "updateProduct: Creating new rental price rule for Product ID %s on Rental Pricelist '%s'. Value: '%s'.",
                                    product_id, pricelist_name, rental_price
                                )
                                self.database.env["product.pricelist.item"].create({
                                    "pricelist_id": rental_pricelist.id,
                                    "product_tmpl_id": product_id,
                                    "fixed_price": rental_price,
                                    "applied_on": "0_product_variant",
                                })


                        # update store image field
                        # only give a warning when failed because most products do not have images
                        elif column_name == "Store Image":
                            image_url = sheet_value.strip()
                            if image_url:
                                try:

                                    # fetch the image from the URL
                                    response = requests.get(image_url, timeout=10)
                                    if response.status_code == 200:
                                        image_data = base64.b64encode(response.content)

                                        # compare existing image data with the new one
                                        existing_image = product.image_1920 or b""
                                        if existing_image != image_data:
                                            _logger.info(
                                                "updateProduct: Updating 'image_1920' for Product ID %s from URL '%s'.",
                                                product_id, image_url
                                            )
                                            product.write({"image_1920": image_data})
                                        else:
                                            _logger.info(
                                                "updateProduct: 'image_1920' for Product ID %s is unchanged. Skipping update.",
                                                product_id
                                            )
                                    else:
                                        _logger.warning(
                                            "updateProduct: Failed to fetch image for Product ID %s from URL '%s'. Status Code: %s.",
                                            product_id, image_url, response.status_code
                                        )
                                        self.add_to_report(
                                            "WARNING",
                                            f"Failed to fetch image for Product ID {product_id} from URL '{image_url}'. Status Code: {response.status_code}."
                                        )
                                except requests.exceptions.RequestException as e:
                                    _logger.error(
                                        "updateProduct: Error fetching image for Product ID %s from URL '%s': %s",
                                        product_id, image_url, str(e), exc_info=True
                                    )
                                    self.add_to_report(
                                        "ERROR",
                                        f"Error fetching image for Product ID {product_id} from URL '{image_url}': {str(e)}"
                                    )
                            else:
                                _logger.info(
                                    "updateProduct: No image URL provided for Product ID %s. Skipping 'image_1920' update.",
                                    product_id
                                )

                        # NOT WORKING
                        # update published status
                        elif column_name in ["Publish_CA", "Publish_USA"]:

                            publish = self.normalize_bools(sheet_value.strip())

                            _logger.info(
                                "updateCCP: Current values for Product %s - is_ca: %s, is_us: %s, is_published: %s",
                                product_id, product.is_ca, product.is_us, product.is_published
                            )
                            
                            if column_name == "Publish_CA":
                                product.is_ca = publish
                                product.is_published = publish

                                if not product.is_ca == publish or product.is_published == publish:
                                    _logger.error("updateCCP: Product %s failed to update is_ca published values. is_ca: %s, expected: %s", product_id, str(product.is_ca), str(publish))
                                else:
                                    _logger.info("updateCCP: Product %s published value for Canada has been set to: %s", product_id, str(publish))

                            elif column_name == "Publish_USA":
                                product.is_us = publish

                                if not product.is_us == publish:
                                    _logger.error("updateCCP: Product %s failed to update is_us published values. is_ca: %s, expected: %s", product_id, str(product.is_ca), str(publish))
                                else:
                                    _logger.info("updateCCP: Product %s published value for America has been set to: %s", product_id, str(publish))



                except Exception as e:
                    _logger.error(
                        "updateProduct: Error while updating field '%s' for Product ID %s: %s",
                        odoo_field, product_id, str(e), exc_info=True
                    )
                    self.add_to_report("ERROR", f"updateProduct: Error while updating field {odoo_field} for Product ID {product_id}: {str(e)}")
            pass

        except Exception as e:
            error_msg = f"Row {row_index}: Error updating Product with SKU {product_id}: {str(e)}"
            _logger.error(f"updateProduct: {error_msg}", exc_info=True)
            self.add_to_report("ERROR", f"{error_msg}")

    # this function is called to create a new product if the sku is not recognized
    # it will attempt to create the product cell by cell, and skip creating any info that generates errors
    # fields that are not updated will be added to a report at the end
    def createProduct(self, product_id, row, sheet_columns, row_index):
        _logger.info("createProduct: Creating new product with SKU: %s.", product_id)









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