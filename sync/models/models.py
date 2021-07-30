#-*- coding: utf-8 -*-

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast
import logging
import json
import re

import requests
import werkzeug.urls

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

_logger = logging.getLogger(__name__)

class sync(models.Model):
    _name = "sync.sync"
    _inherit = "google.drive.config"
    _description = "Sync App"

class sync(models.Model):
    _name = "sync.sync"
    
    _inherit = "google.drive.config"
    
    DatabaseURL = fields.Char(default="https://docs.google.com/spreadsheets/d/14XrvJUaWddKFIEV3eYZvcCtAyzkvdNDswsREgUxiv_A/edit?usp=sharing")
    
    _description = "Sync App"
    def start_sync(self):
        _logger.info("Starting Sync")
        self.getCell()
        _logger.info("Ending Sync")
        
    def getCell(self):
        DatabaseURL = fields.Char(default="")
        _logger.info("Start Sync")
        fileID = "1ZoT9NZ1pJEtYWRavImwsYPnccTxGB51e34qcDo9cclU"
        accsess_token = self.get_access_token()
        headers = {
            'Accept': 'application/json',
            'Authorization': 'Bearer %s' % (accsess_token)
        }
        requestURL = "https://sheets.googleapis.com/v4/spreadsheets/%s" % (fieldID)
        raise UserError(_(str(self.env['google.service']._do_request(requestURL, preuri='', headers=headers, method="GET"))))