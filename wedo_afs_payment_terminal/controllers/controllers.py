# from odoo import http


# class WedoAfsPaymentTerminal(http.Controller):
#     @http.route('/wedo_afs_payment_terminal/wedo_afs_payment_terminal', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/wedo_afs_payment_terminal/wedo_afs_payment_terminal/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('wedo_afs_payment_terminal.listing', {
#             'root': '/wedo_afs_payment_terminal/wedo_afs_payment_terminal',
#             'objects': http.request.env['wedo_afs_payment_terminal.wedo_afs_payment_terminal'].search([]),
#         })

#     @http.route('/wedo_afs_payment_terminal/wedo_afs_payment_terminal/objects/<model("wedo_afs_payment_terminal.wedo_afs_payment_terminal"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('wedo_afs_payment_terminal.object', {
#             'object': obj
#         })

