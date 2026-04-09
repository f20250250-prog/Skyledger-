import logging
import random
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

SENSOR_TYPES = [
    ('engine_temp', 'Engine Temperature (°C)'),
    ('fuel_level', 'Fuel Level (%)'),
    ('oil_pressure', 'Oil Pressure (PSI)'),
    ('cabin_pressure', 'Cabin Pressure (PSI)'),
    ('hydraulics', 'Hydraulics (PSI)'),
    ('altitude', 'Altitude (ft)'),
    ('airspeed', 'Airspeed (knots)'),
]

ALERT_THRESHOLDS = {
    'engine_temp':    {'min': 200,  'max': 900,   'unit': '°C'},
    'fuel_level':     {'min': 10,   'max': 100,   'unit': '%'},
    'oil_pressure':   {'min': 25,   'max': 100,   'unit': 'PSI'},
    'cabin_pressure': {'min': 8,    'max': 15,    'unit': 'PSI'},
    'hydraulics':     {'min': 2000, 'max': 3500,  'unit': 'PSI'},
}

class AviationIotSensorReading(models.Model):
    _name = 'aviation.iot.reading'
    _description = 'Aircraft IoT Sensor Reading'
    _order = 'timestamp desc'

    vehicle_id = fields.Many2one(
        'fleet.vehicle', string='Aircraft', required=True, ondelete='cascade', index=True
    )
    schedule_id = fields.Many2one(
        'flight.schedule', string='Flight', ondelete='set null', index=True
    )
    iot_device_id = fields.Char(string='IoT Device Serial/ID')
    sensor_type = fields.Selection(SENSOR_TYPES, string='Sensor Type', required=True)
    value = fields.Float(string='Reading Value', digits=(10, 4))
    unit = fields.Char(string='Unit', compute='_compute_unit', store=True)
    timestamp = fields.Datetime(
        string='Timestamp', default=fields.Datetime.now, required=True
    )
    is_alert = fields.Boolean(string='Alert', compute='_compute_is_alert', store=True)
    alert_reason = fields.Char(string='Alert Reason', compute='_compute_is_alert', store=True)

    @api.depends('sensor_type')
    def _compute_unit(self):
        for rec in self:
            thresh = ALERT_THRESHOLDS.get(rec.sensor_type, {})
            rec.unit = thresh.get('unit', '')

    @api.depends('sensor_type', 'value')
    def _compute_is_alert(self):
        for rec in self:
            thresh = ALERT_THRESHOLDS.get(rec.sensor_type)
            if not thresh:
                rec.is_alert = False
                rec.alert_reason = ''
                continue
            if rec.value < thresh['min']:
                rec.is_alert = True
                rec.alert_reason = _(
                    '%s below minimum (%.1f < %.1f)',
                    dict(SENSOR_TYPES).get(rec.sensor_type), rec.value, thresh['min']
                )
            elif rec.value > thresh['max']:
                rec.is_alert = True
                rec.alert_reason = _(
                    '%s above maximum (%.1f > %.1f)',
                    dict(SENSOR_TYPES).get(rec.sensor_type), rec.value, thresh['max']
                )
            else:
                rec.is_alert = False
                rec.alert_reason = ''

    @api.model
    def simulate_live_feed(self, vehicle_id, schedule_id=None):
        v_id = vehicle_id.id if isinstance(vehicle_id, models.Model) else vehicle_id
        s_id = schedule_id.id if isinstance(schedule_id, models.Model) else schedule_id
        sim_data = {
            'engine_temp':    random.gauss(750, 40),
            'fuel_level':     random.uniform(15, 98),
            'oil_pressure':   random.gauss(60, 5),
            'cabin_pressure': random.gauss(11.5, 0.3),
            'hydraulics':     random.gauss(2800, 100),
        }
        readings = self.env['aviation.iot.reading']
        for sensor_type, value in sim_data.items():
            reading = self.create({
                'vehicle_id': v_id,
                'schedule_id': s_id,
                'sensor_type': sensor_type,
                'value': round(value, 2),
                'timestamp': fields.Datetime.now(),
                'iot_device_id': 'SIM-SENSOR-%s' % sensor_type.upper(),
            })
            readings |= reading
            if reading.is_alert:
                _logger.warning(
                    'Skyledger IoT Alert – Aircraft ID %s | %s | %s',
                    v_id, sensor_type, reading.alert_reason
                )
        return readings.ids