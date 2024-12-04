# -*- coding: utf-8 -*-

from .utilities import utilities
from datetime import datetime, date, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo.tools.translate import _
from odoo import models

_logger = logging.getLogger(__name__)

class sync_ccp:
    
    def __init__(self, name, sheet, database):
        self.name = name
        self.sheet = sheet
        self.database = database
        
        
        
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
    def syncCCP(self):
        _logger.info("syncCCP: Starting synchronization process for ccp")
        
        # variables to verify format
        # if you need to add more columns for new sync data, add them here
        expected_width = 11
        expected_columns = {
            "Owner ID": "ownerId",
            "EID/SN": "eidsn",
            "External ID": "externalId",
            "Product Code": "code",
            "Sheet Source": "source",
            "Product Name": "name",
            "Publish": "publish",
            "Expiration Date": "date",
            "Valid": "valid",
            "Date Valid": "date_valid",
            "Continue": "continue",
        }
        
        sheet_width = len(self.sheet[1]) if len(self.sheet) > 1 else 0
        sheet_columns = self.sheet[0] if len(self.sheet) > 0 else []
        
        # variables that will contain a list of any missing or extra columns in the sheet
        missing_columns = [header for header in expected_columns.keys() if header not in sheet_columns]
        extra_columns = [header for header in sheet_columns if header not in expected_columns]
        
        # verify that sheet format is as expected
        if sheet_width != expected_width:
            _logger.error("syncCCP: Sheet invalid. The sheet width does not match the expected number. Expected: %s, Actual: %s", expected_width, sheet_width)
            return True, f"Sheet width mismatch. Expected: {expected_width}, Actual: {sheet_width}."
        elif missing_columns:
            _logger.error("syncCCP: Sheet invalid. The following columns are missing: %s", missing_columns)
            return True, f"Missing columns: {missing_columns}."
        elif extra_columns:
            _logger.error("syncCCP: Sheet invalid. The following columns are extras: %s", extra_columns)
            return True, f"Extra columns: {extra_columns}."
        
        _logger.info("syncCCP: Sheet validated. Proceeding with CCP synchronization.")
        
        # start processing rows beginning at second row
        for row_index, row in enumerate(self.sheet[1:], start=2):
            try:
                
                # only proceed if the value for continue is marked as true
                continue_column = sheet_columns.index("Continue")
                should_continue = str(row[continue_column]).strip().lower() == "true"
                
                if not should_continue:
                    _logger.info("syncCCP: Row %d: Continue is set to false. Stopping the sync here.", row_index)
                    break
                
                
                # only proceed if the row is marked as valid
                valid_column = sheet_columns.index("Valid")
                valid = str(row[valid_column]).strip().lower() == "true"
                
                if not valid:
                    _logger.info("syncCCP: Row %d: Marked as invalid. Skipping.", row_index)
                    continue
                
                
                # get eid/sn and check if it exists in odoo
                eidsn_column = sheet_columns.index("EID/SN")
                eidsn = str(row[eidsn_column]).strip()
                
                if not eidsn:
                    _logger.warning("syncCCP: Row %d: Missing EID/SN. Skipping.", row_index)
                    continue
                
                
                # check if the eid/sn already exists in odoo
                ccp_ids = self.database.env["ir.model.data"].search(
                    [("name", "=", eidsn), ("model", "=", "stock.lot")]
                )
                
                if ccp_ids:
                    _logger.info("syncCCP: Row %d: EID/SN '%s' found in Odoo. Calling updateCCP.", row_index, eidsn)
                    self.updateCCP(ccp_ids[-1].res_id, row, sheet_columns)
                else:
                    _logger.info("syncCCP: Row %d: EID/SN '%s' not found in Odoo. Calling createCCP.", row_index, eidsn)
                    self.createCCP(eidsn, row, sheet_columns)
            
            except Exception as e:
                _logger.error("syncCCP: Error occurred while processing row %d: %s", row_index, str(e), exc_info=True)
        
        return False, "syncCCP: CCP synchronization completed successfully."
    
    
    
    # this function is called to update a ccp that already exists
    # it will attempt to update the ccp cell by cell, and skip updating any info that generates errors
    # fields that are not updated will be added to a report at the end
    # note that if the expiration date is "false" or blank, it will not be added to the report, as this is a very common bug and intended to be overlooked
    def updateCCP(self, ccp_id, row, sheet_columns):
        _logger.info("updateCCP: Searching for any changes for CCP item: %s.", ccp_id)

        ccp = self.database.env["stock.lot"].browse(ccp_id)
        
        # map the google sheets cells to odoo fields
        field_mapping = {
            "EID/SN": "name",
            "Product Code": "sku",
            "Product Name": "product_id",
            "Publish": "publish",
            "Expiration Date": "expire",
            "Owner ID": "owner",
        }
        
        for column_name, odoo_field in field_mapping.items():
            try:
                if column_name in sheet_columns:
                    
                    # get new sheets value
                    column_index = sheet_columns.index(column_name)
                    sheet_value = str(row[column_index]).strip()
                    sheet_value_normalized = self.normalize_bools(odoo_field, sheet_value)

                    # handle special cases for specific fields
                    if odoo_field == "product_id":
                        
                        # find product by sku in odoo
                        product_code_column = sheet_columns.index("Product Code")
                        product_code = str(row[product_code_column]).strip()
                        product = self.database.env["product.product"].search(
                            [("sku", "=", product_code)], limit=1
                        )
                        
                        # stop if not found
                        if not product:
                            _logger.warning(
                                "updateCCP: Row %d: Product with SKU '%s' not found. Skipping product_id update.",
                                row.index(row) + 1, product_code
                            )
                            continue
                        
                        # update if found
                        if ccp.product_id.id != product.id:
                            _logger.info(
                                "updateCCP: Field 'product_id' changed for CCP ID %s. Old Value: '%s', New Value: '%s'.",
                                ccp_id, ccp.product_id.name if ccp.product_id else None, product.name
                            )
                            ccp.product_id = product.id

                    elif odoo_field == "owner":
                        
                        owner_column_index = sheet_columns.index("Owner ID")
                        owner_nickname = str(row[owner_column_index]).strip()
                        
                        # find company owner in odoo
                        owner = self.database.env["res.partner"].search(
                            [("company_nickname", "=", owner_nickname)], limit=1
                        )
                        
                        # stop if not found
                        if not owner:
                            _logger.warning(
                                "updateCCP: Row %d: Owner with nickname '%s' not found. Skipping owner update.",
                                row_index, owner_nickname
                            )
                            continue
                        
                        # update if found
                        if ccp.owner.id != owner.id:
                            _logger.info(
                                "updateCCP: Field 'owner' changed for CCP ID %s. Old Value: '%s', New Value: '%s'.",
                                ccp_id, ccp.owner.name if ccp.owner else None, owner.name
                            )
                            ccp.owner = owner.id

                    # directly update sku (char field in odoo)
                    elif odoo_field == "sku":
                        if ccp.sku != sheet_value:
                            _logger.info(
                                "updateCCP: Field 'sku' changed for CCP ID %s. Old Value: '%s', New Value: '%s'.",
                                ccp_id, ccp.sku, sheet_value
                            )
                            ccp.sku = sheet_value
                            
                    # normalize and update expiration date
                    elif odoo_field == "expire":
                        
                        # normalize both values (different data types)
                        normalized_sheet_value = self.normalize_date(sheet_value)
                        normalized_odoo_value = self.normalize_date(ccp.expire or "")

                        # comprare normalized values
                        if normalized_odoo_value != normalized_sheet_value:
                            _logger.info(
                                "updateCCP: Field 'expire' changed for CCP ID %s. Old Value: '%s', New Value: '%s'.",
                                ccp_id, normalized_odoo_value, normalized_sheet_value
                            )
                            ccp.expire = normalized_sheet_value


                    # handle any other fields by updating directly 
                    # if you add fields to update that are not char fields in odoo, add a new elif statement to handle it properly before this
                    else:
                        odoo_value = ccp[odoo_field]
                        
                        # normalize
                        if isinstance(odoo_value, models.Model):
                            odoo_value = odoo_value.id
                        odoo_value_normalized = self.normalize_bools(odoo_field, str(odoo_value).strip() if odoo_value else "")

                        # compare, log, and update
                        if odoo_value_normalized != sheet_value_normalized:
                            _logger.info(
                                "updateCCP: Field '%s' changed for CCP ID %s. Old Value: '%s', New Value: '%s'.",
                                odoo_field, ccp_id, odoo_value, sheet_value
                            )
                            ccp[odoo_field] = sheet_value_normalized if sheet_value_normalized else False

            except Exception as e:
                _logger.error(
                    "updateCCP: Error while updating field '%s' for CCP ID %s: %s",
                    odoo_field, ccp_id, str(e), exc_info=True
                )


    # this function is called to create a new ccp if the eid is not recognized
    # it will attempt to create the ccp cell by cell, and skip creating any info that generates errors
    # fields that are not updated will be added to a report at the end
    # note that if the expiration date is "false" or blank, it will not be added to the report, as this is a very common bug and intended to be overlooked
    def createCCP(self, eidsn, row, sheet_columns):
        _logger.info("createCCP: Creating new CCP item with EID/SN '%s'.", eidsn)
        
                
        
        
        
        

