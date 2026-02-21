/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { PaymentInterface } from "@point_of_sale/app/utils/payment/payment_interface";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { serializeDateTime } from "@web/core/l10n/dates";
import { register_payment_method } from "@point_of_sale/app/services/pos_store";

export class PaymentAFS extends PaymentInterface {
    setup() {
        super.setup(...arguments);
        this.afs_transaction_in_progress = false;
        this.afs_transaction_id = null;
        this.dialog = this.env.services.dialog;
        this.paymentLineResolvers = {};
        this.orm = this.env.services.orm
    }

    async sendPaymentRequest(uuid) {
        await super.sendPaymentRequest(...arguments);
        const order = this.pos.getOrder();
        const line = order.getSelectedPaymentline();

        line.setPaymentStatus('waitingCard');
            if (line.amount < 0) {
                this._showError({ message: _t("Refunds are not supported by this payment method.") });
                line.setPaymentStatus('retry');
                return;
            }
            const result = await this._afsMakePaymentRequest(order, line, uuid);

            if (result.status === 'error') {
                this._showError({ message: result.message });
                this.afs_transaction_in_progress = false;
                this.afs_transaction_id = null;
                line.setPaymentStatus('retry');
            } else if (result.status === 'polling') {
                const confirmed = await this._waitForPaymentConfirmation(line, uuid);
                console.log(_t("payment status: %s", confirmed ? "success" : "failed"))
                if (confirmed === true) {
                    this.afs_transaction_in_progress = false;
                    this.afs_transaction_id = null;
                    line.setPaymentStatus('done');
                    return true;
                } else {
                    line.setPaymentStatus('force_done');
                    return false;
                }
            }
            this.afs_transaction_in_progress = false;
            this.afs_transaction_id = null;
            line.setPaymentStatus('done');
            return result.status === 'success';
    }

    async sendPaymentCancel(order, uuid) {
        await super.sendPaymentCancel(...arguments);
        if (this.afs_transaction_in_progress) {
            //await this._afsCancelPaymentRequest();
            this.afs_transaction_in_progress = false;
            this.afs_transaction_id = null;
            this._showInfo(_t("Cancel payment from terminal device"));
        }
    }

    async _waitForPaymentConfirmation(line, uuid) {
        console.log("waitiing for payment confirmation")
        const order = this.pos.getOrder();
        const paymentLine = line;
        let result = { status: 'pending' };
        let pollCount = 0;
        const maxPolls = 3; // Poll for 30 seconds (30 * 1000ms / 1000ms interval)
        const pollInterval = 1000; // 1 second

        // Start the payment request
        const initialRequest = await this._afsFetchPaymentStatus(paymentLine);
        if (initialRequest.status === 'error') {
            console.log("Error in initial request for status fetch")
            console.log({ message: initialRequest.message })
            this.sendPaymentCancel(order, uuid);
            // this._showError({ message: initialRequest.message });
            return false;
        } else if (initialRequest.status === 'polling') {
            result.status = 'polling';
        }

        while (result.status === 'polling' && pollCount < maxPolls && !this.afs_transaction_id) {
            await new Promise(resolve => setTimeout(resolve, pollInterval));

            result = await this._afsFetchPaymentStatus(paymentLine);
            pollCount++;
            if (result.status === 'error') {
                console.log("Error in status fetch")
                console.log({ message: result.message })
                this.sendPaymentCancel(order, uuid);
                //this._showError({ message: result.message });
                return false;
            }
        }

        if (result.status === 'success') {
            return true;
        } else if (result.status === 'polling') {
            console.log("payment time out")
            this.sendPaymentCancel(order, uuid); // Attempt to cancel if timed out
            return false;
        } else {
            this._showError({ message: _t("An unknown error occurred during payment.") });
            this.sendPaymentCancel(order, uuid);
            return false;
        }
    }


    get pendingAFSline() {
        return this.pos.getPendingPaymentLine("afs");
    }

