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
    trust_payment_journal_id = fields.Many2one('account.journal', string='AR Bank Account', domain=[('type', '=', 'bank')],
                                    help="Bank account used for collecting customer payments")
    trust_checks_journal_id = fields.Many2one('account.journal', string='Checks Bank Account', domain=[('type', '=', 'bank')],
                                    help="Bank account used for registering the checks or cash for the trust.")

    @api.multi
    def open_collect_passthrough_money_trust(self):
        action = self.open_payments_action('inbound')
        action['context'].update({'trust_action': True, 'target_journal_id': self.id})
        action['views'] = [[self.env.ref('account_trust.view_trust_account_payment_tree').id, 'tree']]
        for jr in self:
            if jr.trust_checks_journal_id:
                action['domain'] = [
                    ('journal_id', '=', jr.trust_checks_journal_id.id),
                    ('payment_type', '=', 'inbound'),
                    ('is_deposited', '=', False)
                ]
        return action

    @api.multi
    def open_collect_money_trust(self):
        action = self.open_payments_action('inbound')
        action['context'].update({'trust_action': True})
        return action

    @api.multi
    def open_spend_money_trust(self):
        action = self.open_payments_action('outbound')
        action['context'].update({'trust_action': True})
        return action

    @api.multi
    def open_trust_ar(self):
        action = self.open_payments_action('to_receivables')
        action['context'].update({'trust_action': True})
        return action


class AccountChartTemplate(models.Model):
    _inherit = "account.chart.template"

    # @api.model
    # def generate_journals(self, acc_template_ref, company, journals_dict=None):
    #     print acc_template_ref, company, journals_dict
    #     journal_to_add = [{'name': _('Trust Fund'), 'type': 'bank', 'code': 'TRS', 'favorite': True, 'sequence': 9, 'is_trust_account': True}]
    #     return super(AccountChartTemplate, self).generate_journals(acc_template_ref=acc_template_ref, company=company, journals_dict=journal_to_add)


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.model
    def _default_payment_type(self):
        """ This routine will generate the selection """
        is_trust_action = self._context.get('trust_action')

        sel = [('outbound', 'Send Money'),
               ('inbound', 'Receive Money'),
               ('transfer', 'Internal Transfer'),
               ('to_receivables', 'To Customer Invoices'),
               ('to_payables', 'To Supplier Bills')]

        if not is_trust_action:
            sel.remove(('to_receivables', 'To Customer Invoices'))
            sel.remove(('to_payables', 'To Supplier Bills'))
        else:
            sel.remove(('transfer', 'Internal Transfer'))

        return sel

    payment_type = fields.Selection('_default_payment_type', string='Payment Type', required=True)
    is_deposited = fields.Boolean('Is Deposited?', help="This is a technical field, means the check is deposited on the passthrough account")

    @api.multi
    def deposit_check_cash(self):
        target_journal_id = self._context.get('target_journal_id')
        if not target_journal_id:
            raise UserError(_("There is no target journal defined"))
        for jr in self:
            Payment = self.env['account.payment']
            payment = Payment.create({
                'amount': jr.amount,
                'anva_trx_id': jr.anva_trx_id and jr.anva_trx_id.id or False,
                'company_id': jr.company_id.id,
                'journal_id': target_journal_id,
                'partner_id': jr.partner_id.id,
                'partner_type': jr.partner_type,
                'payment_type': jr.payment_type,
                'payment_method_id': jr.payment_method_id.id,
                'project_id': jr.project_id.id,
                'payment_reference': jr.payment_reference,
                'payment_method_code': 'manual',
            })
            payment.post()
            jr.is_deposited = True

        return payment.journal_id.open_collect_passthrough_money_trust()

    @api.multi
    def post(self):
        res = super(AccountPayment, self).post()
        for recv in self:
            if self.journal_id.is_trust_account:
                if not recv.partner_id:
                    raise UserError(_("You need to select a partner"))
                if not recv.company_id.account_trust_id:
                    raise UserError(_("You need to set a trust account in company form.\n"
                                      "Please go to Settings >> Companies and chose an account."))
        return res

    def _compute_destination_account_id(self):
        super(AccountPayment, self)._compute_destination_account_id()
        # If it is a trust account type and has checks or cash origin account
        if self.journal_id.is_trust_account and self.journal_id.trust_checks_journal_id:
            self.destination_account_id = self.journal_id.trust_checks_journal_id.default_debit_account_id.id
        # If it is a trust account type
        elif self.journal_id.is_trust_account:
            self.destination_account_id = self.env.user.company_id.account_trust_id.id