# SKIP_NO_CHANGE = True


# class sync_ccp:
#     def __init__(self, name, sheet, database):
#         self.name = name
#         self.sheet = sheet
#         self.database = database

#     def syncCCP(self):
#         _logger.info("CCP.PY: Starting CCP synchronization.")
#         skipped_items = []  # List to store skipped rows and errors

#         # Confirm GS Tab is in the correct Format
#         sheetWidth = 11
#         columns = dict()
#         columnsMissing = False
#         msg = ""
#         i = 1

#         # Check if the header matches the expected format
#         ccpHeaderDict = dict()
#         ccpHeaderDict["Owner ID"] = "ownerId"
#         ccpHeaderDict["EID/SN"] = "eidsn"
#         ccpHeaderDict["External ID"] = "externalId"
#         ccpHeaderDict["Product Code"] = "code"
#         ccpHeaderDict["Product Name"] = "name"
#         ccpHeaderDict["Publish"] = "publish"
#         ccpHeaderDict["Expiration Date"] = "date"
#         ccpHeaderDict["Valid"] = "valid"
#         ccpHeaderDict["Continue"] = "continue"
#         columns, msg, columnsMissing = utilities.checkSheetHeader(ccpHeaderDict, self.sheet, self.name)

#         if len(self.sheet[i]) != sheetWidth or columnsMissing:
#             msg = (
#                 "<h1>CCP page Invalid</h1>\n<p>"
#                 + str(self.name)
#                 + " width is: "
#                 + str(len(self.sheet[i]))
#                 + " Expected "
#                 + str(sheetWidth)
#                 + "</p>\n"
#                 + msg
#             )
#             self.database.sendSyncReport(msg)
#             _logger.warning(f"CCP.PY: Sheet header validation failed. {msg}")
#             return True, msg

