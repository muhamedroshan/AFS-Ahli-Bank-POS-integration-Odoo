/** @odoo-module */

import { PosPayment } from "@point_of_sale/app/models/pos_payment";
import { patch } from "@web/core/utils/patch";

patch(PosPayment.prototype, {
    setup(obj, options) {
        super.setup(...arguments);
        this.afs_transaction_id = this.afs_transaction_id || null;
    },

    /**
     * Overrides the export_for_printing method to include the AFS transaction ID.
     * This makes the ID available on receipts.
     */
    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        result.afs_transaction_id = this.afs_transaction_id || this.transaction_id;
        return result;
    },

    /**
     * Overrides the export_as_JSON method to include the AFS transaction ID
     * when sending payment data to the backend.
     */
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.afs_transaction_id = this.afs_transaction_id || this.transaction_id;
        return json;
    },

    /**
     * Overrides the init_from_JSON method to correctly load the AFS transaction ID
     * when loading order data from the backend.
     */
    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.afs_transaction_id = json.afs_transaction_id;
        // Also, ensure the generic transaction_id is populated for consistency if it exists
        this.transaction_id = this.transaction_id || json.afs_transaction_id;
    },
});
