from odoo import models, fields, _

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    def action_transfer_expense(self):
        """Generate and confirm a customer invoice with an order line assigned to Inter-Company Expenses."""
        self.ensure_one()  # Ensure the method is called on a single record

        # Get or create the partner
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

        # Get or create the "Inter-Company Expenses" account
        inter_company_account = self.env['account.account'].search([
            ('name', '=', 'Inter-Company Expenses'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        if not inter_company_account:
            inter_company_account = self.env['account.account'].create({
                'name': 'Inter-Company Expenses',
                'code': '99999',  # Example account code; adjust as needed
                'account_type': 'expense',  # Explicitly mark as expense type
                'company_id': self.company_id.id,
            })

        # Create the customer invoice
        invoice = self.env['account.move'].create({
            'partner_id': partner.id,
            'move_type': 'out_invoice',  # Customer Invoice
            'company_id': self.company_id.id,
            'invoice_date': fields.Date.context_today(self),
        })

        # Add an order line with the absolute value of the bank statement line amount
        self.env['account.move.line'].create({
            'move_id': invoice.id,
            'account_id': inter_company_account.id,
            'name': 'Inter-Company Expense',  # Description for the line
            'quantity': 1.0,
            'price_unit': abs(self.amount),  # Use the absolute value of the bank statement line amount
        })

        # Confirm the invoice
        invoice.action_post()

        # Log a note on the invoice
        note_message = _(
            "Invoice automatically generated and confirmed as a transferred expense from %s"
        ) % (self.display_name or _("Unknown Document"))
        invoice.message_post(body=note_message)

        # Return an action to open the invoice
        return {
            'type': 'ir.actions.act_window',
            'name': _('Customer Invoice'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
            'target': 'current',
        }
