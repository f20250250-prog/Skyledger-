                       

"""
aviation_erp/models/fleet_extension.py
Sprint 3 – Fleet & Maintenance
Extends fleet.vehicle to add aviation-specific fields:
  - Aircraft type, registration, max range
  - Seat counts per cabin class
  - Maintenance threshold
  - IoT sensor device linkage
"""

from odoo import api, fields, models, _





AIRCRAFT_TYPES = [

    ('narrow_body', 'Narrow Body (e.g. B737, A320)'),

    ('wide_body', 'Wide Body (e.g. B777, A350)'),

    ('regional_jet', 'Regional Jet (e.g. E175, CRJ)'),

    ('turboprop', 'Turboprop'),

    ('cargo', 'Cargo Aircraft'),

    ('private', 'Business / Private Jet'),

]



class MaintenanceRequestAviationExtension(models.Model):

    _inherit = 'maintenance.request'



    vehicle_id = fields.Many2one(

        'fleet.vehicle', string='Aircraft',

        domain="[('is_aircraft', '=', True)]",

        ondelete='set null', index=True

    )

    aog_reason = fields.Char(string='AOG Reason')



class FleetVehicleAviationExtension(models.Model):

    _inherit = 'fleet.vehicle'



                                                                                

    aviation_type = fields.Selection(

        AIRCRAFT_TYPES, string='Aircraft Type',

        help='Leave empty for non-aviation fleet vehicles'

    )

    is_aircraft = fields.Boolean(

        string='Is Aircraft', compute='_compute_is_aircraft', store=True

    )

    manufacturer = fields.Char(string='Manufacturer', help='e.g. Boeing, Airbus, Embraer')

    aircraft_model = fields.Char(string='Aircraft Model', help='e.g. 737-800, A320neo')

    max_range_nm = fields.Float(string='Max Range (Nautical Miles)')

    cruise_speed_kts = fields.Integer(string='Cruise Speed (knots)')

    max_fuel_capacity_gal = fields.Float(string='Max Fuel Capacity (Gallons)')

    year_of_manufacture = fields.Integer(string='Year of Manufacture')



                                                                                

    seats_first = fields.Integer(string='First Class Seats', default=0)

    seats_business = fields.Integer(string='Business Seats', default=0)

    seats_premium_economy = fields.Integer(string='Premium Economy Seats', default=0)

    seats_economy = fields.Integer(string='Economy Seats', default=150)

    total_seats = fields.Integer(

        string='Total Seats', compute='_compute_total_seats', store=True

    )



                                                                                

    maintenance_threshold_nm = fields.Float(

        string='Maintenance Threshold (nm)',

        default=50_000,

        help='Auto-create maintenance request when odometer exceeds this value'

    )

    open_maintenance_count = fields.Integer(

        string='Open Maintenance Requests',

        compute='_compute_open_maintenance_count'

    )

    has_emergency_maintenance = fields.Boolean(

        string='Emergency Maintenance Open',

        compute='_compute_open_maintenance_count'

    )



                                                                              

                                                                          

    iot_engine_temp_device_id = fields.Char(string='Engine Temp Sensor ID')

    iot_fuel_level_device_id = fields.Char(string='Fuel Level Sensor ID')

    

    last_engine_temp_c = fields.Float(string='Engine Temp (°C)', readonly=True)

    last_fuel_level_pct = fields.Float(string='Fuel Level (%)', readonly=True)

    iot_last_update = fields.Datetime(string='Last IoT Update', readonly=True)

    iot_alert = fields.Boolean(

        string='IoT Alert Active',

        compute='_compute_iot_alert', store=True

    )



                                                                                 

    schedule_ids = fields.One2many(

        'flight.schedule', 'vehicle_id', string='Flight Schedules'

    )

    completed_flights = fields.Integer(

        string='Completed Flights', compute='_compute_completed_flights'

    )



                                                                                



    @api.depends('aviation_type')

    def _compute_is_aircraft(self):

        for rec in self:

            rec.is_aircraft = bool(rec.aviation_type)



    @api.depends('seats_first', 'seats_business', 'seats_premium_economy', 'seats_economy')

    def _compute_total_seats(self):

        for rec in self:

            rec.total_seats = (

                rec.seats_first

                + rec.seats_business

                + rec.seats_premium_economy

                + rec.seats_economy

            )



    def _compute_open_maintenance_count(self):

        for rec in self:

            requests = self.env['maintenance.request'].search([

                ('vehicle_id', '=', rec.id),

                ('stage_id.done', '=', False),

            ])

            rec.open_maintenance_count = len(requests)

            rec.has_emergency_maintenance = any(

                r.maintenance_type == 'emergency' for r in requests

            )



    def _compute_completed_flights(self):

        for rec in self:

            rec.completed_flights = self.env['flight.schedule'].search_count([

                ('vehicle_id', '=', rec.id),

                ('state', '=', 'completed'),

            ])



    @api.depends('last_engine_temp_c', 'last_fuel_level_pct')

    def _compute_iot_alert(self):

        ENGINE_TEMP_MAX = 900.0       

        FUEL_LEVEL_MIN = 10.0       

        for rec in self:

            rec.iot_alert = (

                rec.last_engine_temp_c > ENGINE_TEMP_MAX

                or (0 < rec.last_fuel_level_pct < FUEL_LEVEL_MIN)

            )



                                                                                



    def action_refresh_iot_sensors(self):

        """
        Polls IoT devices. 
        COMMUNITY VERSION: Uses simulation logic only.
        """

        import random

        for rec in self:

            if not rec.is_aircraft:

                continue



                                                          

                                                     

            rec.last_engine_temp_c = round(random.gauss(750, 50), 1)



                                                         

            rec.last_fuel_level_pct = round(random.uniform(20, 95), 1)



            rec.iot_last_update = fields.Datetime.now()



                                                          

            if rec.iot_alert:

                rec.message_post(

                    body=_(

                        '⚠️ IoT Alert: Engine Temp %.1f°C | Fuel Level %.1f%%',

                        rec.last_engine_temp_c, rec.last_fuel_level_pct

                    ),

                    subtype_xmlid='mail.mt_note'

                )



    def action_view_schedules(self):

        return {

            'type': 'ir.actions.act_window',

            'name': _('Flight Schedules'),

            'res_model': 'flight.schedule',

            'view_mode': 'list,form',

            'domain': [('vehicle_id', '=', self.id)],

            'context': {'default_vehicle_id': self.id},

        }

    

    def action_view_maintenance_requests(self):

        return {

            'type': 'ir.actions.act_window',

            'name': 'Maintenance Requests',

            'res_model': 'maintenance.request',

            'view_mode': 'list,form',

            'domain': [('vehicle_id', '=', self.id)],

            'context': {'default_vehicle_id': self.id},

        }



