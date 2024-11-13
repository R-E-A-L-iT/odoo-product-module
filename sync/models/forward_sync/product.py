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

SKIP_NO_CHANGE = True


class sync_products:
    def __init__(self, name, sheet, database):
        self.name = name
        self.sheet = sheet
        self.database = database

    def syncProducts(self, sheet):
        _logger.info(f"Starting product synchronization for sheet: {self.name}")
       
        columns = dict()
        columnsMissing = False
        msg = ""
        i = 1

        # Validate header format
        _logger.debug("Validating sheet header...")
        productHeaderDict = {
            "SKU": "sku",
            "EN-Name": "english_name",
            "FR-Name": "french_name",
            "EN-Description": "english_description",
            "FR-Description": "french_description",
            "PriceCAD": "priceCAD",
            "PriceUSD": "priceUSD",
            "Product Type": "type",
            "Tracking": "tracking",
            "CanBeSold": "can_be_sold",
            "Valid": "valid",
            "Continue": "continue"
        }

        sheetWidth = len(productHeaderDict)                                            
        columns, msg, columnsMissing = utilities.checkSheetHeader(productHeaderDict, self.sheet, self.name)

        if sheetWidth != len(sheet[i]) or columnsMissing:
            msg = (
                f"<h1>Product page Invalid</h1>\n<p>{self.name} width is: {len(self.sheet[i])} Expected {sheetWidth}</p>\n{msg}"
            )
            self.database.sendSyncReport(msg)
            _logger.error(f"Sheet header validation failed: {msg}")
            return True, msg

        # Process each row
        _logger.debug("Processing rows in the sheet...")
        while True:
            if str(sheet[i][columns["continue"]]).upper() != "TRUE":
                _logger.debug(f"Stopping at row {i} due to 'Continue' flag being False.")
                break

            key = str(sheet[i][columns["sku"]])
            _logger.debug(f"Processing row {i} with SKU: {key}")

            # Validation checks
            if not utilities.check_id(key):
                msg = utilities.buildMSG(msg, self.name, key, "Key Error")
                _logger.warning(f"Invalid SKU at row {i}: {key}")
                i += 1
                continue

            if not utilities.check_price(sheet[i][columns["priceCAD"]]):
                msg = utilities.buildMSG(msg, self.name, key, "CAD Price Invalid")
                _logger.warning(f"Invalid CAD price at row {i}: {sheet[i][columns['priceCAD']]}")
                i += 1
                continue

            if not utilities.check_price(sheet[i][columns["priceUSD"]]):
                msg = utilities.buildMSG(msg, self.name, key, "USD Price Invalid")
                _logger.warning(f"Invalid USD price at row {i}: {sheet[i][columns['priceUSD']]}")
                i += 1
                continue

            # Data processing
            try:
                external_id = str(sheet[i][columns["sku"]])
                product_ids = self.database.env["ir.model.data"].search(
                    [("name", "=", external_id), ("model", "=", "product.template")]
                )

                if product_ids:
                    product = self.database.env["product.template"].browse(
                        product_ids[-1].res_id
                    )
                    if len(product) != 1:
                        msg = utilities.buildMSG(
                            msg,
                            self.name,
                            key,
                            "Product ID Recognized But Product Count is Invalid",
                        )
                        _logger.error(f"Invalid product count for SKU {key}")
                        i += 1
                        continue

                    _logger.info(f"Updating product for SKU {key}")
                    self.updateProducts(
                        product,
                        str(sheet[i][:]),
                        sheet[i][columns["english_name"]],
                        sheet[i][columns["french_name"]],
                        sheet[i][columns["english_description"]],
                        sheet[i][columns["french_description"]],
                        sheet[i][columns["priceCAD"]],
                        sheet[i][columns["priceUSD"]],
                        "serial",
                        "product",
                        sheet[i][columns["can_be_sold"]]
                    )
                else:
                    _logger.info(f"Creating and updating product for SKU {key}")
                    self.createAndUpdateProducts(
                        external_id,
                        str(sheet[i][:]),
                        sheet[i][columns["english_name"]],
                        sheet[i][columns["french_name"]],
                        sheet[i][columns["english_description"]],
                        sheet[i][columns["french_description"]],
                        sheet[i][columns["priceCAD"]],
                        sheet[i][columns["priceUSD"]],
                        "serial",
                        "product",
                        sheet[i][columns["can_be_sold"]]
                    )

            except Exception as e:
                _logger.error(f"Exception processing SKU {key}: {str(e)}", exc_info=True)
                msg = utilities.buildMSG(msg, self.name, key, str(e))
                return True, msg

            i += 1

        _logger.info("Product synchronization complete.")
        return False, msg

    def updateProducts(
        self,
        product,
        product_stringRep,
        product_name_english,
        product_name_french,
        product_description_sale_english,
        product_description_sale_french,
        product_price_cad,
        product_price_usd,
        product_tracking,
        product_type,
        can_be_sold
    ):
        _logger.debug(f"Checking if update is required for product: {product.name}")
        if product.stringRep == product_stringRep and SKIP_NO_CHANGE:
            _logger.info(f"No changes detected for product: {product.name}. Skipping update.")
            return

        _logger.info(f"Updating product: {product.name}")
        product.name = product_name_english

        product_sync_common.translatePricelist(
            self.database,
            product,
            product_name_english,
            product_description_sale_english,
            "en_US",
        )
        product_sync_common.translatePricelist(
            self.database,
            product,
            product_name_french,
            product_description_sale_french,
            "fr_CA",
        )

        product.description_sale = product_description_sale_english
        product.type = product_type
        product.stringRep = product_stringRep

        product_sync_common.addProductToPricelist(
            self.database, product, "🇨🇦", product_price_cad
        )
        product_sync_common.addProductToPricelist(
            self.database, product, "🇺🇸", product_price_usd
        )
        product.price = product_price_cad
        product.cadVal = product_price_cad
        product.usdVal = product_price_usd

        if str(can_be_sold).upper() == "TRUE":
            product.sale_ok = True
        else:
            product.sale_ok = False

    def createProducts(self, external_id, product_name):
        _logger.info(f"Creating new product with external ID: {external_id}")
        ext = self.database.env["ir.model.data"].create(
            {"name": external_id, "model": "product.template"}
        )[0]
        product = self.database.env["product.template"].create({"name": product_name})[0]

        product.tracking = "serial"
        product.type = "product"
        ext.res_id = product.id

    # Method to create and update a product
    # Input
    #   external_id:                The SKU in GoogleSheet
    #   product_stringRep:          The GoogleSheet line that represent all the informations of the product
    #   product_name:               Product Name
    #   product_description_sale:   English dercription
    #   product_price_cad:          Price in CAD
    #   product_price_usd:          Price in USD
    #   product_tracking:           Tracking
    #   product_type:               Type
    #   product.sale_ok             can_be_sold if the product can be sold or not    
    # Output
    #   product:                    The product created
    
    def createAndUpdateProducts(
        self,
        external_id,
        product_stringRep,
        product_name_english,
        product_name_french,
        product_description_sale_english,
        product_description_sale_french,
        product_price_cad,
        product_price_usd,
        product_tracking,
        product_type,
        can_be_sold
    ):
        # creates record and updates it
        product = self.createProducts(external_id, product_name_english)
        self.updateProducts(
            product,
            product_stringRep,
            product_name_english,
            product_name_french,
            product_description_sale_english,
            product_description_sale_french,
            product_price_cad,
            product_price_usd,
            product_tracking,
            product_type,
            can_be_sold
        )
        _logger.info(f"Created product: {product.name}")
        return product

    # def createAndUpdateProducts(self, external_id, *args, **kwargs):
    #     _logger.info(f"Creating and updating product with external ID: {external_id}")
    #     product = self.createProducts(external_id, kwargs["product_name_english"])
    #     self.updateProducts(product, *args, **kwargs)
