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

    _sync_cancel_reason = "<h1>The Sync Process Was forced to quit and no records were updated</h1><h1> The Following Rows of The Google Sheet Table are invalid<h1>"
    _sync_fail_reason = "<h1>The Following Rows of The Google Sheet Table are invalid and were not Updated to Odoo</h1>"

    _odoo_sync_data_index = 0

    ###################################################################
    # STARTING POINT
    def start_sync(self, psw=None):
        _logger.info("Starting Sync")
        db_name = self.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
        template_id = sheetsAPI.get_master_database_template_id(db_name)
        _logger.info("db_name: " + str(db_name))
        _logger.info("template_id: " + str(template_id))

        sheetName = ""
        sheetIndex = -1
        modelType = ""
        valid = False

        line_index = 1
        msg = ""

        # Checks authentication values
        if (not self.is_psw_format_good(psw)):
            return

        # Get the ODOO_SYNC_DATA tab
        sync_data = self.getMasterDatabaseSheet(
            template_id, psw, self._odoo_sync_data_index)

        # loop through entries in first sheet
        while (True):
            msg_temp = ""
            sheetName = str(sync_data[line_index][0])
            sheetIndex, msg_temp = self.getSheetIndex(sync_data, line_index)
            msg += msg_temp
            modelType = str(sync_data[line_index][2])
            valid = (str(sync_data[line_index][3]).upper() == "TRUE")

            if (not valid):
                _logger.info("Valid: " + sheetName + " is " + str(valid) + " because the str was : " +
                             str(sync_data[line_index][3]) + ".  Ending sync process!")
                break

            if (sheetIndex < 0):
                break

            _logger.info("Valid: " + sheetName + " is " + str(valid) + ".")
            quit, msgr = self.getSyncValues(sheetName,
                                            psw,
                                            template_id,
                                            sheetIndex,
                                            modelType)
            msg = msg + msgr
            line_index += 1

            if (quit):
                self.syncFail(msg, self._sync_cancel_reason)
                return

        # error
        if (msg != ""):
            self.syncFail(msg, self._sync_fail_reason)

        _logger.info("Ending Sync")

    ###################################################################
    # Check the password format
    # Input
    #   psw:   The password to open the googlesheet
    # Output
    #   True : Password format is good
    #   False: Password format if bad
    def is_psw_format_good(self, psw):

        # Checks authentication values
        if ((psw == None) or (str(type(psw)) != "<class 'dict'>")):
            msg = "<h1>Sync Error</h1><p>Authentication values Missing</p>"
            _logger.info(msg)
            self.sendSyncReport(msg)
            return False

        return True

    ###################################################################
    # Get a tab in the GoogleSheet Master Database
    # Input
    #   template_id:    The GoogleSheet Template ID to acces the master database
    #   psw:            The password to acces the DB
    #   index:          The index of the tab to pull
    # Output
    #   data:           A tab in the GoogleSheet Master Database
    def getMasterDatabaseSheet(self, template_id, psw, index):
        # get the database data; reading in the sheet

        try:
            return (self.getDoc(psw, template_id, index))
        except Exception as e:
            _logger.info(e)
            msg = "<h1>Failed To Retrieve Master Database Document</h1><p>Sync Fail</p><p>" + \
                str(e) + "</p>"
            self.syncFail(msg, self._sync_fail_reason)
            quit

    ###################################################################
    # Get the Sheet Index of the Odoo Sync Data tab, column B
    # Input
    #   sync_data:  The GS ODOO_SYNC_DATA tab
    #   lineIndex:  The index of the line to get the SheetIndex
    # Output
    #   sheetIndex: The Sheet Index for a given Abc_ODOO tab to read
    #   msg:        Message to append to the repport
    def getSheetIndex(self, sync_data, lineIndex):
        sheetIndex = -1
        i = -1
        msg = ""

        if (lineIndex < 1):
            return -1

        i = self.getColumnIndex(sync_data, "Sheet Index")
        if (i < 0):
            return -1

        try:
            sheetIndex = int(sync_data[lineIndex][i])
        except ValueError:
            sheetIndex = -1
            msg = "BREAK: check the tab ODOO_SYNC_DATA, there must have a non numeric value in column number " + \
                str(i) + " called 'Sheet Index', line " + \
                str(lineIndex) + ": " + str(sync_data[lineIndex][1]) + "."
            _logger.info(sync_data)

            _logger.info(msg)
            # test to push

        return sheetIndex, msg

    ###################################################################
    def getSyncValues(self, sheetName, psw, template_id, sheetIndex, syncType):

        sheet = self.getMasterDatabaseSheet(template_id, psw, sheetIndex)

        _logger.info("Sync Type is: " + syncType)
        # identify the type of sheet
        if (syncType == "Companies"):
            syncer = sync_companies(sheetName, sheet, self)
            quit, msg = syncer.syncCompanies()

        elif (syncType == "Contacts"):
            syncer = sync_contacts(sheetName, sheet, self)
            quit, msg = syncer.syncContacts()

        elif (syncType == "Products"):
            syncer = sync_products(sheetName, sheet, self)
            quit, msg = syncer.syncProducts(sheet)

        elif (syncType == "CCP"):
            syncer = sync_ccp(sheetName, sheet, self)
            quit, msg = syncer.syncCCP()

        elif (syncType == "Pricelist"):
            # syncer = sync_pricelist.connect(sheetName, sheet, self)
            syncer = sync_pricelist(sheetName, sheet, self)
            quit, msg = syncer.syncPricelist()
            quit = False
            msg = ""
            # quit, msg = self.syncPricelist(sheet)

        elif (syncType == "WebHTML"):
            syncer = syncWeb(sheetName, sheet, self)
            quit, msg = syncer.syncWebCode(sheet)
            if msg != "":
                _logger.error(msg)

        _logger.info("Done with " + syncType)

        if (quit):
            _logger.info("quit: " + str(quit) + "\n")
            _logger.info("msg:  " + str(msg))

        return quit, msg

    ###################################################################
    # Build the message when a sync fail occurs.  Once builded, it will display the message
    # in the logger, and send a repport by email.
    # Input
    #   msg:    The msg that contain information on the failling issue
    #   reason: The reason that lead to the faillur.
    def syncFail(self, msg, reason):
        link = "https://www.r-e-a-l.store/web?debug=assets#id=34&action=12&model=ir.cron&view_type=form&cids=1%2C3&menu_id=4"
        msg = reason + \
            msg + "<a href=\"" + link + "\">Manual Retry</a>"
        _logger.info(msg)
        self.sendSyncReport(msg)

    ###################################################################
    def sendSyncReport(self, msg):
        values = {'subject': 'Sync Report'}
        message = self.env['mail.message'].create(values)[0]

        values = {'mail_message_id': message.id}

        email = self.env['mail.mail'].create(values)[0]
        email.body_html = msg
        email.email_to = "sync@store.r-e-a-l.it"
        email_id = {email.id}
        email.process_email_queue(email_id)

    ###################################################################
    def archive_product(self, product_id):
        product = self.env['product.template'].search(
            [('id', '=', product_id)])
        product.active = False

    ###################################################################
    # Get all value in column of a sheet.  If column does not exist, it will return an empty dict().
    # IMPORTANT:     Row must containt a Valid and Continue column.
    #               Row is skippd if valid is False
    #               Method is exit if the Continue is False
    #
    # Exception
    #   MissingColumnError:  If thrown, the column name is missing.
    #                        If thrown, the column "Valid" is missing.
    #                        If thrown, the column "Continue" is missing.
    # Input
    #   sheet: The sheet to look for all the SKU
    # Output
    #   sku_dict: A dictionnary that contain all the SKU as key, and the value is set to 'SKU'
    def getAllValueFromColumn(self, sheet, column_name):
        sku_dict = dict()
        columnIndex = self.getColumnIndex(sheet, column_name)
        sheet_valid_column_index = self.getColumnIndex(sheet, "Valid")
        sheet_continue_column_index = self.getColumnIndex(sheet, "Continue")

        if (columnIndex < 0):
            raise Exception(
                'MissingColumnError', ("The following column name is missing: " + str(column_name)))

        if (sheet_valid_column_index < 0):
            raise Exception('MissingColumnError',
                            ("The following column name is missing: Valid"))

        if (sheet_continue_column_index < 0):
            raise Exception('MissingColumnError',
                            ("The following column name is missing: Continue"))

        sheet_sku_column_index = self.getColumnIndex(sheet, column_name)

        for i in range(1, len(sheet)):
            if (not str(sheet[i][sheet_continue_column_index]).upper() == "TRUE"):
                break

            if (not str(sheet[i][sheet_valid_column_index]).upper() == "TRUE"):
                continue

            sku_dict[sheet[i][sheet_sku_column_index]] = column_name

        return sku_dict

    ###################################################################
    # Check if a all key unique in two dictionnary
    # Input
    #   dict_small: the smallest dictionnary
    #   dict_big:   The largest dictionnary
    # Output
    #   1st:    True: There is at least one key that exists in both dictionary
    #           False: All key are unique
    #   2nd:    The name of the duplicated Sku
    def checkIfKeyExistInTwoDict(self, dict_small, dict_big):
        for sku in dict_small.keys():
            if sku in dict_big.keys():
                errorMsg = str(sku)
                _logger.info(
                    "------------------------------------------- errorMsg = str(sku): " + str(sku))
                return True, errorMsg
        return False, ""

    ###################################################################
    # Method to get the ODOO_SYNC_DATA column index
    # Exception
    #   MissingTabError:  If thrown, there is a missing tab.  Further logic should not execute since the MasterDataBase does not have the right format.
    # Input
    #   odoo_sync_data_sheet:   The ODOO_SYNC_DATA tab pulled
    # Output
    #   result: A dictionnary:  Key: named of the column
    #                           Value: the index number of that column.
    def checkOdooSyncDataTab(self, odoo_sync_data_sheet):
        odoo_sync_data_sheet_name_column_index = self.getColumnIndex(
            odoo_sync_data_sheet, "Sheet Name")
        odoo_sync_data_sheet_index_column_index = self.getColumnIndex(
            odoo_sync_data_sheet, "Sheet Index")
        odoo_sync_data_model_type_column_index = self.getColumnIndex(
            odoo_sync_data_sheet, "Model Type")
        odoo_sync_data_valid_column_index = self.getColumnIndex(
            odoo_sync_data_sheet, "Valid")
        odoo_sync_data_continue_column_index = self.getColumnIndex(
            odoo_sync_data_sheet, "Continue")

        if (odoo_sync_data_sheet_name_column_index < 0):
            error_msg = (
                "Sheet: ODOO_SYNC_DATA does not have a 'Sheet Name' column.")
            raise Exception('MissingTabError', error_msg)

        if (odoo_sync_data_sheet_index_column_index < 0):
            error_msg = (
                "Sheet: ODOO_SYNC_DATA does not have a 'Sheet Index' column.")
            raise Exception('MissingTabError', error_msg)

        if (odoo_sync_data_model_type_column_index < 0):
            error_msg = (
                "Sheet: ODOO_SYNC_DATA does not have a 'Model Type' column.")
            raise Exception('MissingTabError', error_msg)

        if (odoo_sync_data_valid_column_index < 0):
            error_msg = (
                "Sheet: ODOO_SYNC_DATA does not have a 'Valid' column.")
            raise Exception('MissingTabError', error_msg)

        if (odoo_sync_data_continue_column_index < 0):
            error_msg = (
                "Sheet: ODOO_SYNC_DATA does not have a 'Continue' column.")
            raise Exception('MissingTabError', error_msg)

        result = dict()

        result['odoo_sync_data_sheet_name_column_index'] = odoo_sync_data_sheet_name_column_index
        result['odoo_sync_data_sheet_index_column_index'] = odoo_sync_data_sheet_index_column_index
        result['odoo_sync_data_model_type_column_index'] = odoo_sync_data_model_type_column_index
        result['odoo_sync_data_valid_column_index'] = odoo_sync_data_valid_column_index
        result['odoo_sync_data_continue_column_index'] = odoo_sync_data_continue_column_index

        return result

    # Get all SKU from the model type 'Products' and 'Pricelist'
    # Exception
    #   MissingSheetError:  A sheet is missing
    #   MissingTabError:    A tab in a sheet is missing
    #   SkuUnicityError:    A SKU is not unique
    # Input
    #   psw:            password to acces the Database
    #   template_id:    GoogleSheet TemplateID
    # Output
    #   sku_catalog_gs: A dictionnary that contain all the SKU as key, and 'SKU as value

    ###################################################################
    def getListSkuGS(self, psw, template_id):
        sku_catalog_gs = dict()

        i = 0
        msg = ""

        # Get the ODOO_SYNC_DATA tab
        sync_data = self.getMasterDatabaseSheet(
            template_id, psw, self._odoo_sync_data_index)

        # check ODOO_SYNC_DATA tab
        result_dict = self.checkOdooSyncDataTab(sync_data)
        odoo_sync_data_sheet_name_column_index = result_dict['odoo_sync_data_sheet_name_column_index']
        odoo_sync_data_sheet_index_column_index = result_dict[
            'odoo_sync_data_sheet_index_column_index']
        odoo_sync_data_model_type_column_index = result_dict['odoo_sync_data_model_type_column_index']
        odoo_sync_data_valid_column_index = result_dict['odoo_sync_data_valid_column_index']
        odoo_sync_data_continue_column_index = result_dict['odoo_sync_data_continue_column_index']

        while (i < len(sync_data)):
            i += 1
            sheet_name = ""
            refered_sheet_index = -1
            msg_temp = ""
            modelType = ""
            valid_value = False
            continue_value = False
            sku_dict = dict()
            refered_sheet_valid_column_index = -1
            refered_sheet_sku_column_index = -1

            sheet_name = str(
                sync_data[i][odoo_sync_data_sheet_name_column_index])
            refered_sheet_index, msg_temp = self.getSheetIndex(sync_data, i)
            msg += msg_temp
            modelType = str(
                sync_data[i][odoo_sync_data_model_type_column_index])
            valid_value = (
                str(sync_data[i][odoo_sync_data_valid_column_index]).upper() == "TRUE")
            continue_value = (
                str(sync_data[i][odoo_sync_data_continue_column_index]).upper() == "TRUE")

            # Validation for the current loop
            if (not continue_value):
                # _logger.info("------------------------------------------- BREAK not continue_value while i: " + str(i))
                break

            if ((modelType not in ["Pricelist", "Products"])):
                # _logger.info("------------------------------------------- continue (modelType != 'Pricelist') or (modelType != 'Products') while i: " + str(i) + " model: " + str(modelType))
                continue

            if (not valid_value):
                # _logger.info("------------------------------------------- continue (not valid_value) while i: " + str(i))
                continue

            if (refered_sheet_index < 0):
                error_msg = ("Sheet Name: " + sheet_name +
                             " is missing in the GoogleData Master DataBase.  The Sku Cleaning task could not be executed!")
                _logger.info(
                    "------------------------------------------- raise while i: " + str(i) + " " + error_msg)
                raise Exception('MissingSheetError', error_msg)

            # Get the reffered sheet
            refered_sheet = self.getMasterDatabaseSheet(
                template_id, psw, refered_sheet_index)
            refered_sheet_valid_column_index = self.getColumnIndex(
                refered_sheet, "Valid")
            refered_sheet_sku_column_index = self.getColumnIndex(
                refered_sheet, "SKU")

            # Validation
            if (refered_sheet_valid_column_index < 0):
                error_msg = ("Sheet: " + sheet_name +
                             " does not have a 'Valid' column. The Sku Cleaning task could not be executed!")
                _logger.info(
                    "------------------------------------------- raise while i: " + str(i) + " " + error_msg)
                raise Exception('MissingTabError', error_msg)

            if (refered_sheet_sku_column_index < 0):
                error_msg = ("Sheet: " + sheet_name +
                             " does not have a 'SKU' column. The Sku Cleaning task could not be executed!")
                _logger.info(
                    "------------------------------------------- raise while i: " + str(i) + " " + error_msg)
                raise Exception('MissingTabError', error_msg)

            # main purpose
            sku_dict = self.getAllValueFromColumn(refered_sheet, "SKU")
            result, sku_in_double = self.checkIfKeyExistInTwoDict(
                sku_dict, sku_catalog_gs)

            if (result):
                error_msg = (
                    "The folowing SKU appear twice in the Master Database: " + str(sku_in_double))
                _logger.info(
                    "------------------------------------------- raise while i: " + str(i) + " " + error_msg)
                raise Exception('SkuUnicityError', error_msg)

            for sku in sku_dict:
                sku_catalog_gs[sku] = "sku"

        return sku_catalog_gs

    ###################################################################
    # Return the column index of the columnName
    # Input
    #   sheet:      The sheet to find the Valid column index
    #   columnName: The name of the column to find
    # Output
    #   columnIndex: -1 if could not find it
    #                > 0 if a column name exist
    def getColumnIndex(self, sheet, columnName):
        header = sheet[0]
        columnIndex = 0

        for column in header:
            if (column == columnName):
                return columnIndex

            columnIndex += 1

        return -1

    ###################################################################
    # Method the return a list of product.id need to be archived.
    # The list include all product.id that does not have a prodcut.sku, or that the string or product.sku is False.
    # The list include all product.id that the product.sku is in Odoo and not in GoogleSheet Master Database.
    # Input
    #   psw: the password to acces the GoogleSheet Master Database.
    #   p_optNoSku:
    #   p_optInOdooNotGs:
    # Output
    #   to_archive: a list of product.id
    def getSkuToArchive(self, psw=None, p_optNoSku=True, p_optInOdooNotGs=True):
        _logger.info(
            "------------------------------------------- BEGIN  getSkuToArchive")
        catalog_odoo = dict()
        catalog_gs = dict()
        to_archive = []

        # Checks authentication values
        if (not self.is_psw_format_good(psw)):
            _logger.info("Password not valid")
            return

        template_id_exception_list = []
        template_id_exception_list.append(18103)  # services on Timesheet
        template_id_exception_list.append(561657)
        template_id_exception_list.append(561658)
        #561657
        for e in template_id_exception_list:
            _logger.info(
                "---------------- Exeption list: product.template.id: " + str(e))

        #################################
        # Odoo Section
        products = self.env['product.template'].search([])
        _logger.info("products length before clean up: " + str(len(products)))

        for product in products:
            if (product.active == False):
                continue

            # Check if the ID is in the exception list
            if (product.id in template_id_exception_list):
                continue

            if (p_optNoSku and ((str(product.sku) == "False") or (str(product.sku) == None))):
                if (str(product.id) != "False"):
                    to_archive.append(str(product.id))

                _logger.info("---------------- To archived: Product with NO SKU: Product id: " + str(product.id).ljust(
                    10) + ", active is: " + str(product.active).ljust(7) + ", name: " + str(product.name))

            if (p_optInOdooNotGs and (str(product.sku) not in catalog_odoo)):
                catalog_odoo[str(product.sku)] = 1
            else:
                catalog_odoo[str(product.sku)
                             ] = catalog_odoo[str(product.sku)] + 1

        #######################################
        # GoogleSheet Section
        try:
            db_name = self.env['ir.config_parameter'].sudo(
            ).get_param('web.base.url')
            template_id = sheetsAPI.get_master_database_template_id(db_name)
            catalog_gs = self.getListSkuGS(psw, template_id)

        except Exception as e:
            _logger.info(
                "Cleaning Sku job is interrupted with the following error : \n" + str(e))
            return

        #######################################
        # listing product in Odoo and not in GS
        for item in catalog_odoo:
            if (not item in catalog_gs):
                product = self.env['product.template'].search(
                    [('sku', '=', item)])
                _logger.info("---------------- To archived: In Odoo, NOT in GS: Product id:  " + str(
                    product.id).ljust(10) + "sku: " + str(product.sku).ljust(55) + "name: " + str(product.name))
                if (str(product.id) == "False"):
                    _logger.info(
                        "listing product in Odoo and not in GS, str(product.id) was False.")
                elif (str(product.sku) == "time_product_product_template"):
                    _logger.info("Can not archive Service on Timesheet.")
                # Check if the ID is in the exception list
                elif (item in template_id_exception_list):
                    continue
                else:
                    to_archive.append(str(product.id))

        _logger.info("catalog_gs length: " + str(len(catalog_gs)))
        _logger.info("catalog_odoo length: " + str(len(catalog_odoo)))
        _logger.info("to_archive length: " + str(len(to_archive)))
        _logger.info(
            "--------------- END getSkuToArchive ---------------------------------------------")

        return to_archive

    ###################################################################
    # Method to clean all sku that are pulled by self.getSkuToArchive
    def cleanSku(self, psw=None, p_archive=False, p_optNoSku=True, p_optInOdooNotGs=True):
        _logger.info(
            "--------------- BEGIN cleanSku ---------------------------------------------")
        to_archive_list = self.getSkuToArchive(
            psw, p_optNoSku, p_optInOdooNotGs)
        to_archive_dict = dict()
        sales_with_archived_product = 0

        if p_archive:
            # Archiving all unwanted products
            _logger.info(
                "------------------------------------------- Number of products to archied: " + str(len(to_archive_list)))
            archiving_index = 0

            for item in to_archive_list:
                _logger.info(str(archiving_index).ljust(
                    4) + " archving :" + str(item))
                archiving_index += 1
                self.archive_product(str(item))

            if p_optNoSku:
                _logger.info(
                    "------------------------------------------- ALL products with no SKU or are archived.")
            if p_optInOdooNotGs:
                _logger.info(
                    "------------------------------------------- ALL products with Sku in Odoo and not in GoogleSheet DB are archived.")

        # Switch to dictionnary to optimise the rest of the querry
        for i in range(len(to_archive_list)):
            to_archive_dict[to_archive_list[i]] = 'sku'

        # Listing all sale.order that contain archhived product.id
        order_object_ids = self.env['sale.order'].search([('id', '>', 0)])
        for order in order_object_ids:
            sale_order_lines = self.env['sale.order.line'].search(
                [('order_id', '=', order.id)])

            for line in sale_order_lines:
                product = self.env['product.product'].search(
                    [('id', '=', line.product_id.id)])
                if (str(product.id) in to_archive_dict):
                    if ((str(product.id) != "False")):
                        _logger.info("---------------")
                        _logger.info("orders name: " + str(order.name))
                        _logger.info("id in a sale order: " + str(product.id))
                        _logger.info("sku in a sale order: " +
                                     str(product.sku))
                        _logger.info("name in a sale order: " +
                                     str(product.name))
                        _logger.info("---------------")
                        sales_with_archived_product += 1

        _logger.info("number of sales with archived product: " +
                     str(sales_with_archived_product))
        _logger.info(
            "--------------- END cleanSku ---------------------------------------------")

    ###################################################################
    # Method to log all product id, sku, skuhidden and name
    # Input
    #   sale_name: the name of the sale order
    def log_product_from_sale(self, sale_name, p_log=True):
        _logger.info("Listing all product from: " + str(sale_name))
        order_object_ids = self.env['sale.order'].search(
            [('name', '=', sale_name)])
        for order in order_object_ids:
            sale_order_lines = self.env['sale.order.line'].search(
                [('order_id', '=', order.id)])

            for line in sale_order_lines:
                product = self.env['product.product'].search(
                    [('id', '=', line.product_id.id)])
                if p_log:
                    _logger.info("---------------")
                    _logger.info("orders name: " + str(order.name))
                    _logger.info("id in a sale order: " + str(product.id))
                    _logger.info("sku in a sale order: " + str(product.sku))
                    _logger.info("skuhidden name in a sale order: " +
                                 str(product.skuhidden.name))
                    _logger.info("name in a sale order: " + str(product.name))
                    _logger.info("---------------")

        if p_log:
            _logger.info(
                "--------------- END log_product_from_sale ---------------------------------------------")

    ###################################################################
    # query to find the QUOTATION-2023-01-05-007, id 552
    def searchQuotation(self):
        sale = self.env['sale.order'].search(
            [('id', '=', 552)])
        _logger.info("--------------- sale.order.")
        _logger.info("sale.id: " + str(sale.id))
        _logger.info("sale.name: " + str(sale.name))
        _logger.info("---------------")

    ###################################################################
    # Method to identify all product with the same name
    # Output a dictionary
    #   key : a product template name
    #   values: list of product_template.id that have the same name
    def getProductsWithSameName(self, p_log=True):
        dup_product_template_name = dict()
        products_tmpl = self.env['product.template'].search([])
        count = 0
        if p_log:
            _logger.info(
                "------------------------------------------------------------------")
            _logger.info("---------------  getProductsWithSameName")
            _logger.info(
                "---------------  Number of product template to check: " + str(len(products_tmpl)))

        # For each product,
        for product in products_tmpl:
            if (product.active == False):
                continue

            # Check if the product is already identfied
            if (product.name in dup_product_template_name):
                continue

            # checking if their is other products with the same name.
            doubled_names = self.env['product.template'].search(
                [('name', '=', product.name)])

            if (len(doubled_names) > 1):
                count += 1
                dup_product_template_name[product.name] = []
                # if yes, adding all the product id founded and the name in a list
                for doubled_name in doubled_names:
                    if p_log:
                        _logger.info("--------------- " +
                                     str(count).ljust(5) +
                                     "product_template.id: " + str(doubled_name.id).ljust(10) + str(product.name))
                    dup_product_template_name[product.name].append(
                        doubled_name.id)

        if p_log:
            _logger.info("--------------- Count of the dict: " +
                         str(len(dup_product_template_name)))
            _logger.info(
                "--------------- END getProductsWithSameName ---------------------------------------------")

        return dup_product_template_name

    ###################################################################
    def getSaleOrderByProductId(self, p_product_template_id, p_log=True):
        # validate that product_id is an integer
        try:
            product_template_id = int(p_product_template_id)
        except Exception as e:
            _logger.info(
                "--------------- Could not convert to int product_template_id: " + str(product_template_id))
            _logger.info("--------------- " + str(e))
            return

        # gatter product templte
        product_template = self.env['product.template'].search([
            ('id', '=', product_template_id)])

        # gatter all lines of all sales
        lines = self.env['sale.order.line'].search([])

        product_sold_counter = 0

        # Check if the product.template.id appear in any sale.order.id
        for line in lines:
            for line_product_template in line.product_template_id:
                if (line_product_template.id == product_template.id):
                    for line_order in line.order_id:
                        sale = self.env['sale.order'].search([
                            ('id', '=', line_order.id)])
                        if p_log:
                            _logger.info("---------------" +
                                         "  product_template.id: " + str(product_template.id).ljust(10) +
                                         ", product_template.name: " + str(product_template.name).ljust(100) +
                                         ", line_product_template.id: " + str(line_product_template.id).ljust(20) +
                                         ", sale.id: " + str(sale.id).ljust(10) +
                                         ", sale.name: " + str(sale.name))
                        product_sold_counter += 1
        if p_log:
            _logger.info("--------------- product_sold_counter: " +
                         str(product_sold_counter))
            _logger.info(
                "--------------- END getSaleOrderByProductId ---------------------------------------------")

        return product_sold_counter

    ###################################################################
    def getProductIdBySku(self, p_sku, p_log=True):
        product = self.env['product.product'].search([
            ('sku', '=', p_sku)])
        if p_log:
            _logger.info("--------------- p_sku: " +
                         str(p_sku) + ", id: " + str(product.id))

    ###################################################################
    def cleanProductByName(self):
        duplicate_names_dict = self.getProductsWithSameName(p_log=True)

        for duplicate_name in duplicate_names_dict:
            _logger.info(str(duplicate_name))
            sale_order_count_by_template_id = dict()

            for template_id in duplicate_names_dict[duplicate_name]:
                sale_order_count_by_template_id[template_id] = self.getSaleOrderByProductId(
                    template_id, p_log=False)

            for template_id in sale_order_count_by_template_id:
                if (sale_order_count_by_template_id[template_id] <= 0):
                    action = "could ARCHIVE "
                else:
                    action = "KEEP          "
                _logger.info("           " + action + "template_id " + str(template_id).ljust(
                    10) + " sold count: " + str(sale_order_count_by_template_id[template_id]))
            _logger.info(
                "----------------------------------------------------------------------------------------------------")
            _logger.info("")
            _logger.info("")

        _logger.info(
            "--------------- END cleanProductByName ---------------------------------------------")

        

    ###################################################################

    # def getProductTemplateId(self, name):
    #     product_template = self.env["product.template"].search(
    #         [
    #             ("name", "=", name)
    #         ]
    #     )

    #     if (product_template.id < 0):        
    #         _logger.info("--------------- getProductTemplateId BAD")
    #         _logger.info("--------------- getProductTemplateId: " + str(product_template.id))
    #         return -1

    #     return product_template.id

    def remove_all_rental_pricing(self):
        _logger.info("--------------- remove_all_rental_pricing")
        # Get the product template record you want to update
        products_template = self.env['product.template'].search([]) 

        for p in products_template:
            _logger.info("--------------- remove_all_rental_pricing. p:" + str(p.name))
            # Remove all rental pricing records from the product template
            p.rental_pricing_ids = []



    ###################################################################
    # Method to manualy correct on company
    # Input
    #       p_OwnerID: The short name of the contacted added in GS.  Ex "DIGITALPRECISIO"
    #       p_Name: The name of the contact in Odoo.  Ex "Digital Precision Metrology Inc"
    # Error
    #       Raise an error if contact name does not exist
    def addContact(self, p_OwnerID, p_Name):
        _logger.info("addContact: " + str(p_OwnerID) + ", " + str(p_Name))

        #Check if OwnerID exist
        ownersID = self.env["ir.model.data"].search([("name", "=",str(p_OwnerID))])
        if (len(ownersID) > 0):
            ext = ownersID[0]
        else:
            ext = self.env["ir.model.data"].create({"name":str(p_OwnerID), "model":"res.partner"})[0]  

        #Check if contac name exist 
        company = self.env["res.partner"].search([("name", "=", str(p_Name))])
        if (len(company) > 0):
            company = company[0]
        else:
             raise Exception("Contact name does not exist")
        
        #Assigning the company id
        ext.res_id = company.id

