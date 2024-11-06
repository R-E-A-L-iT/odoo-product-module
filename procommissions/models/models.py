from odoo import models, fields, api

class Commissions(models.Model):
    _name = 'procom.commission'
    _description = 'Commissions Records'
    
    name = fields.Char(string="Commission Name", required=True)
    related_lead = fields.Many2one('crm.lead', string="Related Lead")
    related_order = fields.Many2one('sale.order', string="Related Order", required="True")
    # domain=[('move_type', '=', 'out_invoice')]
    related_invoice = fields.Many2one('account.move', string="Related Invoice")
    related_partner = fields.Many2one('res.partner', string="Customer", readonly=True)
    
    
    # @api.onchange('related_order')
    # def _onchange_related_order(self):
    #     """Auto-fill or clear dependent fields based on related_order selection."""
    #     if self.related_order:
    #         _logger.info(f"Setting related fields based on related_order: {self.related_order.id}")
    #         # If related_order is selected, populate other fields as needed
    #         # For example, partner_id if it were still included:
    #         # self.partner_id = self.related_order.partner_id
    #     else:
    #         _logger.info("Clearing dependent fields since related_order is empty.")
    #         # Clear any fields that depend on related_order if it's empty
    #         self.related_invoice = False
    #         self.related_lead = False
    
    
    # @api.onchange('related_order')
    # def _onchange_related_order(self):
    #     if self.related_order:
    #         partner = self.related_order.partner_id
    #         self.partner_id = partner
    #     else:
    #         self.partner_id = False


    # name = fields.Char(string="Commission Name", required=True)
    # amount = fields.Float(string="Amount")
    
    # invoice_id = fields.Many2one('account.move', string="Invoice", domain=[('move_type', '=', 'out_invoice')], required=True)
    # partner_id = fields.Many2one(related='invoice_id.partner_id', string="Customer", store=True, readonly=True)
    # invoice_date = fields.Date(related='invoice_id.invoice_date', string="Invoice Date", store=True)
    
    # @api.model
    # def create_commission_for_all_invoices(self):
    #     # Fetch all customer invoices
    #     invoices = self.env['account.move'].search([('move_type', '=', 'out_invoice')])
        
    #     # Loop through the invoices and create commission records
    #     for invoice in invoices:
    #         # Check if a commission record already exists for the invoice
    #         if not self.search([('invoice_id', '=', invoice.id)]):
    #             self.create({
    #                 'invoice_id': invoice.id,
    #             })

    # # Action to clear all commission records
    # @api.model
    # def clear_commission_records(self):
    #     # Remove all records from the commission model
    #     self.search([]).unlink()