#         # Loop through rows in Google Sheets
#         _logger.info("CCP.PY: Starting row processing.")
#         while True:
#             if i == len(self.sheet) or str(self.sheet[i][columns["continue"]]) != "TRUE":
#                 _logger.info(f"CCP.PY: Stopping processing at row {i}.")
#                 break

#             try:
#                 # Process the row
#                 external_id = str(self.sheet[i][columns["externalId"]])
#                 expiration_date = str(self.sheet[i][columns["date"]])

#                 # Validate expiration date
#                 if expiration_date in ["", "FALSE"]:
#                     _logger.warning(f"Row {i}: Expiration date is either empty or marked as 'FALSE'. Skipping expiration update.")
#                     expiration_date = None

#                 # Validate External ID
#                 if not utilities.check_id(external_id):
#                     raise ValueError(f"Invalid External ID at row {i}.")

#                 # Search for the CCP item
#                 ccp_ids = self.database.env["ir.model.data"].search(
#                     [("name", "=", external_id), ("model", "=", "stock.lot")]
#                 )

#                 if ccp_ids:
#                     self.updateCCP(
#                         self.database.env["stock.lot"].browse(ccp_ids[-1].res_id),
#                         i,
#                         columns
#                     )
#                 else:
#                     self.createCCP(external_id, i, columns)

