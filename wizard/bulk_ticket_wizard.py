                       

"""
aviation_erp/wizard/bulk_ticket_wizard.py
Utility wizard to bulk-create draft tickets for a flight schedule.
Useful for loading test data and hackathon demos.
"""

from odoo import api, fields, models, _

from odoo.exceptions import UserError





class BulkTicketWizard(models.TransientModel):

    _name = 'aviation.bulk.ticket.wizard'

    _description = 'Bulk Ticket Creator'



    schedule_id = fields.Many2one(

        'flight.schedule', string='Flight', required=True

    )

    cabin_class = fields.Selection([

        ('economy', 'Economy'),

        ('premium_economy', 'Premium Economy'),

        ('business', 'Business'),

        ('first', 'First Class'),

    ], string='Cabin Class', required=True, default='economy')

    ticket_count = fields.Integer(string='Number of Tickets', default=10)

    market_average_price = fields.Float(string='Market Average Price (USD)')



    def action_create_tickets(self):

        self.ensure_one()

        if self.ticket_count <= 0 or self.ticket_count > 500:

            raise UserError(_('Ticket count must be between 1 and 500.'))



        tickets = []

        for i in range(self.ticket_count):

            tickets.append({

                'schedule_id': self.schedule_id.id,

                'cabin_class': self.cabin_class,

                'partner_id': self.env.company.partner_id.id,               

                'market_average_price': self.market_average_price or 0,

            })



        created = self.env['flight.ticket'].create(tickets)

        return {

            'type': 'ir.actions.act_window',

            'name': _('%d Tickets Created', len(created)),

            'res_model': 'flight.ticket',

            'view_mode': 'list,form',

            'domain': [('id', 'in', created.ids)],

        }

