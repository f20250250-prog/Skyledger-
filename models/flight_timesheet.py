                       

"""
aviation_erp/models/flight_timesheet.py
Sprint 3 – Turnaround Timesheets
Extends account.analytic.line (hr_timesheet) to link ground staff
labour entries directly to a flight.schedule.
Also adds a helper to compute per-flight labour cost breakdowns.
"""

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

        """Auto-fill the analytic account from the flight's route analytic account."""

        if self.flight_schedule_id:

            route = self.flight_schedule_id.route_id

            if route and hasattr(route, 'analytic_account_id') and route.analytic_account_id:

                self.account_id = route.analytic_account_id

