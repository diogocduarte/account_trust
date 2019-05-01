# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResCompany(models.Model):
    _inherit = 'res.company'

    account_trust_id = fields.Many2one('account.account', string="Trust Account",
        domain="[('internal_type', '=', 'other'), ('deprecated', '=', False)]",
        help="This account will be used as counterpart for the receivings on the trust accounts.")


class AccountJournal(models.Model):
    _inherit = "account.journal"

    is_trust_account = fields.Boolean('Is a Escrow/Trust Account?', help="This is a technical field")
    trust_payment_journal_id = fields.Many2one('account.journal', string='In Bank Account', domain=[('type', '=', 'bank')],
                                    help="Bank account used for collecting customer payments")

    @api.multi
    def open_collect_money_trust(self):
        action = self.open_payments_action('inbound')
        action['context'].update({'trust_deposit': True})
        return action

    @api.multi
    def open_spend_money_trust(self):
        action = self.open_payments_action('outbound')
        action['context'].update({'trust_withdraw': True})
        return action


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    @api.model
    def generate_journals(self, acc_template_ref, company, journals_dict=None):
        journal_to_add = [{'name': _('Trust Fund'), 'type': 'bank', 'code': 'TRS', 'favorite': True, 'sequence': 9, 'is_trust_account': True}]
        return super(AccountChartTemplate, self).generate_journals(acc_template_ref=acc_template_ref, company=company, journals_dict=journal_to_add)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.multi
    def post(self):
        res = super(AccountPayment, self).post()
        is_trust_deposit = self._context.get('trust_deposit')
        is_trust_withdraw = self._context.get('trust_withdraw')
        for recv in self:
            if is_trust_deposit or is_trust_withdraw:
                if not recv.partner_id:
                    raise UserError(_("You need to select a partner"))
                if not recv.company_id.account_trust_id:
                    raise UserError(_("You need to set a trust account in company form.\n"
                                      "Please go to Settings >> Companies and chose an account."))
        return res

    def _compute_destination_account_id(self):
        super(AccountPayment, self)._compute_destination_account_id()
        is_trust_deposit = self._context.get('trust_deposit')
        is_trust_withdraw = self._context.get('trust_withdraw')

        if is_trust_deposit or is_trust_withdraw:
            self.destination_account_id = self.env.user.company_id.account_trust_id.id
