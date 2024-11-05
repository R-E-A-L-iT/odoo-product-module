from odoo import models, fields

class Commissions(models.Model):
    _name = 'procom.commission'
    _description = 'Commissions Records'

    name = fields.Char(string="Commission Name", required=True)
    amount = fields.Float(string="Amount")
    
    invoice_id = fields.Many2one('account.move', string="Invoice", domain=[('move_type', '=', 'out_invoice')], required=True)
    # partner_id = fields.Many2one(related='invoice_id.partner_id', string="Customer", store=True, readonly=True)
    # invoice_date = fields.Date(related='invoice_id.invoice_date', string="Invoice Date", store=True)
    
    @api.model
    def create_commission_for_all_invoices(self):
        # Fetch all customer invoices
        invoices = self.env['account.move'].search([('move_type', '=', 'out_invoice')])
        
        # Loop through the invoices and create commission records
        for invoice in invoices:
            # Check if a commission record already exists for the invoice
            if not self.search([('invoice_id', '=', invoice.id)]):
                self.create({
                    'invoice_id': invoice.id,
                })

    # Action to clear all commission records
    @api.model
    def clear_commission_records(self):
        # Remove all records from the commission model
        self.search([]).unlink()