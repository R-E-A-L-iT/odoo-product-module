from odoo import models, fields, api, exceptions

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    is_lead_logged_with_leica = fields.Boolean(default=False, string="Logged with Leica")

    def action_log_lead_with_leica(self):
        for record in self:
            # Check if the action has already been performed
            if record.is_lead_logged_with_leica:
                raise exceptions.UserError("This opportunity has already been logged with Leica.")

            # Ensure all required fields are available
            missing_fields = []
            if not record.phone:
                missing_fields.append('Phone')
            if not record.email_from:
                missing_fields.append('Email Address')
            if not record.partner_id:
                missing_fields.append('Company Name')
            if not record.expected_revenue:
                missing_fields.append('Expected Amount')
            if not record.user_id:
                missing_fields.append('Salesperson')

            if missing_fields:
                raise exceptions.UserError(
                    f"The following required fields are missing: {', '.join(missing_fields)}. Please complete them before proceeding."
                )

            # Compose the email body
            email_body = f"""
            Lead Details Logged with Leica:

            Phone: {record.phone}
            Email Address: {record.email_from}
            Company Name: {record.partner_id.name}
            Expected Amount: {record.expected_revenue}
            Salesperson: {record.user_id.name}
            """

            # Send the email
            mail_values = {
                'subject': f"Lead Logged: {record.name}",
                'body_html': email_body,
                'email_to': 'leadgen@r-e-a-l.it',
                'email_from': record.env.user.email or 'no-reply@yourdomain.com',
            }

            mail = self.env['mail.mail'].create(mail_values)
            mail.send()

            # Mark the lead as logged
            record.is_lead_logged_with_leica = True
