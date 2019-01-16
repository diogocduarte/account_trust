# -*- coding: utf-8 -*-
{
    'name': 'Trust Accounting',
    'version': '11.0',
    'author': 'OdooGAP',
    'summary': 'Odoo Trust Fund / Escrow Accounting',
    'description': """
Odoo Trust Fund / Escrow Accounting
=====================


    """,
    'website': 'http://www.odoogap.com',
    'depends': ['account'],
    'category': 'Invoicing Management',
    'data': [
        'views/journal_views.xml',
        'views/res_company_views.xml'
    ],
    'test': [
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': '_auto_install',
}
