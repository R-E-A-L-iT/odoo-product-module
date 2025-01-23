from odoo import http
from odoo.http import request

class WebsiteVisitorIPController(http.Controller):

    @http.route('/log_visitor_ip', type='http', auth="public", website=True, csrf=False)
    def log_visitor_ip(self, **kwargs):
        visitor = request.env['website.visitor']._get_visitor()
        if visitor and not visitor.ip_address:

            # get ip from http request
            visitor.ip_address = request.httprequest.remote_addr
            visitor.sudo().write({'ip_address': visitor.ip_address})
        return ""
