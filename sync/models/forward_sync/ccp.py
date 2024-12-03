# -*- coding: utf-8 -*-

from .utilities import utilities
from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo.tools.translate import _
from odoo import models

_logger = logging.getLogger(__name__)

SKIP_NO_CHANGE = True


class sync_ccp:
    def __init__(self, name, sheet, database):
        self.name = name
        self.sheet = sheet
        self.database = database

    def syncCCP(self):
        _logger.debug("CCP.PY: Starting CCP synchronization.")
        skipped_items = []  # List to store skipped rows and errors

        # Confirm GS Tab is in the correct Format
        sheetWidth = 11
        columns = dict()
        columnsMissing = False
        msg = ""
        i = 1

        # Check if the header matches the expected format
        ccpHeaderDict = dict()
        ccpHeaderDict["Owner ID"] = "ownerId"
        ccpHeaderDict["EID/SN"] = "eidsn"
        ccpHeaderDict["External ID"] = "externalId"
        ccpHeaderDict["Product Code"] = "code"
        ccpHeaderDict["Product Name"] = "name"
        ccpHeaderDict["Publish"] = "publish"
        ccpHeaderDict["Expiration Date"] = "date"
        ccpHeaderDict["Valid"] = "valid"
        ccpHeaderDict["Continue"] = "continue"
        columns, msg, columnsMissing = utilities.checkSheetHeader(ccpHeaderDict, self.sheet, self.name)

        if len(self.sheet[i]) != sheetWidth or columnsMissing:
            msg = (
                "<h1>CCP page Invalid</h1>\n<p>"
                + str(self.name)
                + " width is: "
                + str(len(self.sheet[i]))
                + " Expected "
                + str(sheetWidth)
                + "</p>\n"
                + msg
            )
            self.database.sendSyncReport(msg)
            _logger.warning(f"CCP.PY: Sheet header validation failed. {msg}")
            return True, msg

        # Loop through rows in Google Sheets
        _logger.debug("CCP.PY: Starting row processing.")
        while True:
            # Check if the process should continue
            if i == len(self.sheet) or str(self.sheet[i][columns["continue"]]) != "TRUE":
                _logger.debug(f"CCP.PY: Stopping processing at row {i}.")
                break

            try:
                # # Validate row fields
                # if str(self.sheet[i][columns["valid"]]) != "TRUE":
                #     raise ValueError(f"Row {i} is not marked as valid.")
                
                # Normalize the date format
                expiration_date = str(self.sheet[i][columns["date"]])

                try:
                    # Attempt to parse and reformat the date to YYYY-MM-DD
                    normalized_date = datetime.strptime(expiration_date, "%Y-%m-%d").strftime("%Y-%m-%d")
                    if not utilities.check_date(normalized_date):
                        _logger.warning("Invalid expiration date at row " + str(i))
                        # raise ValueError(f"Invalid Expiration Date '{expiration_date}' at row {i}.")
                    expiration_date = normalized_date
                except ValueError as e:
                    _logger.warning(f"CCP.PY: Invalid Expiration Date '{expiration_date}' at row {i}. Skipping expiration update.")
                    expiration_date = None  # Skip updating expiration date
                    
                    

                if not utilities.check_id(str(self.sheet[i][columns["externalId"]])):
                    raise ValueError(f"Invalid External ID at row {i}.")

                normalized_date = datetime.strptime(expiration_date, "%Y-%m-%d").strftime("%Y-%m-%d")
                if not utilities.check_date(normalized_date):
                    _logger.warning("Row " + str(i) + ": Skipped a line because the expiration date is invalid ")
                    # raise ValueError(f"Invalid Expiration Date at row {i}.")

                # Process the row
                external_id = str(self.sheet[i][columns["externalId"]])
                ccp_ids = self.database.env["ir.model.data"].search(
                    [("name", "=", external_id), ("model", "=", "stock.lot")]
                )

                if len(ccp_ids) > 0:
                    self.updateCCP(
                        self.database.env["stock.lot"].browse(ccp_ids[-1].res_id),
                        i,
                        columns
                    )
                else:
                    self.createCCP(external_id, i, columns)

            except Exception as e:
                # Log and skip the problematic row
                error_message = f"CCP.PY: Error occurred at row {i}: {str(e)}"
                _logger.error(error_message, exc_info=True)
                skipped_items.append({
                    "row": i,
                    "externalId": str(self.sheet[i][columns["externalId"]]),
                    "error": str(e)
                })

            i += 1

        # Compile skipped items report
        if skipped_items:
            report = "\n".join(
                [f"Row {item['row']}: External ID {item['externalId']} - Error: {item['error']}" for item in skipped_items]
            )
            _logger.warning(f"CCP.PY: Skipped items report:\n{report}")
            self.database.sendSyncReport(f"<h1>Skipped Items Report</h1><pre>{report}</pre>")

        _logger.info("CCP.PY: CCP synchronization completed successfully.")
        return False, ""


    # def updateCCP(self, ccp_item, i, columns):
    #     _logger.debug("Updating CCP item: %s at row %d", ccp_item, i)
    #     if ccp_item.stringRep == str(self.sheet[i][:]):
    #         _logger.info("No changes detected for row %d. Skipping update.", i)
    #         _logger.info("Skipping becuase no changes detected. stringRep for row %d: Existing: %s | New: %s", i, ccp_item.stringRep, str(self.sheet[i][:]))
    #         return

    #     ccp_item.name = self.sheet[i][columns["eidsn"]]

    #     product_ids = self.database.env["product.product"].search(
    #         [("sku", "=", self.sheet[i][columns["code"]])])
    #     ccp_item.product_id = product_ids[-1].id if product_ids else None
    #     _logger.debug("Updated product_id for row %d: %s", i, product_ids[-1].id if product_ids else None)

    #     partner = self.database.env["res.partner"].search([
    #         ("company_nickname", "=", self.sheet[i][columns["ownerId"]].strip())
    #     ], limit=1)

    #     if not partner:
    #         _logger.warning("No matching partner found for company_nickname '%s' in row %d.", self.sheet[i][columns["ownerId"]], i)
    #         ccp_item.owner = None
    #     else:
    #         ccp_item.owner = partner.id
    #         _logger.debug("Updated owner for row %d: %s", i, partner.id)

    #     if self.sheet[i][columns["date"]] != "FALSE":
    #         ccp_item.expire = self.sheet[i][columns["date"]]
    #     else:
    #         ccp_item.expire = None

    #     ccp_item.publish = self.sheet[i][columns["publish"]]

    #     ccp_item.stringRep = str(self.sheet[i][:])
    #     _logger.info("Successfully updated CCP item at row %d", i)
    
    def updateCCP(self, ccp_item, i, columns):
        # Extract relevant fields from the sheet
        new_representation = {
            "eidsn": self.sheet[i][columns["eidsn"]],
            "code": self.sheet[i][columns["code"]],
            "date": self.sheet[i][columns["date"]],
            "publish": self.sheet[i][columns["publish"]],
        }

        # Extract the current representation from the database
        current_representation = {
            "eidsn": ccp_item.name,
            "code": ccp_item.product_id.sku if ccp_item.product_id else None,
            "date": ccp_item.expire,
            "publish": ccp_item.publish,
        }

        # Log detailed comparisons
        _logger.debug("Comparing stringRep for row %d: Current: %s | New: %s", i, current_representation, new_representation)

        # Check for changes in relevant fields except date
        if (
            current_representation["eidsn"] == new_representation["eidsn"]
            and current_representation["code"] == new_representation["code"]
            and current_representation["publish"] == new_representation["publish"]
        ):
            # Validate the date separately to avoid skipping other updates
            if (
                utilities.check_date(new_representation["date"])
                and current_representation["date"] == new_representation["date"]
            ):
                _logger.info("No changes detected for row %d. Skipping update.", i)
                return

        # Update the CCP item
        _logger.info("Changes detected for row %d. Updating CCP item.", i)
        ccp_item.name = new_representation["eidsn"]

        product_ids = self.database.env["product.product"].search(
            [("sku", "=", new_representation["code"])])
        ccp_item.product_id = product_ids[-1].id if product_ids else None

        # Only update the expiration date if it is valid
        if utilities.check_date(new_representation["date"]):
            ccp_item.expire = new_representation["date"]
            _logger.info("Expiration date updated for row %d to '%s'.", i, new_representation["date"])
        else:
            _logger.warning("Invalid expiration date '%s' for row %d. Skipping expiration date update.", new_representation["date"], i)

        ccp_item.publish = new_representation["publish"]

        # Update stringRep for the next comparison
        ccp_item.stringRep = str(new_representation)
        _logger.info("Updated CCP item: %s", ccp_item.name)



    def createCCP(self, external_id, i, columns):
        _logger.debug("Creating new CCP record for external ID: %s at row %d", external_id, i)
        ext = self.database.env["ir.model.data"].create({"name": external_id, "model": "stock.lot"})[0]
        product_ids = self.database.env["product.product"].search([("sku", "=", self.sheet[i][columns["code"]])])
        product_id = product_ids[-1].id if product_ids else None
        company_id = self.database.env["res.company"].search([("id", "=", 1)]).id

        ccp_item = self.database.env["stock.lot"].create({
                "name": self.sheet[i][columns["eidsn"]],
                "product_id": product_id,
                "company_id": company_id,
            })[0]
        ext.res_id = ccp_item.id

        _logger.info("New CCP record created for external ID: %s at row %d", external_id, i)
        self.updateCCP(ccp_item, i, columns)