#             except Exception as e:
#                 # Rollback the transaction on error
#                 self.database.env.cr.rollback()
#                 error_message = f"CCP.PY: Error occurred at row {i}: {str(e)}"
#                 _logger.error(error_message, exc_info=True)

#                 # Log the skipped item
#                 skipped_items.append({
#                     "row": i,
#                     "externalId": str(self.sheet[i][columns["externalId"]]),
#                     "error": str(e)
#                 })

#             i += 1

#         # Compile skipped items report
#         if skipped_items:
#             try:
#                 report = "\n".join(
#                     [f"Row {item['row']}: External ID {item['externalId']} - Error: {item['error']}" for item in skipped_items]
#                 )
#                 _logger.warning(f"CCP.PY: Skipped items report:\n{report}")
#                 self.database.sendSyncReport(f"<h1>Skipped Items Report</h1><pre>{report}</pre>")
#             except Exception as e:
#                 _logger.error(f"Failed to send skipped items report: {str(e)}", exc_info=True)

#         _logger.info("CCP.PY: CCP synchronization completed successfully.")
#         return False, ""



#     # def updateCCP(self, ccp_item, i, columns):
#     #     _logger.debug("Updating CCP item: %s at row %d", ccp_item, i)
#     #     if ccp_item.stringRep == str(self.sheet[i][:]):
#     #         _logger.info("No changes detected for row %d. Skipping update.", i)
#     #         _logger.info("Skipping becuase no changes detected. stringRep for row %d: Existing: %s | New: %s", i, ccp_item.stringRep, str(self.sheet[i][:]))
#     #         return

#     #     ccp_item.name = self.sheet[i][columns["eidsn"]]

#     #     product_ids = self.database.env["product.product"].search(
#     #         [("sku", "=", self.sheet[i][columns["code"]])])
#     #     ccp_item.product_id = product_ids[-1].id if product_ids else None
#     #     _logger.debug("Updated product_id for row %d: %s", i, product_ids[-1].id if product_ids else None)

#     #     partner = self.database.env["res.partner"].search([
#     #         ("company_nickname", "=", self.sheet[i][columns["ownerId"]].strip())
#     #     ], limit=1)

#     #     if not partner:
#     #         _logger.warning("No matching partner found for company_nickname '%s' in row %d.", self.sheet[i][columns["ownerId"]], i)
#     #         ccp_item.owner = None
#     #     else:
#     #         ccp_item.owner = partner.id
#     #         _logger.debug("Updated owner for row %d: %s", i, partner.id)

#     #     if self.sheet[i][columns["date"]] != "FALSE":
#     #         ccp_item.expire = self.sheet[i][columns["date"]]
#     #     else:
#     #         ccp_item.expire = None

#     #     ccp_item.publish = self.sheet[i][columns["publish"]]

#     #     ccp_item.stringRep = str(self.sheet[i][:])
#     #     _logger.info("Successfully updated CCP item at row %d", i)
    
#     def updateCCP(self, ccp_item, i, columns):
#         # Extract relevant fields from the sheet
#         new_representation = {
#             "eidsn": self.sheet[i][columns["eidsn"]],
#             "code": self.sheet[i][columns["code"]],
#             "date": self.sheet[i][columns["date"]],
#             "publish": self.sheet[i][columns["publish"]],
#         }

