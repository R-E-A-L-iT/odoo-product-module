#  -*- coding: utf-8 -*-

import ast
import logging
import json
import re

import requests
import werkzeug.urls
import base64

from odoo.addons.google_account.models.google_service import GOOGLE_TOKEN_ENDPOINT, TIMEOUT
from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import RedirectWarning, AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo.tools.translate import _
from odoo import models, fields, api

from .pricelist import sync_pricelist
from .ccp import sync_ccp
from .googlesheetsAPI import sheetsAPI
from .website import syncWeb
from .product import sync_products
from .company import sync_companies
from .contact import sync_contacts

_logger = logging.getLogger(__name__)


class sync(models.Model):
    _name = "sync.sync"
    _inherit = "sync.sheets"
    DatabaseURL = fields.Char(default="")
    _description = "Sync App"

    ###################################################################
    # STARTING POINT
    def start_sync(self, psw=None):
        _logger.info("Starting Sync")

        # Track sync start and end times
        sync_start_time = fields.Datetime.now()
        sync_end_time = None

        # Initialize sync report details
        overall_status = "success"
        combined_error_report = []
        combined_items_updated = []

        db_name = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        template_id = sheetsAPI.get_master_database_template_id(db_name)
        _logger.info("db_name: " + str(db_name))
        _logger.info("template_id: " + str(template_id))

        line_index = 1
        msg = ""

        # Checks authentication values
        if not self.is_psw_format_good(psw):
            return

        # Get the ODOO_SYNC_DATA tab
        sync_data = self.getMasterDatabaseSheet(template_id, psw, self._odoo_sync_data_index)

        # Loop through entries in the first sheet
        while True:
            msg_temp = ""
            sheetName = str(sync_data[line_index][0])
            sheetIndex, msg_temp = self.getSheetIndex(sync_data, line_index)
            msg += msg_temp
            modelType = str(sync_data[line_index][2])
            valid = (str(sync_data[line_index][3]).upper() == "TRUE")

            if not valid:
                _logger.info(f"Valid: {sheetName} is {valid}. Ending sync process!")
                break

            if sheetIndex < 0:
                break

            _logger.info(f"Valid: {sheetName} is {valid}.")
            quit, msgr, sync_result = self.getSyncValues(sheetName, psw, template_id, sheetIndex, modelType)
            msg += msgr
            line_index += 1

            if quit:
                self.syncFail(msg, self._sync_cancel_reason)
                return

            # Process results for CCP and Pricelist syncs
            if modelType in ["CCP", "Pricelist"]:
                status, error_report, items_updated = sync_result.get("status"), sync_result.get("error_report"), sync_result.get("items_updated")

                # Combine sync data
                combined_error_report.append(error_report)
                combined_items_updated.extend(items_updated)

                # Update overall status
                if status == "error":
                    overall_status = "error"
                elif status == "warning" and overall_status != "error":
                    overall_status = "warning"

        # End sync
        sync_end_time = fields.Datetime.now()

        # Generate sync report
        self.create_sync_report(sync_start_time, sync_end_time, overall_status, combined_error_report, combined_items_updated)

        # Log ending sync
        _logger.info("Ending Sync")

    ###################################################################
    # Create Sync Report
    def create_sync_report(self, start_time, end_time, status, error_reports, items_updated):
        # Combine error reports into a single string
        combined_error_report = "\n".join([report for report in error_reports if report])

        # Generate name for the sync report
        report_name = f"Report for {start_time.strftime('%H:%M')} sync on {start_time.strftime('%d/%m/%Y')}"

        # Calculate sync duration in minutes
        sync_duration = (end_time - start_time).total_seconds() / 60.0

        # Create the sync report record
        self.env['sync.report'].create({
            'name': report_name,
            'status': status,
            'start_datetime': start_time,
            'end_datetime': end_time,
            'sync_duration': sync_duration,
            'error_report': combined_error_report or "No errors yet...",
            'items_updated': "\n".join(items_updated) or "No items updated..."
        })

    ###################################################################
    # Get Sync Values
    def getSyncValues(self, sheetName, psw, template_id, sheetIndex, syncType):
        sheet = self.getMasterDatabaseSheet(template_id, psw, sheetIndex)
        sync_result = {"status": "success", "error_report": "", "items_updated": []}

        _logger.info("Sync Type is: " + syncType)

        # Identify the type of sheet
        if syncType == "Companies":
            syncer = sync_companies(sheetName, sheet, self)
            quit, msg = syncer.syncCompanies()

        elif syncType == "Contacts":
            syncer = sync_contacts(sheetName, sheet, self)
            quit, msg = syncer.syncContacts()

        elif syncType == "Products":
            syncer = sync_products(sheetName, sheet, self)
            quit, msg = syncer.syncProducts(sheet)

        elif syncType == "CCP":
            syncer = sync_ccp(sheetName, sheet, self)
            quit, msg, sync_result = syncer.syncCCP()  # Expecting new return format

        elif syncType == "Pricelist":
            syncer = sync_pricelist(sheetName, sheet, self)
            quit, msg, sync_result = syncer.syncPricelist()  # Expecting new return format

        elif syncType == "WebHTML":
            syncer = syncWeb(sheetName, sheet, self)
            quit, msg = syncer.syncWebCode(sheet)
            if msg != "":
                _logger.error(msg)

        _logger.info("Done with " + syncType)

        return quit, msg, sync_result
