from odoo import models, fields, api, _


class ExpenseTransferWizard(models.TransientModel):
    _name = 'expense.transfer.wizard'
    _description = 'Expense Transfer Wizard'

    # select comany excluding current company
    company_id = fields.Many2one(
        'res.company', 
        string='Select Company', 
        required=True,
        domain=[('id', '!=', lambda self: self.env.company.id)]
    )

    def action_confirm_transfer(self):

        active_id = self.env.context.get('active_id')
        bank_statement_line = self.env['account.bank.statement.line'].browse(active_id)

        if bank_statement_line:
            bank_statement_line.action_transfer_expense(company_id=self.company_id)


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    def action_transfer_expense(self, company_id=None):
        self.ensure_one()

        # transfer occurs between two companies
        # company 1 and company 2
        # expense transfer is triggered in company 1
        # create an invoice in company 1 addressed to company 2 for expense
        # create bill in company 2 matching the invoice from company 1

        if not company_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'expense.transfer.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {'active_id': self.id},
            }

        # Get the partner by ID
        partner = company_id.partner_id
        if not partner.exists():
            raise ValueError(_("The partner with ID 54508 (R-E-A-L.iT U.S. Inc) does not exist."))

        # Get or create the "Inter-Company Expenses" account
        inter_company_account = self.env['account.account'].search([
            ('name', '=', 'Inter-Company Expenses'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        if not inter_company_account:
            inter_company_account = self.env['account.account'].create({
                'name': 'Inter-Company Expenses',
                'code': '99999',
                'account_type': 'expense',
                'company_id': self.company_id.id,
            })

        # create the customer invoice
        invoice = self.env['account.move'].create({
            'partner_id': partner.id,
            'move_type': 'out_invoice',
            'company_id': self.company_id.id,
            'invoice_date': fields.Date.context_today(self),
        })

        # create order line on customer invoice
        self.env['account.move.line'].create({
            'move_id': invoice.id,
            'account_id': inter_company_account.id,
            'name': 'Inter-Company Expense',
            'quantity': 1.0,
            'price_unit': abs(self.amount),
        })

        # confirm the invoice
        invoice.action_post()

        # Update the note field (narration) on the bank statement line
        self.narration = _("Invoice created: %s") % (invoice.name or _("Unknown Invoice"))

        # send notification to user that transfer has been created succesfully
        # add button to view bill or view invoice

        return True