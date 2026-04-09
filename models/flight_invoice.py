                       

"""
aviation_erp/models/flight_invoice.py
Sprint 4 – Invoice / Accounting helpers (non-ticket)
Provides utility methods for batch invoice posting and reporting.
"""

from odoo import api, fields, models, _





class MaintenanceRequestAviationExtension(models.Model):

    """
    Extend maintenance.request to accept a fleet.vehicle foreign key
    (Odoo's native maintenance module links to equipment, not vehicles).
    We add vehicle_id as an aviation-specific extension.
    """

    _inherit = 'maintenance.request'



    vehicle_id = fields.Many2one(

        'fleet.vehicle', string='Aircraft',

        domain="[('aviation_type', '!=', False)]",

        ondelete='set null', index=True

    )

    maintenance_type = fields.Selection(

        selection_add=[

            ('emergency', 'Emergency AOG'),

        ],

        ondelete={'emergency': 'set default'}

    )

    aog_reason = fields.Text(

        string='AOG Reason',

        help='Aircraft On Ground – reason for emergency maintenance'

    )

    estimated_downtime_hours = fields.Float(string='Est. Downtime (hrs)')

