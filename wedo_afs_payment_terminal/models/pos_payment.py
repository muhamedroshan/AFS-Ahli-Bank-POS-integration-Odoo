import logging
from odoo import models, fields

_logger = logging.getLogger(__name__)


class PosPayment(models.Model):
    _inherit = "pos.payment"

    afs_transaction_id = fields.Char(string='AFS Transaction ID', readonly=True, copy=False,
                                     help="The unique transaction identifier returned by the AFS payment terminal.")

    def _export_for_ui(self, payment):
        """
        Override to include the AFS transaction ID in the data sent to the POS UI.
        This allows the UI to have context about the transaction.
        """
        result = super()._export_for_ui(payment)
        result['afs_transaction_id'] = payment.afs_transaction_id
        return result

    def from_ui(self, payment_vals):
        """
        Override to handle the AFS transaction ID coming from the UI.
        When a payment is created or updated from the POS interface, this ensures
        the AFS ID is correctly saved.
        """
        # Keep the afs_transaction_id from the UI to be saved in the backend
        if 'afs_transaction_id' in payment_vals:
            self.env.context = dict(self.env.context, afs_transaction_id=payment_vals['afs_transaction_id'])
        return super(PosPayment, self).from_ui(payment_vals)

    def _prepare_payment_vals(self, payment_data):
        """
        Override to add the AFS transaction ID to the payment creation values.
        """
        vals = super()._prepare_payment_vals(payment_data)
        if self.env.context.get('afs_transaction_id'):
            vals['afs_transaction_id'] = self.env.context.get('afs_transaction_id')
        return vals
