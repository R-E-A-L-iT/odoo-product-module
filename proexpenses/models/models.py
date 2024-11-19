# pro_expenses/models/bank_statement_line.py
from odoo import models, fields

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    def action_transfer_expense(self):
        # Placeholder function for the button action
        return True