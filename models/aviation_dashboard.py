from odoo import api, fields, models, tools
class AviationDashboardKpi(models.Model):
    _name = 'aviation.dashboard.kpi'
    _description = 'Aviation Executive Dashboard KPI'
    _auto = False
    _rec_name = 'route_name'
    route_id = fields.Many2one('flight.route', string='Route', readonly=True)
    route_name = fields.Char(string='Route', readonly=True)
    month = fields.Char(string='Month', readonly=True)
    total_revenue = fields.Float(string='Total Revenue (USD)', readonly=True)
    total_cost = fields.Float(string='Total Cost (USD)', readonly=True)
    asm = fields.Float(string='Available Seat Miles', readonly=True)
    rasm = fields.Float(string='RASM', readonly=True, help='Revenue per Available Seat Mile')
    casm = fields.Float(string='CASM', readonly=True, help='Cost per Available Seat Mile')
    flights_operated = fields.Integer(string='Flights Operated', readonly=True)
    avg_occupancy = fields.Float(string='Avg Occupancy (%)', readonly=True)
    fuel_cost = fields.Float(string='Fuel Cost (USD)', readonly=True)
    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW aviation_dashboard_kpi AS
            SELECT
                fs.id                                                   AS id,
                fs.route_id                                             AS route_id,
                fr.name                                                 AS route_name,
                TO_CHAR(fs.departure_datetime, 'YYYY-MM')               AS month,
                COALESCE(fs.total_revenue, 0)                           AS total_revenue,
                COALESCE(fr.base_operational_cost, 0)
                    + COALESCE(fs.total_labour_cost, 0)                 AS total_cost,
                COALESCE(fs.total_seats, 0)
                    * COALESCE(fr.distance_nm, 0)                       AS asm,
                CASE
                    WHEN COALESCE(fs.total_seats, 0)
                         * COALESCE(fr.distance_nm, 0) = 0
                    THEN 0
                    ELSE COALESCE(fs.total_revenue, 0)
                         / (fs.total_seats * fr.distance_nm)
                END                                                     AS rasm,
                CASE
                    WHEN COALESCE(fs.total_seats, 0)
                         * COALESCE(fr.distance_nm, 0) = 0
                    THEN 0
                    ELSE (
                        COALESCE(fr.base_operational_cost, 0)
                        + COALESCE(fs.total_labour_cost, 0)
                    ) / (fs.total_seats * fr.distance_nm)
                END                                                     AS casm,
                1                                                       AS flights_operated,
                COALESCE(fs.occupancy_rate, 0)                          AS avg_occupancy,
                COALESCE(fr.fuel_burn_gallons, 0)
                    * COALESCE(
                        (SELECT CAST(value AS FLOAT)
                         FROM ir_config_parameter
                         WHERE key = 'aviation_erp.jet_a1_price_usd'
                         LIMIT 1),
                        2.85
                    )                                                   AS fuel_cost
            FROM
                flight_schedule fs
            JOIN
                flight_route fr ON fr.id = fs.route_id
            WHERE
                fs.state IN ('completed', 'landed', 'airborne')
        """)
        super().init()