# -*- coding: utf-8 -*-

from .utilities import utilities
from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo.tools.translate import _
from odoo import models

_logger = logging.getLogger(__name__)


class product_sync_common():

    @classmethod
    def translatePricelist(cls, database, product, name, description, lang):
        _logger.error(str(lang))
        product_name = database.env['ir.translation'].search([('res_id', '=', product.id),
                                                              ('name', '=',
                                                               'product.template,name'),
                                                              ('lang', '=', lang)])
        if (len(product_name) > 0):
            for name_record in product_name:
                name_record.value = name

        else:
            product_name_new = database.env['ir.translation'].create({'name': 'product.template,name',
                                                                      'lang': lang,
                                                                      'res_id': product.id})[0]
            product_name_new.value = name
            product_name_new.type = 'model'

        product_description = database.env['ir.translation'].search([('res_id', '=', product.id),
                                                                     ('name', '=', 'product.template,description_sale'),
                                                                     ('lang', '=', lang)])

        if (len(product_description) > 0):
            for description_record in product_description:
                description_record.value = description
        else:
            product_description_new = database.env['ir.translation'].create({'name': 'product.template,description_sale',
                                                                             'lang': lang,
                                                                             'res_id': product.id})[0]
            product_description_new.value = description
            product_description_new.type = 'model'
        return

    @classmethod
    def addProductToPricelist(database, product, pricelistName, price):
        pass
