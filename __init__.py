# -*- coding: utf-8 -*-
from . import models
from odoo import api, SUPERUSER_ID, _


def create_trust_journal(env, company, acc_template_ref):
    bank_journals = env['account.journal']
    # Create the journals that will trigger the account.account creation
    for acc in acc_template_ref:
        bank_journals += env['account.journal'].create({
            'name': acc['acc_name'],
            'type': acc['account_type'],
            'is_trust_account': True,
            'company_id': company.id,
            'currency_id': acc.get('currency_id', env['res.currency']).id,
            'sequence': 10
        })

    return bank_journals


def _auto_install(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    company_id = env.user.company_id
    acc_template_ref = [{'acc_name': _('Trust Fund'), 'account_type': 'bank'}]
    create_trust_journal(env, company_id, acc_template_ref)
