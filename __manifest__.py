# -*- coding: utf-8 -*-
{
    'name': 'Trust Accounting',
    'version': '10.0',
    'author': 'OdooGAP',
    'summary': 'Odoo Trust Fund / Escrow Accounting',
    'description': """
Odoo Trust Fund / Escrow Accounting
===================================

This module implements basic functionalites for managing trust accounts. 
This featureset is very common in Law practice firms where lawyers need
to maintain a correct CoA while managing client trusts.

    """,
    'website': 'http://www.odoogap.com',
    'depends': ['base', 'account_accountant'],
    'category': 'Invoicing Management',
    'data': [
        'views/journal_views.xml',
        'views/res_company_views.xml'
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    #'post_init_hook': '_auto_install',
}
