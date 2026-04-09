import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

FLIGHT_STATES = [
    ('draft', 'Draft'),
    ('confirmed', 'Confirmed'),
    ('boarding', 'Boarding'),
    ('airborne', 'Airborne'),
    ('landed', 'Landed'),
    ('completed', 'Completed'),
    ('cancelled', 'Cancelled'),
]

class FlightSchedule(models.Model):
    _name = 'flight.schedule'
    _description = 'Flight Schedule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'departure_datetime desc'
    _rec_name = 'flight_number'

    flight_number = fields.Char(
        string='Flight Number', required=True, copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('flight.schedule')
    )
    route_id = fields.Many2one(
        'flight.route', string='Route', required=True, ondelete='restrict'
    )
    state = fields.Selection(
        FLIGHT_STATES, string='Status', default='draft',
        tracking=True, index=True
    )

    vehicle_id = fields.Many2one(
        'fleet.vehicle', string='Aircraft', required=True,
        domain="[('aviation_type', '!=', False)]",
        ondelete='restrict', tracking=True
    )
    aircraft_registration = fields.Char(
        related='vehicle_id.license_plate', string='Registration', store=True
    )

    departure_datetime = fields.Datetime(
        string='Departure (UTC)', required=True, tracking=True
    )
    arrival_datetime = fields.Datetime(
        string='Arrival (UTC)', required=True, tracking=True
    )
    block_time_hours = fields.Float(
        string='Block Time (hrs)', compute='_compute_block_time', store=True
    )
    is_red_eye = fields.Boolean(
        string='Red-Eye Flight', compute='_compute_is_red_eye', store=True,
        help='Departure between 00:00 and 04:00 UTC'
    )

    partner_latitude = fields.Float(
        string='Origin Latitude', digits=(10, 7),
        related='route_id.origin_airport_id.partner_latitude', store=True
    )
    partner_longitude = fields.Float(
        string='Origin Longitude', digits=(10, 7),
        related='route_id.origin_airport_id.partner_longitude', store=True
    )

    total_seats = fields.Integer(
        string='Total Seats', related='vehicle_id.total_seats', store=True
    )
    seats_sold = fields.Integer(
        string='Seats Sold', compute='_compute_seats_sold', store=True
    )
    seats_available = fields.Integer(
        string='Seats Available', compute='_compute_seats_sold', store=True
    )
    occupancy_rate = fields.Float(
        string='Occupancy (%)', compute='_compute_seats_sold', store=True,
        digits=(5, 2)
    )

    ticket_ids = fields.One2many('flight.ticket', 'schedule_id', string='Tickets')
    ticket_count = fields.Integer(
        string='Tickets', compute='_compute_ticket_count', store=True
    )
    total_revenue = fields.Monetary(
        string='Total Revenue', compute='_compute_total_revenue',
        currency_field='currency_id', store=True
    )
    currency_id = fields.Many2one(
        'res.currency', default=lambda self: self.env.ref('base.USD')
    )

    cargo_weight_kg = fields.Float(string='Cargo Weight (kg)')
    expected_cargo_profit = fields.Monetary(
        string='Expected Cargo Profit', currency_field='currency_id'
    )

    weather_alert_active = fields.Boolean(
        string='Weather Alert', default=False, tracking=True,
        help='When active, adds an insurance surcharge to all tickets on this flight'
    )

    timesheet_ids = fields.One2many(
        'account.analytic.line', 'flight_schedule_id',
        string='Ground Staff Timesheets'
    )
    total_labour_cost = fields.Monetary(
        string='Labour Cost', compute='_compute_labour_cost',
        currency_field='currency_id', store=True
    )

    last_engine_temp_c = fields.Float(string='Last Engine Temp (°C)')
    last_fuel_level_pct = fields.Float(string='Last Fuel Level (%)')
    iot_alert = fields.Boolean(string='IoT Alert', default=False)

    rasm = fields.Float(
        string='RASM (USD/ASM)', compute='_compute_rasm_casm', store=True,
        help='Revenue per Available Seat Mile'
    )
    casm = fields.Float(
        string='CASM (USD/ASM)', compute='_compute_rasm_casm', store=True,
        help='Cost per Available Seat Mile'
    )

    @api.depends('departure_datetime', 'arrival_datetime')
    def _compute_block_time(self):
        for rec in self:
            if rec.departure_datetime and rec.arrival_datetime:
                delta = rec.arrival_datetime - rec.departure_datetime
                rec.block_time_hours = delta.total_seconds() / 3600
            else:
                rec.block_time_hours = 0.0

    @api.depends('departure_datetime')
    def _compute_is_red_eye(self):
        for rec in self:
            if rec.departure_datetime:
                hour = rec.departure_datetime.hour
                rec.is_red_eye = 0 <= hour < 4
            else:
                rec.is_red_eye = False

    @api.depends('ticket_ids', 'ticket_ids.state', 'total_seats')
    def _compute_seats_sold(self):
        for rec in self:
            confirmed_tickets = rec.ticket_ids.filtered(
                lambda t: t.state in ('confirmed', 'invoiced')
            )
            sold = len(confirmed_tickets)
            rec.seats_sold = sold
            rec.seats_available = max(0, (rec.total_seats or 0) - sold)
            rec.occupancy_rate = (sold / rec.total_seats * 100) if rec.total_seats else 0.0

    @api.depends('ticket_ids', 'ticket_ids.final_price', 'ticket_ids.state')
    def _compute_total_revenue(self):
        for rec in self:
            rec.total_revenue = sum(
                t.final_price for t in rec.ticket_ids
                if t.state in ('confirmed', 'invoiced')
            )

    @api.depends('ticket_ids')
    def _compute_ticket_count(self):
        for rec in self:
            rec.ticket_count = len(rec.ticket_ids)

    @api.depends('timesheet_ids', 'timesheet_ids.amount')
    def _compute_labour_cost(self):
        for rec in self:
            rec.total_labour_cost = abs(sum(rec.timesheet_ids.mapped('amount')))

    @api.depends('total_revenue', 'total_seats', 'route_id.distance_nm',
                 'route_id.base_operational_cost', 'total_labour_cost')
    def _compute_rasm_casm(self):
        for rec in self:
            asm = (rec.total_seats or 0) * (rec.route_id.distance_nm or 0)
            if asm:
                rec.rasm = rec.total_revenue / asm
                total_cost = (
                    rec.route_id.base_operational_cost
                    + rec.total_labour_cost
                )
                rec.casm = total_cost / asm
            else:
                rec.rasm = 0.0
                rec.casm = 0.0

    @api.constrains('departure_datetime', 'arrival_datetime')
    def _check_datetimes(self):
        for rec in self:
            if rec.arrival_datetime and rec.departure_datetime:
                if rec.arrival_datetime <= rec.departure_datetime:
                    raise ValidationError(_('Arrival must be after Departure.'))

    @api.constrains('vehicle_id', 'departure_datetime', 'arrival_datetime')
    def _check_aircraft_availability(self):
        for rec in self:
            if not (rec.vehicle_id and rec.departure_datetime and rec.arrival_datetime):
                continue
            conflict = self.search([
                ('id', '!=', rec.id),
                ('vehicle_id', '=', rec.vehicle_id.id),
                ('state', 'not in', ('cancelled',)),
                ('departure_datetime', '<', rec.arrival_datetime),
                ('arrival_datetime', '>', rec.departure_datetime),
            ])
            if conflict:
                raise ValidationError(_(
                    'Aircraft %s is already scheduled for flight %s during this period.',
                    rec.vehicle_id.name, conflict[0].flight_number
                ))

    def _check_maintenance_block(self):
        for rec in self:
            emergency_mo = self.env['maintenance.request'].search([
                ('vehicle_id', '=', rec.vehicle_id.id),
                ('maintenance_type', '=', 'emergency'),
                ('stage_id.done', '=', False),
            ], limit=1)
            if emergency_mo:
                raise UserError(_(
                    'Cannot confirm flight %s: Aircraft %s has an open Emergency '
                    'maintenance request "%s". Please resolve it first.',
                    rec.flight_number,
                    rec.vehicle_id.name,
                    emergency_mo.name,
                ))

    def action_confirm(self):
        self._check_maintenance_block()
        self.write({'state': 'confirmed'})
        self.message_post(body=_('Flight confirmed.'))

    def action_board(self):
        self.write({'state': 'boarding'})

    def action_depart(self):
        self.write({'state': 'airborne'})

    def action_land(self):
        self.write({'state': 'landed'})

    def action_complete(self):
        self.write({'state': 'completed'})
        self._post_flight_odometer_update()
        self.message_post(body=_('Flight completed. Post-flight checks triggered.'))

    def action_cancel(self):
        self.write({'state': 'cancelled'})
        self.message_post(body=_('Flight cancelled.'))

    def _post_flight_odometer_update(self):
        MAINTENANCE_THRESHOLD_NM = 50_000
        threshold = int(self.env['ir.config_parameter'].sudo().get_param(
            'aviation_erp.maintenance_threshold_nm',
            default=MAINTENANCE_THRESHOLD_NM,
        ))
        for rec in self:
            if not rec.vehicle_id or not rec.route_id.distance_nm:
                continue
            vehicle = rec.vehicle_id
            new_odometer = (vehicle.odometer or 0) + rec.route_id.distance_nm
            self.env['fleet.vehicle.odometer'].create({
                'vehicle_id': vehicle.id,
                'value': new_odometer,
                'date': fields.Date.today(),
            })
            _logger.info(
                'Skyledger: Updated odometer for %s to %.2f nm after flight %s',
                vehicle.name, new_odometer, rec.flight_number
            )
            if new_odometer >= threshold:
                existing = self.env['maintenance.request'].search([
                    ('vehicle_id', '=', vehicle.id),
                    ('maintenance_type', '=', 'preventive'),
                    ('stage_id.done', '=', False),
                ], limit=1)
                if not existing:
                    self.env['maintenance.request'].create({
                        'name': _(
                            'Scheduled Maintenance – %s (%.0f nm threshold)',
                            vehicle.name, threshold
                        ),
                        'vehicle_id': vehicle.id,
                        'maintenance_type': 'preventive',
                        'description': _(
                            'Auto-generated by Skyledger after flight %s. '
                            'Odometer: %.2f nm.',
                            rec.flight_number, new_odometer
                        ),
                        'request_date': fields.Date.today(),
                    })
                    rec.message_post(
                        body=_('⚠️ Maintenance threshold reached. Preventive maintenance request created.')
                    )

    def action_view_tickets(self):
        self.ensure_one()
        return {
            'name': _('Tickets for %s') % self.flight_number,
            'type': 'ir.actions.act_window',
            'res_model': 'flight.ticket',
            'view_mode': 'list,form',
            'domain': [('schedule_id', '=', self.id)],
            'context': {'default_schedule_id': self.id},
            'target': 'current',
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('flight_number') or vals['flight_number'] == '/':
                vals['flight_number'] = self.env['ir.sequence'].next_by_code('flight.schedule') or '/'
        return super().create(vals_list)