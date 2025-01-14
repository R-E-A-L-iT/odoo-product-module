# -*- coding: utf-8 -*-

import ast
import base64
import re

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo import api, fields, models, SUPERUSER_ID, _, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api

from .translation import name_translation


_logger = logging.getLogger(__name__)


class InvoiceMain(models.Model):
    _inherit = "account.move"
    pricelist_id = fields.Many2one("product.pricelist", string="Pricelist")

    # Setup Initilize Pricelist for Invoice
    @api.onchange("partner_id")
    def _setpricelist(self):
        self.pricelist_id = self.partner_id.property_product_pricelist

    def _calculate_tax(self, price, tax_obj):
        if tax_obj.amount_type != "group" :
            _logger.info("amount: " + str(tax_obj.amount))
            return round(price * tax_obj.amount / 100, 2)

        result = 0

        for child in tax_obj.children_tax_ids:
            result += self._calculate_tax(price, child)

        _logger.info(result)
        return result

    #@api.onchange("pricelist_id", "invoice_line_ids", "invoice_line_ids.tax_ids")
    #def _update_prices(self):
    #    pricelist = self.pricelist_id.id
    #    # Apply the correct price to every product in the invoice
    #    for record in self.invoice_line_ids:
    #        product = record.product_id
    #        taxes = 0
    #        for tax_item in record.tax_ids:
    #            taxes += self._calculate_tax(record.price_unit, tax_item)
    #        if record.price_override == True or pricelist == False:
    #            record.price_subtotal = record.quantity * (record.price_unit + taxes)
    #            continue
    #        # Select Pricelist Entry based on Pricelist and Product
    #        priceResult = self.env["product.pricelist.item"].search(
    #            [
    #                ("pricelist_id.id", "=", pricelist),
    #                ("product_tmpl_id.sku", "=", product.sku),
    #            ]
    #        )
    #        if len(priceResult) < 1:
    #            record.price_unit = product.price
    #            record.price_subtotal = product.price
    #            continue
    #        # Appy Price from Pricelist
    #        # Apply tax info
    #        _logger.info("line 57")
    #        _logger.info(record.tax_ids)
    #        base_price = priceResult[-1].fixed_price
    #        taxes = 0
    #        for tax_item in record.tax_ids:
    #            _logger.info(tax_item.amount)
    #            taxes += self._calculate_tax(base_price, tax_item)
    #            _logger.info("taxes: " + str(taxes))
    #        record.price_unit = base_price
    #        record.price_subtotal = record.quantity * (base_price + taxes)
    #    _logger.info("Prices Updated")



class invoiceLine(models.Model):
    _inherit = "account.move.line"

    # applied_name = fields.Char(compute="get_applied_name", string="Applied Name")
    applied_name = fields.Char( string="Applied Name")

    price_override = fields.Boolean(default=False, string="Override Price")

    def get_price(self):
        pricelist = self.move_id.pricelist_id
        product = self.product_id
        _logger.info("Invoice Price: " + str(product.name))
        priceResult = self.env["product.pricelist.item"].search(
            [
                ("pricelist_id.id", "=", pricelist.id),
                ("product_tmpl_id.sku", "=", product.sku),
            ]
        )
        if len(priceResult) < 1:
            return product.price

        # Appy Price from Pricelist
        return priceResult[-1].fixed_price

    @api.onchange("price_unit")
    def init_price(self):
        # Set flag marking price as custom
        self.price_override = self.price_unit != self.get_price()

    def get_applied_name(self):
        return True
        # n = name_translation(self)
        # n.get_applied_name()
