# from odoo import models, fields, api


# class wedo_afs_payment_terminal(models.Model):
#     _name = 'wedo_afs_payment_terminal.wedo_afs_payment_terminal'
#     _description = 'wedo_afs_payment_terminal.wedo_afs_payment_terminal'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

