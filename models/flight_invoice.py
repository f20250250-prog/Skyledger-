from odoo import api, fields, models, _
class MaintenanceRequestAviationExtension(models.Model):
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