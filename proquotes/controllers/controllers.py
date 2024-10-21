# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import base64
import binascii

from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request
from odoo.http import Response
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers.portal import CustomerPortal as cPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.addons.website.controllers.main import Website as WebsiteINH
from odoo.osv import expression
import re

_logger = logging.getLogger(__name__)


# class CustomPortalSaleOrder(http.Controller):

#     @http.route(['/my/orders/<int:order_id>'], type='http', auth="public", website=True)
#     def update_requesT_lang(self, sale_order_id, **kwargs):
#         sale_order = request.env['sale.order'].sudo().browse(sale_order_id)

#         # Check if the partner's language is French and set the request language to French
#         if sale_order.partner_id.lang.code == 'fr_CA':
#             request.lang.code = 'fr_CA'
#         else:
#             request.lang = request.lang  # Keep the default website language

#         # Call the default controller or return your own response
#         return request.render("sale.sale_order_portal_content", {'sale_order': sale_order})

class QuoteCustomerPortal(cPortal):
    def validate(string):
        reg = "^[a-zA-Z0-9- ]*$"
        return not (re.search(reg, string) == None)

    def _get_portal_order_details(self, order_sudo):
        return {}

    @http.route(
        ["/my/orders/<int:order_id>/ponumber"], type="json", auth="public", website=True
    )
    def poNumber(self, order_id, ponumber, access_token=None, **post):
        # Confirm Access
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if str(order_sudo.state) == "sale":
            _logger.info("Locked Quote")
            order_sudo._compute_tax_totals()
            results = self._get_portal_order_details(order_sudo)

            results["sale_inner_template"] = request.env["ir.ui.view"]._render_template(
                "sale.sale_order_portal_content",
                {
                    "sale_order": order_sudo,
                    "report_type": "html",
                },
            )

            return results
        _logger.info("Unlocked Quote")

        if not self.validate(ponumber):
            return

        order_sudo.customer_po_number = ponumber

        return

    @http.route(
        ["/my/orders/<int:order_id>/select"], type="json", auth="public", website=True
    )
    def select(self, order_id, line_ids, selected, access_token=None, **post):
        # Confirm Access
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if str(order_sudo.state) == "sale":
            _logger.info("Locked Quote")
            order_sudo._compute_tax_totals()
            results = self._get_portal_order_details(order_sudo)

            results["sale_inner_template"] = request.env["ir.ui.view"]._render_template(
                "sale.sale_order_portal_content",
                {
                    "sale_order": order_sudo,
                    "report_type": "html",
                },
            )

            return results
        _logger.info("Unlocked Quote")

        i = 0
        # Loop through Line Items
        while i < len(line_ids):
            # Calculate Line Id
            digits = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}
            line_id_formated = ""

            for c in line_ids[i]:
                if c in digits:
                    line_id_formated = line_id_formated + c

            # Confirm Quote is not confirmed
            if str(order_sudo.state) == "sale":
                _logger.info("Locked Quote")
                return request.redirect(order_sudo.get_portal_url())
            _logger.info("Unlocked Quote")

            # Select Line based on line_id_formated
            select_sudo = (
                request.env["sale.order.line"].sudo().browse(int(line_id_formated))
            )

            # Update Line
            if selected[i] == "true":
                select_sudo.selected = "true"
            else:
                select_sudo.selected = "false"
            i = i + 1

            if order_sudo != select_sudo.order_id:
                return request.redirect(order_sudo.get_portal_url())

        order_sudo._compute_tax_totals()
        results = self._get_portal_order_details(order_sudo)

        results["sale_inner_template"] = request.env["ir.ui.view"]._render_template(
            "sale.sale_order_portal_content",
            {
                "sale_order": order_sudo,
                "report_type": "html",
            },
        )

        return results

    @http.route(
        ["/my/orders/<int:order_id>/sectionSelect"],
        type="json",
        auth="public",
        website=True,
    )
    def sectionSelect(
        self, order_id, section_id, line_ids, selected, access_token=None, **post
    ):
        # Confirm Access
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if str(order_sudo.state) == "sale":
            _logger.info("Locked Quote")
            order_sudo._compute_tax_totals()
            results = self._get_portal_order_details(order_sudo)

            results["sale_inner_template"] = request.env["ir.ui.view"]._render_template(
                "sale.sale_order_portal_content",
                {
                    "sale_order": order_sudo,
                    "report_type": "html",
                },
            )

            return results
        _logger.info("Unlocked Quote")

        i = 0

        # Calculate Line Id
        digits = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}
        section_id_formated = ""
        for c in section_id:
            if c in digits:
                section_id_formated = section_id_formated + c

        select_sudo = (
            request.env["sale.order.line"].sudo().browse(int(section_id_formated))
        )
        if selected:
            select_sudo.selected = "true"
        else:
            select_sudo.selected = "false"

        # Loop through Line Items
        while i < len(line_ids):
            # Calculate Line Id
            digits = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}
            line_id_formated = ""

            for c in line_ids[i]:
                if c in digits:
                    line_id_formated = line_id_formated + c

            select_sudo = (
                request.env["sale.order.line"].sudo().browse(int(line_id_formated))
            )

            # Update Line
            if selected:
                select_sudo.sectionSelected = "true"
            else:
                select_sudo.sectionSelected = "false"
            i = i + 1

            if order_sudo != select_sudo.order_id:
                return request.redirect(order_sudo.get_portal_url())

        order_sudo._compute_tax_totals()
        results = self._get_portal_order_details(order_sudo)

        results["sale_inner_template"] = request.env["ir.ui.view"]._render_template(
            "sale.sale_order_portal_content",
            {
                "sale_order": order_sudo,
                "report_type": "html",
            },
        )

        return results

    @http.route(
        ["/my/orders/<int:order_id>/fold/<string:line_id>"],
        type="json",
        auth="public",
        website=True,
    )
    def hideUnhide(self, order_id, line_id, checked, access_token=None, **post):
        # Confirm Access
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        # Calculate Line Id
        digits = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}
        line_id_formated = ""

        for c in line_id:
            if c in digits:
                line_id_formated = line_id_formated + c

        select_sudo = (
            request.env["sale.order.line"].sudo().browse(int(line_id_formated))
        )

        # Update Line
        if checked:
            select_sudo.hiddenSection = "yes"
        else:
            select_sudo.hiddenSection = "no"

        if order_sudo != select_sudo.order_id:
            return request.redirect(order_sudo.get_portal_url())

        results = self._get_portal_order_details(order_sudo)
        results["sale_template"] = request.env["ir.ui.view"]._render_template(
            "sale.sale_order_portal_content",
            {
                "sale_order": order_sudo,
                "report_type": "html",
            },
        )

        return results

    @http.route(
        ["/my/orders/<int:order_id>/changeQuantity/<string:line_id>"],
        type="json",
        auth="public",
        website=True,
    )
    def change_quantity(self, order_id, line_id, quantity, access_token=None, **post):
        # Confirm Access
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if str(order_sudo.state) == "sale":
            _logger.info("Locked Quote")
            order_sudo._compute_tax_totals()
            results = self._get_portal_order_details(order_sudo)

            results["sale_inner_template"] = request.env["ir.ui.view"]._render_template(
                "sale.sale_order_portal_content",
                {
                    "sale_order": order_sudo,
                    "report_type": "html",
                },
            )

            return results
        _logger.info("Unlocked Quote")

        # Calculate Line Id
        digits = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}
        line_id_formated = ""

        for c in line_id:
            if c in digits:
                line_id_formated = line_id_formated + c

        select_sudo = (
            request.env["sale.order.line"].sudo().browse(int(line_id_formated))
        )

        # Update Line
        select_sudo.product_uom_qty = quantity
        if quantity <= 0:
            raise UserError(_("Product Quantity Must Be At Least 1"))

        if order_sudo != select_sudo.order_id:
            return request.redirect(order_sudo.get_portal_url())
        order_sudo._compute_tax_totals()

        results = self._get_portal_order_details(order_sudo)

        results["sale_inner_template"] = request.env["ir.ui.view"]._render_template(
            "sale.sale_order_portal_content",
            {
                "sale_order": order_sudo,
                "report_type": "html",
            },
        )

        return results

class Website(WebsiteINH):
    @http.route('/website/lang/<lang>', type='http', auth="public", website=True, multilang=False)
    def change_lang(self, lang, r='/', **kwargs):
        """ :param lang: supposed to be value of `url_code` field """
        _logger.info('**********************************',kwargs)
        if lang == 'default':
            lang = request.website.default_lang_id.url_code
            r = '/%s%s' % (lang, r or '/')
        lang_code = request.env['res.lang']._lang_get_code(lang)
        # replace context with correct lang, to avoid that the url_for of request.redirect remove the
        # default lang in case we switch from /fr -> /en with /en as default lang.
        _logger.info('>>>>>>>lang_code>>>>>>>',lang_code)
        request.update_context(lang=lang_code)
        redirect = request.redirect(r or ('/%s' % lang))
        redirect.set_cookie(key='frontend_lang', value=str(lang_code), path='/')
        
        request.session['lang'] = lang_code
        request.env['res.lang']._activate_lang(lang_code)
        _logger.info('>>>>>>>lang_code after>>>>>>>:%s',lang_code)
        #
        _logger.info('>>>>>>>123456789>>>>>>>')
        return redirect
