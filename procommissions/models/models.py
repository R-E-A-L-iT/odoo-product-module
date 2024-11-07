import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

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
    
    # performed demo table
    demo_role_ids = fields.One2many('procom.demo.role', 'commission_id', string="Demo Roles")
    
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
        
    @api.model
    def create(self, vals):
        commission = super(Commissions, self).create(vals)
        
        # Automatically populate demo roles from products in the related order (quote)
        if commission.related_order:
            demo_roles = []
            for line in commission.related_order.order_line:
                demo_roles.append((0, 0, {
                    'product_id': line.product_id.id,
                    'sold_price': line.price_unit,
                }))
            commission.update({'demo_role_ids': demo_roles})
        
        return commission
        

class AccountMove(models.Model):
    _inherit = 'account.move'

    source_order = fields.Many2one('sale.order', string="Source Order", help="The sales order from which this invoice was generated, if any.")

    @api.model
    def create(self, vals):
        invoice = super(AccountMove, self).create(vals)
        
        invoice._create_commission_record()

        return invoice
    
    def _create_commission_record(self):
        commission = self.env['procom.commission']
        for invoice in self:
            if invoice.invoice_origin:
                sale_order = self.env['sale.order'].search([('name', '=', invoice.invoice_origin)], limit=1)
                if sale_order:
                    
                    related_lead = sale_order.opportunity_id if 'opportunity_id' in sale_order._fields else None
                    
                    if related_lead:
                        
                        # commission roles
                        logged_lead_user = related_lead.create_uid if related_lead else None
                        developed_lead_user = related_lead.user_id if related_lead else None
                        quote_to_order_user = sale_order.user_id if sale_order.user_id else None
                        
                        commission.create({
                            'name': f"Commission for {sale_order.name}",
                            'related_invoice': invoice.id,
                            'related_order': sale_order.id,
                            'related_lead': related_lead.id if related_lead else False,
                            'logged_lead': logged_lead_user.id if logged_lead_user else False,
                            'developed_lead': developed_lead_user.id if developed_lead_user else False,
                            'quote_to_order': quote_to_order_user.id if quote_to_order_user else False,
                        })
                    else:
                        _logger.info(f"No related opportunity found for invoice {invoice.name}.")       
                else:
                    _logger.info(f"No related sales order found for invoice {invoice.name}.")
            else:
                _logger.info(f"No invoice origin for invoice {invoice.name}. No commission created.")
                
class lead(models.Model):
    _inherit = 'crm.lead'

    converted_by = fields.Many2one('res.users', string="Converted By", readonly=True,  help="The user who converted this lead into an opportunity.")

    @api.model
    def write(self, vals):
        """Set converted_by when the stage is changed to 'Opportunity'."""
        if 'stage_id' in vals:
            opportunity_stage = self.env.ref('crm.stage_lead2')
            for record in self:
                if vals['stage_id'] == opportunity_stage.id and not record.converted_by:
                    vals['converted_by'] = self.env.user.id
        return super(lead, self).write(vals)
    
    
class demo_lines(models.Model):
    _name = 'procom.demo.lines'
    _description = 'Model for the demo roles table on commission reports'

    commission_id = fields.Many2one('procom.commission', string="Commission", required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string="Product", required=True)
    sold_price = fields.Float(string="Sold Price", required=True)
    purchased_price = fields.Float(string="Purchased Price")
    performed_demo = fields.Many2one('res.users', string="Performed Demo")
    commission = fields.Monetary(string="Commission", compute="_compute_commission", currency_field="currency_id", store=True)

    currency_id = fields.Many2one(related="commission_id.currency_id", store=True, readonly=True)

    @api.depends('sold_price', 'purchased_price', 'performed_demo')
    def _compute_commission(self):
        for record in self:
            if record.performed_demo:
                record.commission = (record.sold_price - (record.purchased_price or 0.0)) * 0.10
            else:
                record.commission = 0.0