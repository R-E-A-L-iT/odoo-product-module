from odoo import models, fields

class Commissions(models.Model):
    _name = 'procom.commission'
    _description = 'Commissions Records'

    name = fields.Char(string="Commission Name", required=True)
    amount = fields.Float(string="Amount")
    
    invoice_id = fields.Many2one('account.move', string="Invoice", domain=[('move_type', '=', 'out_invoice')], required=True)
    partner_id = fields.Many2one(related='invoice_id.partner_id', string="Customer", store=True)
    invoice_date = fields.Date(related='invoice_id.invoice_date', string="Invoice Date", store=True)