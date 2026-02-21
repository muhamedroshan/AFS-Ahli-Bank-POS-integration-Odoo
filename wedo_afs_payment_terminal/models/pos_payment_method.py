import logging
from pprint import pprint

# Corrected relative import for a module in the same package
from .afs_class import PaymentConnectAFS

from odoo import models, fields
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    # --- Fields for AFS Configuration ---
    afs_tid = fields.Char(string='AFS Tid', help='Terminal ID provided by AFS.')
    afs_mid = fields.Char(string='AFS Mid', help='Merchant ID provided by AFS.')
    afs_username = fields.Char(string='AFS Username', help='API Username for AFS.')
    afs_fullname = fields.Char(string="AFS Full Name", help="Full name associated with the AFS account.")
    afs_merchant_secure_key = fields.Char(string='AFS Merchant Secure Key', help='Secure key for transaction hashing/signing.')
    afs_is_test_mode = fields.Boolean(string='AFS Test Mode', help='Check this to use the AFS test/sandbox environment.')

    def _get_payment_terminal_selection(self):
        """Adds 'afs' to the list of available payment terminals."""
        res = super()._get_payment_terminal_selection()
        return res + [('afs', 'AFS')]

    def _get_afs_api(self):
        """Helper method to instantiate and return the AFS connection class."""
        if not all([self.afs_mid, self.afs_tid, self.afs_username, self.afs_merchant_secure_key]):
            _logger.error("AFS credentials are not fully configured for payment method: %s", self.display_name)
            return None
        # Pass the payment method record to the class constructor
        return PaymentConnectAFS(
            service_url="https://ereceiptom.afs.com.bh/Ecr.Om.Abo/EcrComInterface.svc",
            tid=self.afs_tid,
            mid=self.afs_mid,
            secure_key=self.afs_merchant_secure_key
        )

    # --- AFS API Communication Methods ---
    def afs_make_payment_request(self, data):
        """
        Sends a payment request to the AFS terminal using the PaymentConnectAFS class.
        """
        _logger.info("afs_make_payment_request for POS order: %s", data.get('payment_id'))
        line_uuid = data.get('payment_id')

        afs_api = self._get_afs_api()

        if not afs_api:
            return {'status': 'error', 'message': 'AFS terminal is not configured correctly.', 'line_uuid': line_uuid}

        try:
            response = afs_api.send_apex_sale(
                amount=data.get('amount'),
                invoice_number=line_uuid
            )
            # Your class should return a dict in the format the POS expects, including the line_uuid
            if "APPROVAL" in response.get('PosRespText') and "Success" in response.get('WebResponseStatus'):
                return { 'status' : 'success'}
            else:
                return { 'status' : 'waiting', 'afs_transaction_id' : line_uuid }
        except Exception as e:
            _logger.error("Error calling PaymentConnectAFS make_payment: %s", e, exc_info=True)
            return {'status': 'error', 'message': str(e), 'line_uuid': line_uuid}

    def afs_fetch_payment_status(self, data):
        """
        Polls the AFS API to get the status of a pending transaction.
        """
        _logger.info("afs_fetch_payment_status for transaction: %s", data.get('afs_transaction_id'))
        line_uuid = data.get('line_uuid')

        afs_api = self._get_afs_api()
        if not afs_api:
            return {'status': 'error', 'message': 'AFS terminal is not configured correctly.', 'line_uuid': line_uuid}

        try:
            response = afs_api.send_apex_enquiry(
                reference_number=data.get('afs_transaction_id')
            )
            if "APPROVAL" in response.get('PosRespText') and "Success" in response.get('WebResponseStatus'):
                return {'status': 'success'}
            else:
                return {'status': 'polling',}
        except Exception as e:
            _logger.error("Error calling PaymentConnectAFS fetch_status: %s", e, exc_info=True)
            # On network errors, it's often best to keep polling
            return {'status': 'polling', 'message': str(e), 'line_uuid': line_uuid}

    def afs_cancel_payment_request(self, data):
        """
        Sends a request to cancel a pending transaction.
        """
        _logger.info("afs_cancel_payment_request for transaction: %s", data.get('afs_transaction_id'))
        line_uuid = data.get('line_uuid')

        afs_api = self._get_afs_api()
        if not afs_api:
            return {'status': 'error', 'message': 'AFS terminal is not configured correctly.', 'line_uuid': line_uuid}

        try:
            # Assuming your class has a 'cancel_payment' method
            response = afs_api.send_apex_cancellation()
            if "Success" in response.get('WebResponseStatus'):
                return {'status': 'cancelled'}
            else:
                return {'status': 'error', 'message': response.get('PosRespText')}
        except Exception as e:
            _logger.error("Error calling PaymentConnectAFS cancel_payment: %s", e, exc_info=True)
            return {'status': 'error', 'message': str(e), 'line_uuid': line_uuid}
