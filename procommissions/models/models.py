from odoo import models, fields

class Commissions(models.Model):
    _name = 'procom.commission'
    _description = 'Commissions Records'

    name = fields.Char(string="Commission Name", required=True)
    amount = fields.Float(string="Amount")