    async _afsMakePaymentRequest(order, line, uuid) {
        console.log("afsMakePaymentRequest: Starting payment request for line", line.cid);
        if (this.afs_transaction_in_progress) {
            console.warn("afsMakePaymentRequest: A transaction is already in progress.");
            return { status: 'error', message: 'Another transaction is already in progress.' };
        }

        this.afs_transaction_in_progress = true;
        this.afs_transaction_id = uuid;
        const paymentMethod = this.payment_method_id;
        const data = {
            amount: line.amount,
            currency_iso: "OMR",
            payment_id: uuid,
            order_id: order.name,
        };

        try {
            const response = await this.orm.call(
                'pos.payment.method',
                'afs_make_payment_request',
                [[paymentMethod.id], data]
            );

            if (response.status === 'success'){
                console.log("afsMakePaymentRequest: Transaction success")
                return { status: 'success' }
            }
            else if (response.status === 'waiting') {
                console.log("afsMakePaymentRequest: Transaction started, waiting for customer.", response);
                this.afs_transaction_id = response.afs_transaction_id;
                return { status: 'polling' };
            } else {
                console.error("afsMakePaymentRequest: Error from backend.", response);
                this.afs_transaction_in_progress = false;
                return { status: 'error', message: response.message };
            }
        } catch (error) {
            console.error("afsMakePaymentRequest: RPC Error.", error);
            this.afs_transaction_in_progress = false;
            return { status: 'error', message: 'Failed to connect to Odoo server.' };
        }
    }

    async _afsFetchPaymentStatus(line) {
        const paymentMethod = this.payment_method_id;
        console.log("afsFetchPaymentStatus: Polling for status of transaction", this.afs_transaction_id);
        if (!this.afs_transaction_id) {
            console.warn("afsFetchPaymentStatus: No transaction ID to poll.");
            return { status: 'error', message: 'No active transaction to check.' };
        }

        const data = {
            afs_transaction_id: this.afs_transaction_id,
        };

        try {
            const response = await this.orm.call(
                'pos.payment.method',
                'afs_fetch_payment_status',
                [[paymentMethod.id], data]
            );

            console.log("afsFetchPaymentStatus: Poll response received.", response);

            if (response.status === 'success') {
                this.afs_transaction_in_progress = false;
                return { status: 'success' };
            } else if (response.status === 'polling') {
                return { status: 'polling' }; // Continue polling
            } else {
                // Handle error, cancellation, etc.
                this.afs_transaction_in_progress = false;
                return { status: 'error', message: response.message };
            }
        } catch (error) {
            console.error("afsFetchPaymentStatus: RPC Error.", error);
            // Don't stop polling on network errors, just retry after a delay
            return { status: 'polling', message: 'Network error, will retry.' };
        }
    }

    async _afsCancelPaymentRequest() {
        const paymentMethod = this.payment_method_id;
        console.log("afsCancelPaymentRequest: Attempting to cancel transaction", this.afs_transaction_id);
        if (!this.afs_transaction_id) {
            console.warn("afsCancelPaymentRequest: No transaction to cancel.");
            return { status: 'error', message: 'No active transaction to cancel.' };
        }

        const data = {
            afs_transaction_id: this.afs_transaction_id,
        };

        this.afs_transaction_in_progress = false; // Stop polling and allow new transactions

        try {
            const response = await this.orm.call(
                'pos.payment.method',
                'afs_cancel_payment_request',
                [[paymentMethod.id], data]
            );

            console.log("afsCancelPaymentRequest: Cancellation response.", response);
            if (response.status === 'cancelled') {
                return { status: 'cancelled' };
            } else {
                // If cancellation fails, it's hard to recover. Log and inform user.
                return { status: 'error', message: response.message || 'Cancellation failed at the terminal.' };
            }
        } catch (error) {
            console.error("afsCancelPaymentRequest: RPC Error.", error);
            return { status: 'error', message: 'Failed to send cancellation request.' };
        }
    }

    _showError(error) {
        this.dialog.add(AlertDialog, {
            title: _t("Payment Error"),
            body: error.message,
        });
    }

    _showInfo(info) {
        this.dialog.add(AlertDialog, {
            title: _t("Info"),
            body: _t("%s",info),
            });
    }

}

register_payment_method("afs", PaymentAFS);