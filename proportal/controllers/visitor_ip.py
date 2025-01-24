import uuid
from odoo import http
from odoo.http import request

class WebsiteVisitorIPController(http.Controller):

    @http.route('/log_visitor_ip', type='http', auth="public", website=True, csrf=False)
    def log_visitor_ip(self, **kwargs):
        """Logs the IP address of the current website visitor."""
        # Fetch the current visitor session or create a new visitor record
        visitor = request.env['website.visitor'].sudo().search([
            ('access_token', '=', request.session.sid)
        ], limit=1)

        if not visitor:
            # Generate a valid 32-character access_token using UUID
            access_token = uuid.uuid4().hex  # Generates a 32-character hexadecimal string
            visitor = request.env['website.visitor'].sudo().create({
                'name': request.session.sid,
                'access_token': access_token,
            })

        # Log the IP address
        if visitor and not visitor.ip_address:
            visitor.ip_address = request.httprequest.remote_addr

        return "IP Logged"
