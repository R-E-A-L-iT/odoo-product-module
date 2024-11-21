from odoo import models, fields, _

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    def action_transfer_expense(self):
        """Generate and confirm a customer invoice with a matching vendor bill for inter-company accounting."""
        self.ensure_one()  # Ensure the method is called on a single record

        # Get the partner for the invoice (R-E-A-L.iT U.S. Inc)
        partner_invoice = self.env['res.partner'].browse(54508)
        if not partner_invoice.exists():
            raise ValueError(_("The partner with ID 54508 (R-E-A-L.iT U.S. Inc) does not exist."))

        # Get the partner for the bill (r-e-a-l.it solutions)
        partner_bill = self.env['res.partner'].search([
            ('name', '=', 'r-e-a-l.it solutions'),
            ('company_id', '=', partner_invoice.company_id.id)  # Ensure it's in the correct company
        ], limit=1)
        if not partner_bill:
            raise ValueError(_("The partner 'r-e-a-l.it solutions' does not exist in the target company."))

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

        # Create the customer invoice in the current company
        invoice = self.env['account.move'].create({
            'partner_id': partner_invoice.id,
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

        # Update the note field (narration) on the bank statement line
        self.narration = _("Invoice created: %s") % (invoice.name or _("Unknown Invoice"))

        # Switch to the target company (R-E-A-L.iT U.S. Inc) to create the vendor bill
        target_company = partner_invoice.company_id
        current_company = self.env.company
        self.env.company = target_company

        try:
            # Create the vendor bill in the target company
            bill = self.env['account.move'].create({
                'partner_id': partner_bill.id,
                'move_type': 'in_invoice',  # Vendor Bill
                'company_id': target_company.id,
                'invoice_date': fields.Date.context_today(self),
            })

            # Add a bill line with the same account and amount as the invoice
            self.env['account.move.line'].create({
                'move_id': bill.id,
                'account_id': inter_company_account.id,
                'name': 'Inter-Company Expense',  # Description for the line
                'quantity': 1.0,
                'price_unit': abs(self.amount),  # Use the same amount as the invoice
            })

            # Confirm the bill
            bill.action_post()

        finally:
            # Switch back to the original company
            self.env.company = current_company

        return True
