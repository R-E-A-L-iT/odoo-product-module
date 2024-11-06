from odoo import models, fields, api

class Commissions(models.Model):
    _name = 'procom.commission'
    _description = 'Commissions Records'
    
    name = fields.Char(string="Commission Name", required=True)
    related_lead = fields.Many2one('crm.lead', string="Related Lead")
    related_order = fields.Many2one('sale.order', string="Related Order", required="True")
    # domain=[('move_type', '=', 'out_invoice')]
    related_invoice = fields.Many2one('account.move', string="Related Invoice")
    
    # test_user = fields.Many2one('res.users', string="Assigned User")
    
    # sales roles
    new_customer = fields.Many2one('res.users', string="Contact New Customer")
    logged_lead = fields.Many2one('res.users', string="Logged Lead")
    developed_lead = fields.Many2one('res.users', string="Developed Opportunity")
    performed_demo = fields.Many2one('res.users', string="Performed Demo")
    quote_to_order = fields.Many2one('res.users', string="Quote to Order")
    
    currency_id = fields.Many2one(
        'res.currency', 
        string="Currency", 
        compute="_compute_currency_id", 
        store=True
    )

    new_customer_commission = fields.Monetary(string="New Customer Commission", currency_field="currency_id")
    logged_lead_commission = fields.Monetary(string="Logged Lead Commission", currency_field="currency_id")
    developed_lead_commission = fields.Monetary(string="Developed Opportunity Commission", currency_field="currency_id")
    performed_demo_commission = fields.Monetary(string="Performed Demo Commission", currency_field="currency_id")
    quote_to_order_commission = fields.Monetary(string="Quote to Order Commission", currency_field="currency_id")

    @api.depends('related_order')
    def _compute_currency_id(self):
        default_currency = self.env.ref('base.CAD')
        for record in self:
            record.currency_id = record.related_order.currency_id or default_currency
    