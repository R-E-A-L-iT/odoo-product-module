from odoo import models, fields, api, _


class ExpenseTransferWizard(models.TransientModel):
    _name = 'expense.transfer.wizard'
    _description = 'Expense Transfer Wizard'

    # select comany excluding current company
    company_id = fields.Many2one(
        'res.company', 
        string='Select Company', 
        required=True,
        domain=lambda self: [('id', '!=', self.env.company.id)]  # Correctly referencing the current company
    )

    def action_confirm_transfer(self):

        active_id = self.env.context.get('active_id')
        bank_statement_line = self.env['account.bank.statement.line'].browse(active_id)

        if bank_statement_line:
            bank_statement_line.action_transfer_expense(company_id=self.company_id)


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    # transfer occurs between two companies
    # company 1 and company 2
    # expense transfer is triggered in company 1
    # create an invoice in company 1 addressed to company 2 for expense
    # create bill in company 2 matching the invoice from company 1

    def action_transfer_expense(self, company_id=None):
        
        self.ensure_one()

        if not company_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'expense.transfer.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'active_id': self.id},
            }

        # create invoice
        invoice = self.env['account.move'].create({
            'partner_id': company_id.partner_id.id,
            'move_type': 'out_invoice',
            'invoice_line_ids': [(0, 0, {
                'name': 'Inter-Company Expense',
                'account_id': self.env.ref('account.data_account_type_expenses').id,
                'price_unit': abs(self.amount),
            })],
        })

        # create bill
        bill = self.env['account.move'].create({
            'partner_id': company_id.partner_id.id,
            'move_type': 'in_invoice',
            'invoice_line_ids': [(0, 0, {
                'name': 'Inter-Company Expense',
                'account_id': self.env.ref('account.data_account_type_expenses').id,
                'price_unit': abs(self.amount),
            })],
        })

        # push notification
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Transfer Complete',
                'message': 'The expense transfer has been completed successfully.',
                'type': 'success',
                'sticky': False,
                'buttons': [
                    {
                        'name': 'View Invoice',
                        'type': 'action',
                        'action': {
                            'type': 'ir.actions.act_window',
                            'res_model': 'account.move',
                            'view_mode': 'form',
                            'res_id': invoice.id,
                        },
                    },
                    {
                        'name': 'View Bill',
                        'type': 'action',
                        'action': {
                            'type': 'ir.actions.act_window',
                            'res_model': 'account.move',
                            'view_mode': 'form',
                            'res_id': bill.id,
                        },
                    },
                ],
            },
        }