# -*- coding: utf-8 -*-

from odoo import api, fields, models
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

# Add String Rep to facilitate quick check to prevent running a full update every sync


class partner(models.Model):
    _inherit = "res.partner"
    stringRep = fields.Char(default="")


class product(models.Model):
    _inherit = "product.template"
    stringRep = fields.Char(default="")


class pricelist(models.Model):
    _inherit = "product.pricelist"
    stringRep = fields.Char(default="")


class ccp(models.Model):
    _inherit = "stock.lot"
    stringRep = fields.Char(default="")

# app related models

class SyncReport(models.Model):
    _name = 'sync.report'
    _description = 'Sync Report'

    name = fields.Char(string="Report Name", required=True)
    date = fields.Datetime(string="Date", default=fields.Datetime.now)
