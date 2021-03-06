# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv import expression


class ResCompany(models.Model):
    _inherit = 'res.company'

    account_trust_id = fields.Many2one('account.account', string="Trust Account",
                                       domain="[('internal_type', '=', 'other'), ('deprecated', '=', False)]",
                                       help="This account will be used as counterpart for the receivings on the trust accounts.")


class AccountJournal(models.Model):
    _inherit = "account.journal"

    is_trust_account = fields.Boolean('Is a Escrow/Trust Account?', help="This is a technical field")
    trust_payment_journal_id = fields.Many2one('account.journal', string='AR Bank Account',
                                               domain=[('type', '=', 'bank')],
                                               help="Bank account used for collecting customer payments")
    trust_checks_journal_id = fields.Many2one('account.journal', string='Checks Bank Account',
                                              domain=[('type', '=', 'bank')],
                                              help="Passthrough bank account used for registering the checks or cash for the trust.")

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
                    ('state', '!=', 'draft'),
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
        action['context'].update({'trust_action': True, 'default_partner_type': 'customer'})
        return action

    @api.multi
    def open_trust_ar(self):
        action = self.open_payments_action('to_receivables')
        action['context'].update({'trust_action': True})
        return action


class AccountPayment(models.Model):
    _inherit = "account.payment"

    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        if hasattr(super(AccountPayment, self), '_onchange_payment_type'):
            res = super(AccountPayment, self)._onchange_payment_type()
            if self.invoice_ids:
                domain = res['domain']['journal_id']
                domain = expression.AND(
                    [[('is_trust_account', '=', True), ('trust_payment_journal_id', '!=', False)], domain])
                domain = expression.OR([[('is_trust_account', '=', False)], domain])
                res['domain']['journal_id'] = domain
        return res

    is_deposited = fields.Boolean('Is Deposited?',
                                  help="This is a technical field, means the check is deposited on the passthrough account")

    def _prepare_payment_values(self, origin_journal_id):
        """This method is for overriding and passing additional values"""
        return {
            'amount': origin_journal_id.amount,
            'company_id': origin_journal_id.company_id.id,
            'partner_id': origin_journal_id.partner_id.id,
            'partner_type': origin_journal_id.partner_type,
            'payment_type': origin_journal_id.payment_type,
            'payment_method_id': origin_journal_id.payment_method_id.id,
            'project_id': origin_journal_id.project_id.id,
            'payment_reference': origin_journal_id.payment_reference,
            'payment_method_code': 'manual',
        }

    @api.multi
    def deposit_check_cash(self):
        target_journal_id = self._context.get('target_journal_id')
        if not target_journal_id:
            raise UserError(_("There is no target journal defined"))
        for jr in self:
            Payment = self.env['account.payment']
            vals = self._prepare_payment_values(jr)
            vals.update({
                'journal_id': target_journal_id,
            })
            payment = Payment.create(vals)
            payment.post()
            jr.is_deposited = True

        return payment.journal_id.open_collect_passthrough_money_trust()

    @api.multi
    def post(self):
        for recv in self:
            if self.journal_id.is_trust_account:
                if recv.invoice_ids:
                    if not (recv.journal_id.trust_payment_journal_id and recv.journal_id.is_trust_account):
                        raise UserError(_("You cannot use an undeposited checks/cash account for paying invoices."))
                else:
                    if not recv.company_id.account_trust_id:
                        raise UserError(_("You need to set a trust account in company form.\n"
                                          "Please go to Settings >> Companies and chose an account."))
        res = super(AccountPayment, self).post()

        return res

    def _compute_destination_account_id(self):
        super(AccountPayment, self)._compute_destination_account_id()
        context = self._context
        if not self.invoice_ids and self.payment_type == 'inbound':

            # If it is a trust account type for passthrough (checks or cash)
            if self.journal_id.is_trust_account and not self.journal_id.trust_checks_journal_id and not self.journal_id.trust_payment_journal_id:
                self.destination_account_id = self.env.user.company_id.account_trust_id.id

            # If it is a trust account type and has a passthrough account
            elif self.journal_id.is_trust_account and self.journal_id.trust_checks_journal_id:
                self.destination_account_id = self.journal_id.trust_checks_journal_id.default_debit_account_id.id

            # If it is a trust account type without passthrough (merchant)
            elif self.journal_id.is_trust_account and not self.journal_id.trust_checks_journal_id and self.journal_id.trust_payment_journal_id:
                self.destination_account_id = self.env.user.company_id.account_trust_id.id
