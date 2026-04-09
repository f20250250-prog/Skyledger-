                       

"""
aviation_erp/models/flight_seat_class.py
Sprint 1 – Multi-Tier Seat Inventory
Defines Economy / Business / First class buckets per route with
base price tiers that feed the Pricing Engine.
"""

from odoo import api, fields, models, _

from odoo.exceptions import ValidationError



CABIN_CLASSES = [

    ('economy', 'Economy'),

    ('premium_economy', 'Premium Economy'),

    ('business', 'Business'),

    ('first', 'First Class'),

]





class FlightSeatClass(models.Model):

    _name = 'flight.seat.class'

    _description = 'Seat Class / Cabin Tier'

    _order = 'route_id, cabin_class'



    route_id = fields.Many2one(

        'flight.route', string='Route', required=True, ondelete='cascade'

    )

    cabin_class = fields.Selection(

        CABIN_CLASSES, string='Cabin Class', required=True, default='economy'

    )

    seat_count = fields.Integer(string='Allocated Seats', required=True, default=100)

    base_price = fields.Monetary(

        string='Base Fare (USD)', currency_field='currency_id',

        required=True

    )

    currency_id = fields.Many2one(

        'res.currency', default=lambda self: self.env.ref('base.USD')

    )



                                                                                

    max_fuel_surcharge_pct = fields.Float(

        string='Max Fuel Surcharge (%)', default=25.0

    )

    max_demand_surge_pct = fields.Float(

        string='Max Demand Surge (%)', default=50.0

    )



                                                                                

    checked_bags = fields.Integer(string='Free Checked Bags', default=1)

    cabin_bag_kg = fields.Float(string='Cabin Bag Allowance (kg)', default=7.0)

    checked_bag_kg = fields.Float(string='Checked Bag Allowance (kg)', default=23.0)



                                                                                

    product_id = fields.Many2one(

        'product.product', string='Odoo Product',

        help='Maps this cabin class to an Odoo product for invoicing and G/L'

    )



    _sql_constraints = [

        ('unique_class_per_route', 'UNIQUE(route_id, cabin_class)',

         'Each cabin class can only be defined once per route.'),

        ('positive_seats', 'CHECK(seat_count > 0)', 'Seat count must be positive.'),

        ('positive_base_price', 'CHECK(base_price >= 0)', 'Base price cannot be negative.'),

    ]



    @api.constrains('max_fuel_surcharge_pct', 'max_demand_surge_pct')

    def _check_surcharge_caps(self):

        for rec in self:

            if not (0 <= rec.max_fuel_surcharge_pct <= 100):

                raise ValidationError(_('Fuel surcharge cap must be between 0 and 100%.'))

            if not (0 <= rec.max_demand_surge_pct <= 200):

                raise ValidationError(_('Demand surge cap must be between 0 and 200%.'))

