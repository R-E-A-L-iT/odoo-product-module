# pro_expenses/models/bank_statement_line.py
from odoo import models, fields, api, _

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    def action_transfer_expense(self):
        self.ensure_one()

        partner = self.env['res.partner'].search([
            ('name', '=', 'R-E-A-L.iT U.S. Inc'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({
                'name': 'R-E-A-L.iT U.S. Inc',
                'company_id': self.company_id.id,
                'is_company': True,
            })

        invoice = self.env['account.move'].create({
            'partner_id': partner.id,
            'move_type': 'out_invoice',
            'company_id': self.company_id.id,
            'invoice_date': fields.Date.context_today(self),
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Invoice'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
            'target': 'current',
        }