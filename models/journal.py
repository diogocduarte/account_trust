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
    trust_payment_journal_id = fields.Many2one('account.journal', string='Trust Payment Journal',
                                               domain=[('type', 'in', ('bank', 'cash'))])

    @api.multi
    def open_collect_money_trust(self):
        action = self.open_payments_action('inbound', mode='form')
        action['context'].update({'trust_deposit': True})
        return action


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.multi
    def post(self):
        res = super(AccountPayment, self).post()
        is_trust_deposit = self._context.get('trust_deposit')
        for recv in self:
            if is_trust_deposit:
                if not recv.partner_id:
                    raise UserError(_("You need to select a partner"))
                if not recv.company_id.account_trust_id:
                    raise UserError(_("You need to set a trust account in company form.\n"
                                      "Please go to Settings >> Companies and chose an account."))
        return res

    def _compute_destination_account_id(self):
        res = super(AccountPayment, self)._compute_destination_account_id()
        is_trust_deposit = self._context.get('trust_deposit')

        print(is_trust_deposit, self.env.user.company_id.account_trust_id)

        if is_trust_deposit:
            self.destination_account_id = self.env.user.company_id.account_trust_id.id

    #
    # def _create_payment_entry(self, amount):
    #     """ Create a journal entry corresponding to a payment, if the payment references invoice(s) they are reconciled.
    #         Return the journal entry.
    #     """