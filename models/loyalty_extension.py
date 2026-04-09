                       

"""
aviation_erp/models/loyalty_extension.py
Sprint 4 – Loyalty & Frequent Flyer
Hooks into Odoo's loyalty.program to award and redeem FF points.
Points are accrued per confirmed ticket based on distance flown.
"""

from odoo import api, fields, models, _

import logging



_logger = logging.getLogger(__name__)



                                                 

POINTS_PER_NM = {

    'economy': 1,

    'premium_economy': 1.5,

    'business': 3,

    'first': 5,

}





class FlightTicketLoyaltyMixin(models.Model):

    """
    Hooks into flight.ticket to award loyalty points on confirmation.
    Added as a separate model to keep flight_ticket.py focused on pricing.
    """

    _inherit = 'flight.ticket'



    loyalty_card_id = fields.Many2one(

        'loyalty.card', string='FF Card',

        compute='_compute_loyalty_card', store=True

    )

    points_earned = fields.Float(string='Points Earned', readonly=True)



    @api.depends('partner_id')

    def _compute_loyalty_card(self):

        for rec in self:

            card = self.env['loyalty.card'].search([

                ('partner_id', '=', rec.partner_id.id),

                ('program_id.name', 'ilike', 'Frequent Flyer'),

            ], limit=1, order='points desc')

            rec.loyalty_card_id = card



    def _award_loyalty_points(self):

        """Award FF points when ticket is confirmed. Called from action_confirm."""

        for rec in self:

            if not rec.loyalty_card_id:

                                              

                ff_program = self.env['loyalty.program'].search([

                    ('name', 'ilike', 'Frequent Flyer')

                ], limit=1)

                if not ff_program:

                    _logger.info('Skyledger: No Frequent Flyer program found, skipping points.')

                    continue

                card = self.env['loyalty.card'].create({

                    'program_id': ff_program.id,

                    'partner_id': rec.partner_id.id,

                    'points': 0,

                })

                rec.loyalty_card_id = card



            distance = rec.schedule_id.route_id.distance_nm or 0

            multiplier = POINTS_PER_NM.get(rec.cabin_class, 1)

            points = round(distance * multiplier)



            if points and rec.loyalty_card_id:

                rec.loyalty_card_id.sudo().write({

                    'points': rec.loyalty_card_id.points + points

                })

                rec.points_earned = points

                rec.message_post(

                    body=_(

                        '✈️ %d Frequent Flyer points awarded (%.0f nm × %.1f multiplier)',

                        points, distance, multiplier

                    ),

                    subtype_xmlid='mail.mt_note'

                )



                                                       

    def action_confirm(self):

        result = super().action_confirm()

        self._award_loyalty_points()

        return result

