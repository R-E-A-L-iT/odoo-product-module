
from odoo import models, fields, api, _


class ProjectTask(models.Model):
    _inherit = 'project.task'

    diagram = fields.Text(string='Diagram')

