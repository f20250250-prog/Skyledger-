from odoo import api, fields, models, _

class AccountAnalyticLineFlightExtension(models.Model):
    _inherit = 'account.analytic.line'

    flight_schedule_id = fields.Many2one(
        'flight.schedule', string='Flight Schedule',
        index=True, ondelete='set null',
        help='Link this timesheet entry to a specific turnaround / flight'
    )
    ground_staff_role = fields.Selection([
        ('ramp', 'Ramp Agent'),
        ('fueling', 'Fueling Crew'),
        ('catering', 'Catering'),
        ('cleaning', 'Cabin Cleaning'),
        ('baggage', 'Baggage Handler'),
        ('de_icing', 'De-Icing Crew'),
        ('engineering', 'Line Maintenance'),
        ('dispatcher', 'Flight Dispatcher'),
        ('other', 'Other'),
    ], string='Ground Role')

    @api.onchange('flight_schedule_id')
    def _onchange_flight_schedule(self):
        if self.flight_schedule_id:
            route = self.flight_schedule_id.route_id
            if route and hasattr(route, 'analytic_account_id') and route.analytic_account_id:
                self.account_id = route.analytic_account_id