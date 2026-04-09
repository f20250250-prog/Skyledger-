import logging
from odoo import api, fields, models, _
_logger = logging.getLogger(__name__)
class CrmLeadAviationExtension(models.Model):
    _inherit = 'crm.lead'
    tracked_route_ids = fields.Many2many(
        'flight.route',
        'crm_lead_flight_route_rel',
        'lead_id', 'route_id',
        string='Tracked Routes'
    )
    preferred_cabin_class = fields.Selection([
        ('economy', 'Economy'),
        ('premium_economy', 'Premium Economy'),
        ('business', 'Business'),
        ('first', 'First Class'),
    ], string='Preferred Class', default='economy')
    price_alert_threshold = fields.Float(
        string='Alert if price drops below ($)',
        help='Send a price drop alert when ticket price falls below this value'
    )
    last_alerted_price = fields.Float(string='Last Alerted Price', readonly=True)
    @api.model
    def _cron_check_price_drop_alerts(self):
        template = self.env.ref(
            'aviation_erp.mail_template_price_drop_alert',
            raise_if_not_found=False
        )
        if not template:
            _logger.warning('Skyledger: Price Drop Alert template not found.')
            return
        open_leads = self.search([
            ('active', '=', True),
            ('stage_id.is_won', '=', False),
            ('tracked_route_ids', '!=', False),
            ('price_alert_threshold', '>', 0),
        ])
        for lead in open_leads:
            for route in lead.tracked_route_ids:
                upcoming_ticket = self.env['flight.ticket'].search([
                    ('route_id', '=', route.id),
                    ('cabin_class', '=', lead.preferred_cabin_class),
                    ('state', '=', 'draft'),
                    ('schedule_id.state', 'in', ('confirmed', 'boarding')),
                ], limit=1, order='final_price asc')
                if not upcoming_ticket:
                    continue
                current_price = upcoming_ticket.final_price
                threshold = lead.price_alert_threshold
                last_alerted = lead.last_alerted_price
                if current_price <= threshold and current_price != last_alerted:
                    _logger.info(
                        'Skyledger: Price Drop Alert for lead %s – '
                        'Route %s, Price $%.2f (threshold $%.2f)',
                        lead.name, route.name, current_price, threshold
                    )
                    template.send_mail(lead.id, force_send=True, email_values={
                        'email_to': lead.email_from,
                    })
                    lead.last_alerted_price = current_price
                    lead.message_post(
                        body=_(
                            '📧 Price Drop Alert sent – %s at $%.2f (was $%.2f)',
                            route.name, current_price, last_alerted or threshold
                        )
                    )