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
            
        inter_company_account = self.env['account.account'].search([
            ('name', '=', 'Inter-Company Expenses'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        if not inter_company_account:
            inter_company_account = self.env['account.account'].create({
                'name': 'Inter-Company Expenses',
                'code': '99999',  # Example account code; adjust as needed
                'user_type_id': self.env.ref('account.data_account_type_expenses').id,
                'company_id': self.company_id.id,
            })

        invoice = self.env['account.move'].create({
            'partner_id': partner.id,
            'move_type': 'out_invoice',  # Customer Invoice
            'company_id': self.company_id.id,
            'invoice_date': fields.Date.context_today(self),
        })
        
        self.env['account.move.line'].create({
            'move_id': invoice.id,
            'account_id': inter_company_account.id,
            'name': 'Inter-Company Expense',  # Description for the line
            'quantity': 1.0,
            'price_unit': 0.0,  # No cost by default
        })
        
        note_message = _(
            "Invoice automatically generated as a transferred expense from %s"
        ) % (self.display_name or _("Unknown Document"))
        invoice.message_post(body=note_message)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Invoice'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
            'target': 'current',
        }