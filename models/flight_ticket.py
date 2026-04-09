                       

"""
aviation_erp/models/flight_ticket.py
Sprint 2 – Smart Pricing Engine + Sprint 4 – Invoicing & Loyalty
The heart of the Skyledger revenue system.

Pricing stack (applied in order):
  1. Base Fare          (from flight.seat.class)
  2. Fuel Surcharge     (live Jet A-1 index × fuel burn)
  3. Demand Surge       (exponential as seats_available < 20%)
  4. Red-Eye Discount   (departure 00:00–04:00 UTC  →  −15%)
  5. Weather Insurance  (toggle on flight.schedule  →  +8%)
  6. Cargo Subsidy      (high cargo profit  →  up to −10% off base fare)
  7. Competitor Cap     (if price > market_avg × 1.15  →  alert / cap)
  8. Loyalty Discount   (Frequent-Flyer tier  →  up to −10%)
  9. Currency Conversion (AED quotation via res.currency)
"""

import logging

from odoo import api, fields, models, _

from odoo.exceptions import ValidationError, UserError



_logger = logging.getLogger(__name__)



TICKET_STATES = [

    ('draft', 'Draft'),

    ('confirmed', 'Confirmed'),

    ('invoiced', 'Invoiced'),

    ('cancelled', 'Cancelled'),

]



CABIN_CLASSES = [

    ('economy', 'Economy'),

    ('premium_economy', 'Premium Economy'),

    ('business', 'Business'),

    ('first', 'First Class'),

]





