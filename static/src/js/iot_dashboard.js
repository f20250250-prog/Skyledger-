


import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";


const THRESHOLDS = {
    engine_temp:    { min: 200,  max: 900  },
    fuel_level:     { min: 10,   max: 100  },
    oil_pressure:   { min: 25,   max: 100  },
    cabin_pressure: { min: 8,    max: 15   },
    hydraulics:     { min: 2000, max: 3500 },
};


class IoTSensorGauge extends Component {
    static template = "aviation_erp.IoTSensorGauge";
    static props = {
        label: String,
        value: Number,
        unit:  String,
        min:   Number,
        max:   Number,
    };

    get pct() {
        const { value, min, max } = this.props;
        return Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100));
    }

    get statusClass() {
        const { value, min, max } = this.props;
        if (value < min || value > max) return "sky-gauge--alert";
        if (value < min * 1.1 || value > max * 0.9) return "sky-gauge--warn";
        return "sky-gauge--ok";
    }
}


export class IoTDashboardWidget extends Component {
    static template = "aviation_erp.IoTDashboard";
    static props = { vehicleId: Number };

    setup() {
        this.orm  = useService("orm");
        this.state = useState({
            readings: {},
            lastUpdate: null,
            loading: true,
            error: null,
        });

        this._intervalId = null;

        onMounted(() => {
            this._fetchReadings();
            
            this._intervalId = setInterval(() => this._fetchReadings(), 30_000);
        });

        onWillUnmount(() => {
            if (this._intervalId) clearInterval(this._intervalId);
        });
    }

    async _fetchReadings() {
        try {
            const rows = await this.orm.searchRead(
                "aviation.iot.reading",
                [["vehicle_id", "=", this.props.vehicleId]],
                ["sensor_type", "value", "unit", "timestamp", "is_alert"],
                { order: "timestamp desc", limit: 50 }
            );

            
            const latest = {};
            for (const row of rows) {
                if (!latest[row.sensor_type]) {
                    latest[row.sensor_type] = row;
                }
            }
            this.state.readings   = latest;
            this.state.lastUpdate = new Date().toLocaleTimeString();
            this.state.loading    = false;
            this.state.error      = null;
        } catch (err) {
            this.state.error   = err.message || "Failed to fetch IoT readings.";
            this.state.loading = false;
        }
    }

    get hasAlerts() {
        return Object.values(this.state.readings).some(r => r.is_alert);
    }
}


registry.category("actions").add("aviation_iot_dashboard", IoTDashboardWidget);
