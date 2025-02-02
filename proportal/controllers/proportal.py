# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import binascii

from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers.portal import CustomerPortal as CP
from odoo.addons.portal.controllers.portal import (
    pager as portal_pager,
    get_records_pager,
)
import logging

from odoo.osv import expression
from odoo.tools import replace_exceptions
from werkzeug.exceptions import NotFound
from odoo.addons.mail.models.discuss.mail_guest import add_guest_to_context
from odoo.addons.im_livechat.controllers.main import LivechatController

_logger = logging.getLogger(__name__)


class CustomerPortal(CP):
    # Create product page in the portal
    @http.route(
        ["/my/products", "/my/products/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def products(self):
        company = request.env.user.partner_id.parent_id
        values = {"company": company}
        return request.render("proportal.portal_products", values)


class WebsiteLivechat(LivechatController):

    @http.route('/im_livechat/get_session', methods=["POST"], type="json", auth='public')
    @add_guest_to_context
    def get_session(self, channel_id, anonymous_name, previous_operator_id=None, chatbot_script_id=None, persisted=True,
                    **kwargs):
        user_id = None
        country_id = None
        # if the user is identifiy (eg: portal user on the frontend), don't use the anonymous name. The user will be added to session.
        if request.session.uid:
            user_id = request.env.user.id
            country_id = request.env.user.country_id.id
        else:
            # if geoip, add the country name to the anonymous name
            if request.geoip.country_code:
                # get the country of the anonymous person, if any
                country = request.env['res.country'].sudo().search([('code', '=', request.geoip.country_code)], limit=1)
                if country:
                    country_id = country.id

        if previous_operator_id:
            previous_operator_id = int(previous_operator_id)

        chatbot_script = False
        if chatbot_script_id:
            frontend_lang = request.httprequest.cookies.get('frontend_lang', request.env.user.lang or 'en_US')
            chatbot_script = request.env['chatbot.script'].sudo().with_context(lang=frontend_lang).browse(
                chatbot_script_id)
        channel_vals = request.env["im_livechat.channel"].with_context(lang=False).sudo().browse(
            channel_id)._get_livechat_discuss_channel_vals(
            anonymous_name,
            previous_operator_id=previous_operator_id,
            chatbot_script=chatbot_script,
            user_id=user_id,
            country_id=country_id,
            lang=request.httprequest.cookies.get('frontend_lang')
        )
        _logger.info('________________ channel_vals: %s', channel_vals)
        if not channel_vals:
            return False
        if not persisted:
            operator_partner = request.env['res.partner'].sudo().browse(channel_vals['livechat_operator_id'])
            display_name = operator_partner.user_livechat_username or operator_partner.display_name
            return {
                'name': channel_vals['name'],
                'chatbot_current_step_id': channel_vals['chatbot_current_step_id'],
                'state': 'open',
                'operator_pid': (operator_partner.id, display_name.replace(',', '')),
                'chatbot_script_id': chatbot_script.id if chatbot_script else None
            }
        channel = request.env['discuss.channel'].with_context(mail_create_nosubscribe=False).sudo().create(channel_vals)
        with replace_exceptions(UserError, by=NotFound()):
            # sudo: mail.guest - creating a guest and their member in a dedicated channel created from livechat
            __, guest = channel.sudo()._find_or_create_persona_for_channel(
                guest_name=self._get_guest_name(),
                country_code=request.geoip.country_code,
                timezone=request.env['mail.guest']._get_timezone_from_request(request),
                post_joined_message=False
            )
        channel = channel.with_context(guest=guest)  # a new guest was possibly created
        if not chatbot_script or chatbot_script.operator_partner_id != channel.livechat_operator_id:
            channel._broadcast([channel.livechat_operator_id.id])
        channel_info = channel._channel_info()[0]
        if guest:
            channel_info['guest_token'] = guest._format_auth_cookie()

        if channel_vals:
            livechat_channel_id = request.env["im_livechat.channel"].sudo().browse(int(channel_vals.get('livechat_channel_id')))
            for user in livechat_channel_id.user_ids:
                if user.login:  # Ensure the user has an email address
                    email_template = request.env.ref('proportal.live_chet_session_started_email',raise_if_not_found=False)
                    if email_template:
                        mail_body = email_template.body_html
                        subject = email_template.subject
                        mail_body = mail_body.replace('channel_name', livechat_channel_id.name)
                        template_values = {
                            'subject': subject,
                            'email_from':  "sales@r-e-a-l.it",
                            'email_to': user.login,
                            'body_html': mail_body,
                        }
                        email_template.send_mail(livechat_channel_id.id, email_values=template_values, force_send=True)
        return channel_info