/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const STATE_LABELS = {
    draft: "Draft",
    submitted: "Submitted",
    approved: "Approved",
    paid: "Paid",
    rejected: "Rejected",
};

const STATE_CLASSES = {
    draft: "badge-draft",
    submitted: "badge-submitted",
    approved: "badge-approved",
    paid: "badge-paid",
    rejected: "badge-rejected",
};

export class PettyCashDashboard extends Component {
    static template = "leapai_petty_cash.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            data: {},
        });
        onWillStart(() => this._loadData());
    }

    async _loadData() {
        this.state.loading = true;
        try {
            this.state.data = await this.orm.call(
                "petty.cash.dashboard",
                "get_dashboard_data",
                []
            );
        } finally {
            this.state.loading = false;
        }
    }

    formatAmount(amount, symbol = "") {
        const value = Number(amount || 0);
        return `${symbol}${value.toLocaleString("en-US", { minimumFractionDigits: 2 })}`;
    }

    stateLabel(state) {
        return STATE_LABELS[state] || state;
    }

    stateClass(state) {
        return STATE_CLASSES[state] || "";
    }

    openFunds(domain) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Petty Cash Funds",
            res_model: "petty.cash.fund",
            views: [[false, "list"], [false, "form"]],
            domain,
        });
    }

    openRequests(domain) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Petty Cash Requests",
            res_model: "petty.cash.request",
            views: [[false, "list"], [false, "form"]],
            domain,
        });
    }

    openRequest(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "petty.cash.request",
            res_id: id,
            views: [[false, "form"]],
        });
    }

    openTransactions() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Petty Cash Transactions",
            res_model: "petty.cash.transaction",
            views: [[false, "list"], [false, "form"]],
        });
    }
}

registry.category("actions").add("petty_cash_dashboard", PettyCashDashboard);
