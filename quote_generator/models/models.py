# -*- coding: utf-8 -*-

from odoo import models, fields, api

class quote_generator(models.Model):
    _inherit = "sale.order"
    _name = "sale.order"
    
    #transaction_ids = fields.Many2many('sale_order_id', 'transaction_id',
     #                                  string='Transactions', copy=False, readonly=True)
    #def action_quotation_sent(self):
     #   if self.filtered(lambda so: so.state != 'draft'):
      #      raise UserError(_('Custom Error Message to Prove Sucsess'))
       # for order in self:
        #    order.message_subscribe(partner_ids=order.partner_id.ids)
        #self.write({'state': 'sent'})
            