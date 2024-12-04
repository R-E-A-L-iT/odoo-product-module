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
                    self.updateCCP(ccp_ids[-1].res_id, row, sheet_columns, row_index)
                else:
                    _logger.info("syncCCP: Row %d: EID/SN '%s' not found in Odoo. Calling createCCP.", row_index, eidsn)
                    self.createCCP(eidsn, row, sheet_columns, row_index)
            
            except Exception as e:
                _logger.error("syncCCP: Error occurred while processing row %d: %s", row_index, str(e), exc_info=True)
        
        return False, "syncCCP: CCP synchronization completed successfully."
    
    
    
    # this function is called to update a ccp that already exists
    # it will attempt to update the ccp cell by cell, and skip updating any info that generates errors
    # fields that are not updated will be added to a report at the end
    # note that if the expiration date is "false" or blank, it will not be added to the report, as this is a very common bug and intended to be overlooked
    def updateCCP(self, ccp_id, row, sheet_columns, row_index):
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
    def createCCP(self, eidsn, row, sheet_columns, row_index):
        _logger.info("createCCP: Creating new CCP item with EID/SN '%s'.", eidsn)
        
        # map the google sheets cells to odoo fields
        field_mapping = {
            "EID/SN": "name",
            "Product Code": "sku",
            "Product Name": "product_id",
            "Publish": "publish",
            "Expiration Date": "expire",
            "Owner ID": "owner",
        }
        
        # empty dict for all data to write
        # company_id is a required field, 1 is id of R-E-A-L.iT parent company
        new_ccp_values = {"company_id": 1}
        
        # mandatory check, product_id is required field
        product_exists = False

        # loop through cells and collect relevant values
        for column_name, odoo_field in field_mapping.items():
            try:
                if column_name in sheet_columns:
                    
                    # get value from cell in sheet
                    column_index = sheet_columns.index(column_name)
                    sheet_value = str(row[column_index]).strip()

                    # normalize booleans
                    if odoo_field in ["publish", "expire"]:
                        normalized_value = self.normalize_bools(odoo_field, sheet_value)
                        
                    # normalize date
                    elif odoo_field == "expire":
                        normalized_value = self.normalize_date(sheet_value)
                        
                    # get product id
                    elif odoo_field == "product_id":
                        product_code_column = sheet_columns.index("Product Code")
                        product_code = str(row[product_code_column]).strip()
                        product = self.database.env["product.product"].search(
                            [("sku", "=", product_code)], limit=1
                        )
                        
                        if not product:
                            _logger.error(
                                "createCCP: Row %d: Product with SKU '%s' not found. Creation canceled.",
                                row_index, product_code
                            )
                            continue
                        
                        normalized_value = product.id
                        product_exists = True
                        
                    # get company id
                    elif odoo_field == "owner":
                        owner = self.database.env["res.partner"].search(
                            [("company_nickname", "=", sheet_value.strip())], limit=1
                        )
                        
                        if not owner:
                            _logger.warning(
                                "createCCP: Row %d: Owner with nickname '%s' not found. Skipping owner field.",
                                row_index, sheet_value
                            )
                            continue
                        
                        normalized_value = owner.id
                        
                    else:
                        normalized_value = sheet_value

                    # log value being gathered
                    _logger.info(
                        "createCCP: Gathering field '%s' for new CCP. Value: '%s'.",
                        odoo_field, normalized_value
                    )

                    # add value to dict
                    new_ccp_values[odoo_field] = normalized_value

            except Exception as e:
                _logger.error(
                    "createCCP: Error while processing field '%s' for new CCP: %s",
                    column_name, str(e), exc_info=True
                )
        
        # log data for debugging
        _logger.info("createCCP: Data gathered for new CCP: %s", new_ccp_values)

        # create new record
        if product_exists:
            try:
                self.database.env.cr.execute("SAVEPOINT create_ccp_savepoint")
                new_ccp = self.database.env["stock.lot"].create(new_ccp_values)
                self.database.env.cr.execute("RELEASE SAVEPOINT create_ccp_savepoint")
                _logger.info("createCCP: Successfully created new CCP item with ID: %s", new_ccp.id)
            except Exception as e:
                self.database.env.cr.execute("ROLLBACK TO SAVEPOINT create_ccp_savepoint")
                _logger.error("createCCP: Error while creating new CCP item: %s", str(e), exc_info=True)
        else:
            return