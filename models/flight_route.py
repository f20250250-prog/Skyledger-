from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
class FlightRoute(models.Model):
    _name = 'flight.route'
    _description = 'Flight Route'
    _order = 'name'
    name = fields.Char(
        string='Route Code', required=True, copy=False,
        help='e.g. LOS-DXB, automatically computed if left blank'
    )
    origin_airport_id = fields.Many2one(
        'aviation.airport', string='Origin Airport',
        required=True, ondelete='restrict', index=True
    )
    destination_airport_id = fields.Many2one(
        'aviation.airport', string='Destination Airport',
        required=True, ondelete='restrict', index=True
    )
    active = fields.Boolean(default=True)
    distance_nm = fields.Float(
        string='Distance (Nautical Miles)', digits=(10, 2),
        help='Great-circle distance in nautical miles'
    )
    waypoint_ids = fields.One2many(
        'flight.route.waypoint', 'route_id', string='Waypoints'
    )
    base_operational_cost = fields.Monetary(
        string='Base Operational Cost (USD)',
        currency_field='currency_id',
        help='Fixed + variable costs per flight excluding fuel surcharge'
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        default=lambda self: self.env.ref('base.USD')
    )
    fuel_burn_gallons = fields.Float(
        string='Est. Fuel Burn (Gallons)', digits=(10, 2),
        help='Average Jet A-1 consumption per flight on this route'
    )
    seat_class_ids = fields.One2many(
        'flight.seat.class', 'route_id', string='Seat Classes'
    )
    schedule_ids = fields.One2many(
        'flight.schedule', 'route_id', string='Schedules'
    )
    schedule_count = fields.Integer(
        string='Schedules', compute='_compute_schedule_count', store=True
    )
    lead_ids = fields.Many2many(
        'crm.lead', 'crm_lead_flight_route_rel',
        'route_id', 'lead_id',
        string='Tracked Opportunities'
    )
    _sql_constraints = [
        ('unique_route', 'UNIQUE(origin_airport_id, destination_airport_id)',
         'A route between these two airports already exists.'),
    ]
    @api.constrains('origin_airport_id', 'destination_airport_id')
    def _check_different_airports(self):
        for rec in self:
            if rec.origin_airport_id == rec.destination_airport_id:
                raise ValidationError(_('Origin and Destination airports must differ.'))
    @api.depends('schedule_ids')
    def _compute_schedule_count(self):
        for rec in self:
            rec.schedule_count = len(rec.schedule_ids)
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == '/':
                origin = self.env['aviation.airport'].browse(vals.get('origin_airport_id'))
                dest = self.env['aviation.airport'].browse(vals.get('destination_airport_id'))
                vals['name'] = f'{origin.iata_code}-{dest.iata_code}'
        return super().create(vals_list)
    def name_get(self):
        return [
            (rec.id, f'{rec.name} ({rec.origin_airport_id.city} → {rec.destination_airport_id.city})')
            for rec in self
        ]
class FlightRouteWaypoint(models.Model):
    _name = 'flight.route.waypoint'
    _description = 'Route Waypoint'
    _order = 'sequence, id'
    route_id = fields.Many2one('flight.route', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    waypoint_name = fields.Char(string='Waypoint / VOR / Fix', required=True)
    latitude = fields.Float(string='Latitude', digits=(10, 7))
    longitude = fields.Float(string='Longitude', digits=(10, 7))
    altitude_ft = fields.Integer(string='Altitude (ft)')
    notes = fields.Char(string='ATC Notes')