#         # Extract the current representation from the database
#         current_representation = {
#             "eidsn": ccp_item.name,
#             "code": ccp_item.product_id.sku if ccp_item.product_id else None,
#             "date": ccp_item.expire,
#             "publish": ccp_item.publish,
#         }

#         # Log detailed comparisons
#         _logger.info("Comparing stringRep for row %d: Current: %s | New: %s", i, current_representation, new_representation)

#         # Check for changes in relevant fields except date
#         if (
#             current_representation["eidsn"] == new_representation["eidsn"]
#             and current_representation["code"] == new_representation["code"]
#             and current_representation["publish"] == new_representation["publish"]
#         ):
#             # Validate the date separately to avoid skipping other updates
#             if (
#                 utilities.check_date(new_representation["date"])
#                 and current_representation["date"] == new_representation["date"]
#             ):
#                 _logger.info("No changes detected for row %d. Skipping update.", i)
#                 return

#         # Update the CCP item
#         _logger.info("Changes detected for row %d. Updating CCP item.", i)
#         ccp_item.name = new_representation["eidsn"]

#         product_ids = self.database.env["product.product"].search(
#             [("sku", "=", new_representation["code"])]
#         )

#         if product_ids:
#             ccp_item.write({"product_id": product_ids[-1].id if product_ids else None})
#             _logger.info(
#                 "product_id updated using write() for SKU '%s' at row %d.",
#                 new_representation["code"],
#                 i
#             )

#             # _logger.info(
#             #     "Product found for SKU '%s' at row %d. Setting product_id to %d.",
#             #     new_representation["code"],
#             #     i,
#             #     product_ids[-1].id
#             # )
#         else:
#             ccp_item.product_id = None
#             _logger.warning(
#                 "No product found for SKU '%s' at row %d. product_id is set to None.",
#                 new_representation["code"],
#                 i
#             )


#         # Only update the expiration date if it is valid
#         if utilities.check_date(new_representation["date"]):
#             ccp_item.expire = new_representation["date"]
#             _logger.info("Expiration date updated for row %d to '%s'.", i, new_representation["date"])
#         else:
#             _logger.warning("Invalid expiration date '%s' for row %d. Skipping expiration date update.", new_representation["date"], i)

#         ccp_item.publish = new_representation["publish"]

#         # Update stringRep for the next comparison
#         ccp_item.stringRep = str(new_representation)
#         _logger.info("Updated CCP item: %s", ccp_item.name)



#     def createCCP(self, external_id, i, columns):
#         _logger.info("createCCP: Creating new CCP record for external ID: %s at row %d", external_id, i)
        
#         module_name = "sync"  # Default module name to avoid empty values

#         # Check for existing `ir.model.data` record
#         ext = self.database.env["ir.model.data"].search(
#             [("name", "=", external_id), ("model", "=", "stock.lot"), ("module", "=", module_name)], limit=1
#         )

#         if not ext:
#             # Create a new `ir.model.data` record if it doesn't exist
#             ext = self.database.env["ir.model.data"].create({
#                 "name": external_id,
#                 "model": "stock.lot",
#                 "module": module_name,  # Ensure the module is populated
#             })
#             _logger.info("createCCP: Created new ir.model.data entry for external ID: %s", external_id)
#         else:
#             _logger.warning("createCCP: Duplicate ir.model.data entry found for external ID: %s. Reusing existing record.", external_id)

#         # Create the CCP record
#         product_ids = self.database.env["product.product"].search([("sku", "=", self.sheet[i][columns["code"]])])
#         product_id = product_ids[-1].id if product_ids else None
#         company_id = self.database.env["res.company"].search([("id", "=", 1)]).id

#         ccp_item = self.database.env["stock.lot"].create({
#             "name": self.sheet[i][columns["eidsn"]],
#             "product_id": product_id,
#             "company_id": company_id,
#         })

#         # Link the `ir.model.data` record to the new CCP item
#         ext.res_id = ccp_item.id

#         _logger.info("createCCP: New CCP record created for external ID: %s at row %d", external_id, i)
#         self.updateCCP(ccp_item, i, columns)

