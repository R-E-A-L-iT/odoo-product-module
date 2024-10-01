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

_logger = logging.getLogger(__name__)


class mail(models.TransientModel):
    _inherit = "mail.compose.message"

    def get_mail_values(self, res_ids):
        # Force 'reply_to' to be the same as 'email_from'
        result = super().get_mail_values(res_ids)
        for key in result:
            result[key]["reply_to"] = result[key]["email_from"]
            result[key]["reply_to_force_new"] = True
        return result

class MailMessage(models.Model):
    _inherit = 'mail.message'

    @api.model_create_multi
    def create(self, values_list):
        messages = super(MailMessage, self).create(values_list)
        for message in messages:
            if message.model=='sale.order' and message.res_id and message.body:        
                order = self.env['sale.order'].sudo().browse(int(message.res_id))
                if order:
                    
                    recipients = message.partner_ids
                    for contact in order.email_contacts:
                        recipients.append(contact)
                    recipients.append("sales@r-e-a-l.it")
                    
                    message.partner_ids = recipients
                    
                    body = message.body
                    bottom_footer = _("\r\n \r\n Quotation: %s") % (order.sudo().name)
                    body = body + bottom_footer
                    message.body = body
        return messages

class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        if not self:
            return groups

        portal_enabled = isinstance(self, self.env.registry['portal.mixin'])
        if not portal_enabled:
            return groups

        customer = self._mail_get_partners(introspect_fields=False)[self.id]
        if customer:
            access_token = self._portal_ensure_token()
            local_msg_vals = dict(msg_vals or {})
            local_msg_vals['access_token'] = access_token
            local_msg_vals['pid'] = customer[0].id
            local_msg_vals['hash'] = self._sign_token(customer[0].id)
            local_msg_vals.update(customer[0].signup_get_auth_param()[customer[0].id])
            access_link = self._notify_get_action_link('view', **local_msg_vals)

            new_group = [
                ('portal_customer', lambda pdata: pdata['id'] == customer[0].id, {
                    'active': True,
                    'button_access': {
                        'url': access_link,
                    },
                    'has_button_access': True,
                })
            ]
        else:
            new_group = []

        # enable portal users that should have access through portal (if not access rights
        # will do their duty)
        portal_group = next(group for group in groups if group[0] == 'portal')
        portal_group[2]['active'] = True
        portal_group[2]['has_button_access'] = True

        return new_group + groups
