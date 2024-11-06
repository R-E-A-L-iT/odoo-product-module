from odoo import models, fields, api

class Commissions(models.Model):
    _name = 'procom.commission'
    _description = 'Commissions Records'
    
    name = fields.Char(string="Commission Name", required=True)
    related_lead = fields.Many2one('crm.lead', string="Related Lead")
    related_order = fields.Many2one('sale.order', string="Related Order", required="True")
    # domain=[('move_type', '=', 'out_invoice')]
    related_invoice = fields.Many2one('account.move', string="Related Invoice")
    
    test_user = fields.Many2one('res.users', string="Assigned User")
    
    # sales roles
    # new_customer = fields.Many2one('res.user', string="Contact New Customer")
    # logged_lead = fields.Many2one('res.user', string="Logged Lead")
    # developed_lead = fields.Many2one('res.user', string="Developed Opportunity")
    # performed_demo = fields.Many2one('res.user', string="Performed Demo")
    # quote_to_order = fields.Many2one('res.user', string="Quote to Order")
    