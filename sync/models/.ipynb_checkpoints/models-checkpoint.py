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


class partner(models.Model):
    _inhert = "res.partner"
    stringRep = fields.Char(default="")
    
class product(models.Model):
    _inhert = "product.template
    stringRep = fields.Char(default="")
    
class pricelist(models.Model):
    _inhert = "product.pricelist"
    stringRep = fields.Char(default="")
    
class ccp(models.Model):
    _inhert = "stock.production.lot"
    stringRep = fields.Char(default="")
    
    