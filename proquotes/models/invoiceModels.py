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
    pricelist_id = fields.Many2one('product.pricelist', string="Pricelist")

    @api.onchange('pricelist_id')
    def _update_prices(self):
        pricelist = self.pricelist_id.id

        # Apply the correct price to every product in the invoice
        for record in self.invoice_line_ids:
            product = record.product_id

            # Select Pricelist Entry based on Pricelist and Product
            priceResult = self.env['product.pricelist.item'].search(
                [('pricelist_id.id', '=', pricelist), ('product_tmpl_id.sku', '=', product.sku)])
            if (len(priceResult) < 1):
                record.price_unit = product.price
                record.price_subtotal = product.price
                continue

            # Appy Price from Pricelist
            _logger.info(record.tax_ids)
            record.price_unit = priceResult[-1].fixed_price
            record.price_subtotal = record.quantity * \
                priceResult[-1].fixed_price

        _logger.info("Prices Updated")


class invoiceLine(models.Model):
    _inherit = "account.move.line"

    applied_name = fields.Char(
        compute='get_applied_name', string="Applied Name")

    def set_price(self):
        pricelist = self.move_id.pricelist_id
        product = self.product_id
        priceResult = self.env['product.pricelist.item'].search(
            [('pricelist_id.id', '=', pricelist.id), ('product_tmpl_id.sku', '=', product.sku)])
        if (len(priceResult) < 1):
            self.price_unit = product.price
            self.price_subtotal = product.price
            raise Exception(
                f'Price Result is: {priceResult} SKU: {product.sku} Pricelist: {pricelist.id}')
            return

        # Appy Price from Pricelist
        _logger.info(self.tax_ids)
        self.price_unit = priceResult[-1].fixed_price
        self.price_subtotal = self.quantity * \
            priceResult[-1].fixed_price
        # raise Exception(f'{priceResult[-1].fixed_price}')

    @api.onchange('price_unit')
    def init_price(self):
        if (self.product_id != False and self.price_unit == 0):
            self.set_price()

    def get_applied_name(self):
        n = name_translation(self)
        n.get_applied_name()
