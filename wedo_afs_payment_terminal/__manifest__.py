{
    'name': "wedo_afs_payment_terminal",
    'summary': "Integrate your POS with a AFS payment terminal",
    'sequence': 6,
    'description': """
Allow AFS POS payments
==============================

This module allows customers to connect their AFS payment terminal in Oman to Odoo as payment terminal
    """,

    'author': "Wedo Technologies",
    'website': "https://www.wedo.om",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales/Point of Sale',
    'version': '0.2',

    # any module necessary for this one to work correctly
    'depends': ['point_of_sale'],
    'installable': True,
    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/pos_payment_method_views.xml',
    ],

    'assets': {
        'point_of_sale._assets_pos': [
            'wedo_afs_payment_terminal/static/src/**/*',
        ]
    }
}
