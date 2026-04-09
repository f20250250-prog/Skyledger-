


import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component } from "@odoo/owl";


export class RasmCasmBarWidget extends Component {
    static template = "aviation_erp.RasmCasmBar";
    static props = {
        ...standardFieldProps,
        casmValue: { type: Number, optional: true },
    };

    get rasm() { return this.props.record.data.rasm || 0; }
    get casm() { return this.props.record.data.casm || 0; }

    get margin() {
        return this.casm ? ((this.rasm - this.casm) / this.casm * 100) : 0;
    }

    get marginClass() {
        if (this.margin > 10)  return "text-success fw-bold";
        if (this.margin > 0)   return "text-warning";
        return "text-danger fw-bold";
    }

    get rasmPct() {
        const total = this.rasm + this.casm;
        return total ? Math.round((this.rasm / total) * 100) : 50;
    }
}

registry.category("fields").add("rasm_casm_bar", {
    component: RasmCasmBarWidget,
    displayName: "RASM vs CASM Bar",
    supportedTypes: ["float"],
});
