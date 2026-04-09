                       

"""
aviation_erp/models/airport.py
Sprint 1 – Core Infrastructure
Dedicated Airport model so routes can reference real IATA-coded airports
rather than generic res.partner records.
"""

from odoo import api, fields, models, _

from odoo.exceptions import ValidationError





class AviationAirport(models.Model):

    _name = 'aviation.airport'

    _description = 'Airport'

    _order = 'iata_code'

    _rec_name = 'full_label'



                                                                                

    name = fields.Char(string='Airport Name', required=True)

    iata_code = fields.Char(

        string='IATA Code', size=3, required=True, index=True,

        help='3-letter IATA airport code, e.g. DXB, LHR, JFK'

    )

    icao_code = fields.Char(string='ICAO Code', size=4)

    country_id = fields.Many2one('res.country', string='Country', required=True)

    city = fields.Char(string='City', required=True)

    timezone = fields.Selection(

        selection='_tz_get', string='Timezone', default='UTC'

    )



                                                                                

    partner_latitude = fields.Float(string='Latitude', digits=(10, 7))

    partner_longitude = fields.Float(string='Longitude', digits=(10, 7))



                                                                                

    elevation_ft = fields.Integer(string='Elevation (ft)')

    terminal_count = fields.Integer(string='No. of Terminals', default=1)

    active = fields.Boolean(default=True)



                                                                              

    full_label = fields.Char(

        string='Label', compute='_compute_full_label', store=True

    )



                                                                                

    origin_route_ids = fields.One2many(

        'flight.route', 'origin_airport_id', string='Departing Routes'

    )

    destination_route_ids = fields.One2many(

        'flight.route', 'destination_airport_id', string='Arriving Routes'

    )



                                                                                

    _sql_constraints = [

        ('unique_iata', 'UNIQUE(iata_code)', 'IATA code must be unique.'),

    ]



    @api.depends('name', 'iata_code', 'city')

    def _compute_full_label(self):

        for rec in self:

            rec.full_label = f'[{rec.iata_code}] {rec.name} – {rec.city}'





    @api.constrains('iata_code')

    def _check_iata_code(self):

        for rec in self:

            if not rec.iata_code.isalpha() or len(rec.iata_code) != 3:

                raise ValidationError(_('IATA code must be exactly 3 alphabetic characters.'))



    @api.model

    def _tz_get(self):

        return [(tz, tz) for tz in sorted(

            __import__('pytz').all_timezones, key=lambda z: z.lower()

        )]

