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
        # Confirm GS Tab is in the correct Format
        _logger.debug("Starting syncCCP for sheet: %s", self.name)
        sheetWidth = 11
        columns = dict()
        columnsMissing = False
        msg = ""
        i = 1

        # Check if the header matches the appropriate format
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

        _logger.debug("Sheet columns: %s", columns)
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
            _logger.warning("Sheet width mismatch or missing columns. Width: %d, Missing: %s", len(self.sheet[i]), columnsMissing)
            return True, msg

        # Loop through Rows in Google Sheets        
        while True:
            if i >= len(self.sheet):
                _logger.debug("End of sheet reached at row %d.", i)
                break

            # Check if final row was completed
            if str(self.sheet[i][columns["continue"]]) != "TRUE":
                _logger.debug("Stopping sync at row %d due to 'Continue' field.", i)
                break

            # Validate the row
            _logger.debug("Validating row %d: %s", i, self.sheet[i])
            if str(self.sheet[i][columns["valid"]]) != "TRUE":
                _logger.info("Skipping row %d: 'Valid' field is not TRUE.", i)
                i += 1
                continue

            if not utilities.check_id(str(self.sheet[i][columns["externalId"]])):
                _logger.warning("Invalid SKU at row %d: %s", i, self.sheet[i][columns["externalId"]])
                msg = utilities.buildMSG(msg, self.name, "Header", "Invalid SKU")
                i += 1
                continue

            if not utilities.check_date(str(self.sheet[i][columns["date"]])):
                _logger.warning("Invalid Expiration Date at row %d: %s", i, self.sheet[i][columns["date"]])
                msg = utilities.buildMSG(
                    msg,
                    self.name,
                    str(self.sheet[i][columns["externalId"]]),
                    "Invalid Expiration Date: " + str(self.sheet[i][columns["date"]])
                )
                i += 1
                continue

            try:                
                # Create or Update record as needed
                external_id = str(self.sheet[i][columns["externalId"]])
                _logger.debug("Processing external ID: %s at row %d", external_id, i)
                ccp_ids = self.database.env["ir.model.data"].search(
                    [("name", "=", external_id), 
                     ("model", "=", "stock.lot")])
                
                if ccp_ids:
                    _logger.debug("Found existing CCP record for external ID: %s", external_id)
                    self.updateCCP(
                        self.database.env["stock.lot"].browse(ccp_ids[-1].res_id),
                        i,
                        columns)
                else:
                    _logger.debug("No existing CCP record found for external ID: %s. Creating new record.", external_id)
                    self.createCCP(external_id, i, columns)

            except Exception as e:
                _logger.error("Error processing row %d: %s", i, e, exc_info=True)
                msg = utilities.buildMSG(msg, self.name, str(external_id), str(e))
                return True, msg

            i += 1
        return False, msg

    def updateCCP(self, ccp_item, i, columns):
        _logger.debug("Updating CCP item: %s at row %d", ccp_item, i)
        if ccp_item.stringRep == str(self.sheet[i][:]):
            _logger.info("No changes detected for row %d. Skipping update.", i)
            return

        ccp_item.name = self.sheet[i][columns["eidsn"]]

        product_ids = self.database.env["product.product"].search(
            [("sku", "=", self.sheet[i][columns["code"]])])
        ccp_item.product_id = product_ids[-1].id if product_ids else None
        _logger.debug("Updated product_id for row %d: %s", i, product_ids[-1].id if product_ids else None)

        partner = self.database.env["res.partner"].search([
            ("company_nickname", "=", self.sheet[i][columns["ownerId"]].strip())
        ], limit=1)

        if not partner:
            _logger.warning("No matching partner found for company_nickname '%s' in row %d.", self.sheet[i][columns["ownerId"]], i)
            ccp_item.owner = None
        else:
            ccp_item.owner = partner.id
            _logger.debug("Updated owner for row %d: %s", i, partner.id)

        if self.sheet[i][columns["date"]] != "FALSE":
            ccp_item.expire = self.sheet[i][columns["date"]]
        else:
            ccp_item.expire = None

        ccp_item.publish = self.sheet[i][columns["publish"]]

        ccp_item.stringRep = str(self.sheet[i][:])
        _logger.info("Successfully updated CCP item at row %d", i)

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
