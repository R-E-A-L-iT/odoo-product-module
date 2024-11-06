from odoo import models, fields, api

class Commissions(models.Model):
    _name = 'procom.commission'
    _description = 'Commissions Records'
    
    state = fields.Selection(
        [('unpaid', 'Unpaid'), ('partially_paid', 'Partially Paid'), ('fully_paid', 'Fully Paid')],
        string="Status", default='unpaid', required=True
    )
    
    name = fields.Char(string="Commission Name", required=True)
    related_lead = fields.Many2one('crm.lead', string="Related Lead")
    related_order = fields.Many2one('sale.order', string="Related Order", required="True")
    # domain=[('move_type', '=', 'out_invoice')]
    related_invoice = fields.Many2one('account.move', string="Related Invoice")
    related_partner = fields.Many2one('res.partner', string="Customer", compute="_compute_related_partner", store=True)
    
    # sales roles
    new_customer = fields.Many2one('res.users', string="Contact New Customer")
    logged_lead = fields.Many2one('res.users', string="Logged Lead")
    developed_lead = fields.Many2one('res.users', string="Developed Opportunity")
    performed_demo = fields.Many2one('res.users', string="Performed Demo")
    quote_to_order = fields.Many2one('res.users', string="Quote to Order")
    
    currency_id = fields.Many2one(
        'res.currency', 
        string="Currency", 
        compute="_compute_currency_id", 
        store=True
    )

    # commission fields
    new_customer_commission = fields.Monetary(string="New Customer Commission", currency_field="currency_id", compute="_compute_commissions", store=True)
    logged_lead_commission = fields.Monetary(string="Logged Lead Commission", currency_field="currency_id", compute="_compute_commissions", store=True)
    developed_lead_commission = fields.Monetary(string="Developed Opportunity Commission", currency_field="currency_id", compute="_compute_commissions", store=True)
    performed_demo_commission = fields.Monetary(string="Performed Demo Commission", currency_field="currency_id", compute="_compute_commissions", store=True)
    quote_to_order_commission = fields.Monetary(string="Quote to Order Commission", currency_field="currency_id", compute="_compute_commissions", store=True)
    
    # computation fields
    sales_price = fields.Monetary(string="Sales Price (before tax)", currency_field="currency_id", compute="_compute_sales_price", store=True)
    reality_cost = fields.Monetary(string="Reality Cost", currency_field="currency_id")
    shipping_cost = fields.Monetary(string="Shipping Cost", currency_field="currency_id")
    reality_margin = fields.Monetary(string="Reality Margin", currency_field="currency_id", compute="_compute_reality_margin", store=True)

    @api.depends('related_order')
    def _compute_currency_id(self):
        default_currency = self.env.ref('base.CAD')
        for record in self:
            record.currency_id = record.related_order.currency_id or default_currency
            
    @api.depends('related_order')
    def _compute_sales_price(self):
        for record in self:
            record.sales_price = record.related_order.amount_untaxed if record.related_order else 0.0
            
    @api.depends('related_order')
    def _compute_related_partner(self):
        for record in self:
            record.related_partner = record.related_order.partner_id if record.related_order else False

    @api.depends('sales_price', 'reality_cost', 'shipping_cost')
    def _compute_reality_margin(self):
        for record in self:
            record.reality_margin = record.sales_price - record.reality_cost - record.shipping_cost
            
    @api.depends('reality_margin', 'new_customer', 'logged_lead', 'developed_lead', 'performed_demo', 'quote_to_order')
    def _compute_commissions(self):
        for record in self:
            record.new_customer_commission = (
                0.05 * record.reality_margin if record.new_customer and record.new_customer.name != "Derek deBlois" else 0.0
            )
            record.logged_lead_commission = (
                0.05 * record.reality_margin if record.logged_lead and record.logged_lead.name != "Derek deBlois" else 0.0
            )
            record.developed_lead_commission = (
                0.15 * record.reality_margin if record.developed_lead and record.developed_lead.name != "Derek deBlois" else 0.0
            )
            record.performed_demo_commission = (
                0.10 * record.reality_margin if record.performed_demo and record.performed_demo.name != "Derek deBlois" else 0.0
            )
            record.quote_to_order_commission = (
                0.05 * record.reality_margin if record.quote_to_order and record.quote_to_order.name != "Derek deBlois" else 0.0
            )
            
    def action_set_unpaid(self):
        self.state = 'unpaid'

    def action_set_partially_paid(self):
        self.state = 'partially_paid'

    def action_set_fully_paid(self):
        self.state = 'fully_paid'
        
        

class AccountMove(models.Model):
    _inherit = 'account.move'

    source_order = fields.Many2one('sale.order', string="Source Order", help="The sales order from which this invoice was generated, if any.")

    @api.model
    def create(self, vals):
        invoice = super(AccountMove, self).create(vals)
        if invoice.invoice_origin:
            sale_order = self.env['sale.order'].search([('name', '=', invoice.invoice_origin)], limit=1)
            if sale_order:
                invoice.source_order = sale_order.id
                _logger.info(f"Setting source_order for invoice {invoice.name} to sale order {sale_order.name}")
        return invoice
    
    def _create_commission_record(self):
        commission = self.env['procom.commission']
        for invoice in self:
            if invoice.source_order:
                _logger.info(f"Creating commission record for invoice {invoice.name} with source order {invoice.source_order.name}")
                commission.create({
                    'name': f"Commission for Invoice {invoice.name}",
                    'related_invoice': invoice.id,
                    'related_order': invoice.source_order.id,
                })
            else:
                _logger.info(f"No source order found for invoice {invoice.name}. Commission record not created.")