class FlightTicket(models.Model):

    _name = 'flight.ticket'

    _description = 'Flight Ticket'

    _inherit = ['mail.thread', 'mail.activity.mixin']

    _order = 'schedule_id, cabin_class, id'

    _rec_name = 'ticket_ref'



                                                                                

    ticket_ref = fields.Char(

        string='Ticket Reference', required=True, copy=False,

        default=lambda self: self.env['ir.sequence'].next_by_code('flight.ticket')

    )

    state = fields.Selection(TICKET_STATES, default='draft', tracking=True, index=True)



                                                                                

    partner_id = fields.Many2one(

        'res.partner', string='Passenger', required=True, ondelete='restrict'

    )

    passport_number = fields.Char(string='Passport / ID')



                                                                                

    schedule_id = fields.Many2one(

        'flight.schedule', string='Flight', required=True, ondelete='restrict',

        index=True

    )

    route_id = fields.Many2one(

        related='schedule_id.route_id', store=True, string='Route'

    )

    cabin_class = fields.Selection(

        CABIN_CLASSES, string='Cabin Class', required=True, default='economy'

    )

    seat_number = fields.Char(string='Seat Number')



                                                                                

    seat_class_id = fields.Many2one(

        'flight.seat.class', string='Seat Class Config',

        compute='_compute_seat_class_id', store=True

    )



                                                                                

                                

                                                                                



                                                                                

    base_fare = fields.Monetary(

        string='Base Fare (USD)', currency_field='currency_id',

        compute='_compute_ticket_price', store=True

    )



                                                                               

    fuel_surcharge = fields.Monetary(

        string='Fuel Surcharge (USD)', currency_field='currency_id',

        compute='_compute_ticket_price', store=True

    )

    jet_a1_price_snapshot = fields.Float(

        string='Jet A-1 Snapshot (USD/gal)', digits=(10, 4),

        help='Price at time of last price computation'

    )



                                                                               

    demand_surge_pct = fields.Float(

        string='Demand Surge (%)', compute='_compute_ticket_price', store=True

    )

    demand_surge_amount = fields.Monetary(

        string='Demand Surge (USD)', currency_field='currency_id',

        compute='_compute_ticket_price', store=True

    )



                                                                               

    red_eye_discount_pct = fields.Float(

        string='Red-Eye Discount (%)', compute='_compute_ticket_price', store=True

    )

    red_eye_discount_amount = fields.Monetary(

        string='Red-Eye Discount (USD)', currency_field='currency_id',

        compute='_compute_ticket_price', store=True

    )



                                                                               

    weather_surcharge_pct = fields.Float(

        string='Weather Surcharge (%)', compute='_compute_ticket_price', store=True

    )

    weather_surcharge_amount = fields.Monetary(

        string='Weather Insurance (USD)', currency_field='currency_id',

        compute='_compute_ticket_price', store=True

    )



                                                                                

    cargo_subsidy_amount = fields.Monetary(

        string='Cargo Subsidy (USD)', currency_field='currency_id',

        compute='_compute_ticket_price', store=True

    )



                                                                               

    market_average_price = fields.Monetary(

        string='Market Average (USD)', currency_field='currency_id',

        help='Sourced from competitor benchmarking API (manual input for demo)'

    )

    competitor_alert = fields.Boolean(

        string='Competitor Alert', compute='_compute_ticket_price', store=True,

        help='True if our price is >15% above market average'

    )



                                                                               

    loyalty_tier = fields.Selection(

        [('silver', 'Silver'), ('gold', 'Gold'), ('platinum', 'Platinum')],

        string='FF Tier', compute='_compute_loyalty_tier', store=True

    )

    loyalty_discount_pct = fields.Float(

        string='Loyalty Discount (%)', compute='_compute_ticket_price', store=True

    )

    loyalty_discount_amount = fields.Monetary(

        string='Loyalty Discount (USD)', currency_field='currency_id',

        compute='_compute_ticket_price', store=True

    )



                                                                                

    subtotal_usd = fields.Monetary(

        string='Subtotal (USD)', currency_field='currency_id',

        compute='_compute_ticket_price', store=True

    )

    final_price = fields.Monetary(

        string='Final Price (USD)', currency_field='currency_id',

        compute='_compute_ticket_price', store=True, tracking=True

    )



                                                                                

    currency_id = fields.Many2one(

        'res.currency', string='Currency',

        default=lambda self: self.env.ref('base.USD')

    )

    quote_currency_id = fields.Many2one(

        'res.currency', string='Quote Currency',

        default=lambda self: self.env.ref('base.AED', raise_if_not_found=False)

    )

    final_price_quoted = fields.Monetary(

        string='Price (Quoted Currency)', currency_field='quote_currency_id',

        compute='_compute_ticket_price', store=True

    )



                                                                                

    invoice_id = fields.Many2one('account.move', string='Invoice', copy=False)

    invoice_state = fields.Selection(

        related='invoice_id.state', string='Invoice Status'

    )



                                                                                

             

                                                                                



    @api.depends('schedule_id', 'cabin_class')

    def _compute_seat_class_id(self):

        for rec in self:

            if rec.schedule_id and rec.cabin_class:

                seat_class = self.env['flight.seat.class'].search([

                    ('route_id', '=', rec.schedule_id.route_id.id),

                    ('cabin_class', '=', rec.cabin_class),

                ], limit=1)

                rec.seat_class_id = seat_class

            else:

                rec.seat_class_id = False



    @api.depends('partner_id')

    def _compute_loyalty_tier(self):

        """Resolve loyalty tier from the partner's loyalty points / rank."""

        for rec in self:

            partner = rec.partner_id

                                                               

            loyalty_card = self.env['loyalty.card'].search([

                ('partner_id', '=', partner.id),

                ('program_id.name', 'ilike', 'Frequent Flyer'),

            ], limit=1, order='points desc')



            if loyalty_card:

                points = loyalty_card.points

                if points >= 100_000:

                    rec.loyalty_tier = 'platinum'

                elif points >= 50_000:

                    rec.loyalty_tier = 'gold'

                else:

                    rec.loyalty_tier = 'silver'

            else:

                rec.loyalty_tier = False



                                                                                

                                     

                                                                                



    @api.depends(

        'schedule_id', 'schedule_id.seats_available', 'schedule_id.total_seats',

        'schedule_id.is_red_eye', 'schedule_id.weather_alert_active',

        'schedule_id.expected_cargo_profit',

        'cabin_class', 'seat_class_id', 'seat_class_id.base_price',

        'market_average_price', 'loyalty_tier', 'quote_currency_id',

    )

    def _compute_ticket_price(self):

        FuelSvc = self.env['aviation.fuel.index']



        for rec in self:

            if not rec.seat_class_id or not rec.schedule_id:

                rec._zero_out_pricing()

                continue



            sc = rec.seat_class_id

            sched = rec.schedule_id



                                                                              

            base = sc.base_price

            rec.base_fare = base



                                                                              

            fuel_burn = sched.route_id.fuel_burn_gallons or 0

            jet_price = FuelSvc.get_current_jet_a1_price()

            rec.jet_a1_price_snapshot = jet_price



            raw_fuel_cost = jet_price * fuel_burn

                                                                   

            max_fuel = base * (sc.max_fuel_surcharge_pct / 100)

            fuel_surch = min(raw_fuel_cost, max_fuel)

            rec.fuel_surcharge = round(fuel_surch, 2)



            running_total = base + fuel_surch



                                                                              

            avail = sched.seats_available or 0

            total = sched.total_seats or 1

            occupancy = 1 - (avail / total)



            if occupancy >= 0.80:                         

                                                                            

                overfill = (occupancy - 0.80) / 0.05

                surge_pct = min(overfill * 5.0, sc.max_demand_surge_pct)

            else:

                surge_pct = 0.0



            surge_amount = round(base * surge_pct / 100, 2)

            rec.demand_surge_pct = surge_pct

            rec.demand_surge_amount = surge_amount

            running_total += surge_amount



                                                                              

            if sched.is_red_eye:

                red_eye_pct = 15.0

                red_eye_amount = round(running_total * red_eye_pct / 100, 2)

            else:

                red_eye_pct = 0.0

                red_eye_amount = 0.0



            rec.red_eye_discount_pct = red_eye_pct

            rec.red_eye_discount_amount = red_eye_amount

            running_total -= red_eye_amount



                                                                               

            if sched.weather_alert_active:

                wx_pct = 8.0

                wx_amount = round(running_total * wx_pct / 100, 2)

            else:

                wx_pct = 0.0

                wx_amount = 0.0



            rec.weather_surcharge_pct = wx_pct

            rec.weather_surcharge_amount = wx_amount

            running_total += wx_amount



                                                                              

            cargo_profit = sched.expected_cargo_profit or 0

            if cargo_profit > 5_000:                                    

                subsidy_pct = min(cargo_profit / 500_000, 0.10)           

                cargo_subsidy = round(base * subsidy_pct, 2)

            else:

                cargo_subsidy = 0.0



            rec.cargo_subsidy_amount = cargo_subsidy

            running_total -= cargo_subsidy



                                              

            running_total = max(running_total, base * 0.80)



            rec.subtotal_usd = round(running_total, 2)



                                                                              

            market_avg = rec.market_average_price or 0

            if market_avg and running_total > market_avg * 1.15:

                rec.competitor_alert = True

                _logger.warning(

                    'Skyledger Pricing: Ticket %s price $%.2f is >15%% above '

                    'market avg $%.2f on %s',

                    rec.ticket_ref or '(new)', running_total, market_avg,

                    sched.flight_number

                )

                                                      

                running_total = round(market_avg * 1.15, 2)

            else:

                rec.competitor_alert = False



                                                                               

            tier_discounts = {'silver': 3.0, 'gold': 7.0, 'platinum': 10.0}

            loyalty_pct = tier_discounts.get(rec.loyalty_tier, 0.0)

            loyalty_amount = round(running_total * loyalty_pct / 100, 2)

            rec.loyalty_discount_pct = loyalty_pct

            rec.loyalty_discount_amount = loyalty_amount

            running_total -= loyalty_amount



                                                                               

            rec.final_price = round(max(running_total, 0), 2)



                                                                               

            if rec.quote_currency_id and rec.quote_currency_id != rec.currency_id:

                rec.final_price_quoted = rec.currency_id._convert(

                    rec.final_price,

                    rec.quote_currency_id,

                    rec.env.company,

                    fields.Date.today(),

                )

            else:

                rec.final_price_quoted = rec.final_price



    def _zero_out_pricing(self):

        """Reset all pricing fields to zero when dependencies are unset."""

        fields_to_zero = [

            'base_fare', 'fuel_surcharge', 'demand_surge_pct',

            'demand_surge_amount', 'red_eye_discount_pct', 'red_eye_discount_amount',

            'weather_surcharge_pct', 'weather_surcharge_amount',

            'cargo_subsidy_amount', 'loyalty_discount_pct', 'loyalty_discount_amount',

            'subtotal_usd', 'final_price', 'final_price_quoted',

        ]

        self.update({f: 0 for f in fields_to_zero})

        self.competitor_alert = False



                                                                                

                                    

                                                                                



    @api.onchange('market_average_price')

    def _onchange_market_average(self):

        if self.market_average_price and self.final_price:

            ratio = self.final_price / self.market_average_price

            if ratio > 1.15:

                return {

                    'warning': {

                        'title': _('Competitor Alert'),

                        'message': _(

                            'Current price ($%.2f) is %.0f%% above market average ($%.2f). '

                            'Price will be auto-capped at 115%% of market average.',

                            self.final_price, (ratio - 1) * 100, self.market_average_price

                        )

                    }

                }



                                                                                

                   

                                                                                



    def action_confirm(self):

        for rec in self:

            if rec.schedule_id.seats_available <= 0:

                raise UserError(_('No seats available on flight %s.', rec.schedule_id.flight_number))

            rec.state = 'confirmed'

            rec.message_post(body=_('Ticket confirmed at $%.2f.', rec.final_price))

                                                

        self._create_invoice()



    def action_cancel(self):

        self.write({'state': 'cancelled'})



                                                                                

                                             

                                                                                



    def _create_invoice(self):

        """
        Generate account.move for each confirmed ticket.
        Base Fare and Fuel Surcharge are mapped to different G/L accounts
        via the product's category income account.
        """

        AccountMove = self.env['account.move']



        for rec in self:

            if rec.invoice_id:

                continue                    



            sc = rec.seat_class_id

            if not sc or not sc.product_id:

                _logger.warning(

                    'Skyledger: No product mapped for %s – invoice skipped.',

                    rec.ticket_ref

                )

                continue



                                                                         

            fuel_product_id = int(

                self.env['ir.config_parameter'].sudo().get_param(

                    'aviation_erp.fuel_surcharge_product_id', default=0

                )

            )

            fuel_product = self.env['product.product'].browse(fuel_product_id) if fuel_product_id else None



            invoice_lines = [

                                

                (0, 0, {

                    'product_id': sc.product_id.id,

                    'name': _(

                        'Base Fare – %s (%s)', rec.schedule_id.flight_number,

                        dict(CABIN_CLASSES).get(rec.cabin_class, rec.cabin_class)

                    ),

                    'quantity': 1,

                    'price_unit': rec.base_fare,

                }),

            ]



                                                                  

            if rec.fuel_surcharge and fuel_product:

                invoice_lines.append((0, 0, {

                    'product_id': fuel_product.id,

                    'name': _(

                        'Fuel Surcharge – %s (Jet A-1 @ $%.4f/gal)',

                        rec.schedule_id.flight_number,

                        rec.jet_a1_price_snapshot

                    ),

                    'quantity': 1,

                    'price_unit': rec.fuel_surcharge,

                }))

            elif rec.fuel_surcharge:

                                                                       

                invoice_lines[0][2]['name'] += _(

                    ' (incl. Fuel Surcharge $%.2f)', rec.fuel_surcharge

                )



                               

            if rec.weather_surcharge_amount:

                invoice_lines.append((0, 0, {

                    'product_id': sc.product_id.id,

                    'name': _('Weather Insurance Surcharge – %s', rec.schedule_id.flight_number),

                    'quantity': 1,

                    'price_unit': rec.weather_surcharge_amount,

                }))



                                         

            if rec.red_eye_discount_amount:

                invoice_lines.append((0, 0, {

                    'product_id': sc.product_id.id,

                    'name': _('Red-Eye Discount – %s', rec.schedule_id.flight_number),

                    'quantity': 1,

                    'price_unit': -rec.red_eye_discount_amount,

                }))



            if rec.loyalty_discount_amount:

                invoice_lines.append((0, 0, {

                    'product_id': sc.product_id.id,

                    'name': _(

                        'Frequent Flyer %s Discount (%.0f%%)',

                        rec.loyalty_tier.title() if rec.loyalty_tier else '',

                        rec.loyalty_discount_pct

                    ),

                    'quantity': 1,

                    'price_unit': -rec.loyalty_discount_amount,

                }))



            move = AccountMove.create({

                'move_type': 'out_invoice',

                'partner_id': rec.partner_id.id,

                'currency_id': rec.currency_id.id,

                'invoice_line_ids': invoice_lines,

                'narration': _(

                    'Skyledger ticket %s | Flight %s | %s → %s',

                    rec.ticket_ref,

                    rec.schedule_id.flight_number,

                    rec.schedule_id.route_id.origin_airport_id.iata_code,

                    rec.schedule_id.route_id.destination_airport_id.iata_code,

                ),

            })



            rec.write({'invoice_id': move.id, 'state': 'invoiced'})

            rec.message_post(

                body=_('Invoice %s generated.', move.name),

                subtype_xmlid='mail.mt_note'

            )



    def action_view_invoice(self):

        self.ensure_one()

        return {

            'type': 'ir.actions.act_window',

            'res_model': 'account.move',

            'res_id': self.invoice_id.id,

            'view_mode': 'form',

        }



                                                                                

         

                                                                                



    @api.model_create_multi

    def create(self, vals_list):

        for vals in vals_list:

            if not vals.get('ticket_ref') or vals['ticket_ref'] == '/':

                vals['ticket_ref'] = (

                    self.env['ir.sequence'].next_by_code('flight.ticket') or '/'

                )

        return super().create(vals_list)

