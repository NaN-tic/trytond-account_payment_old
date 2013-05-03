# This file is part of account_payment module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from decimal import Decimal
from trytond.model import Workflow, ModelView, ModelSQL, fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval, If, Equal
from trytond.transaction import Transaction
__all__ = [
#    'AccountPaymentJournalType',
    'AccountPaymentJournal',
    'AccountPayment',
    'Line',
    ]
__metaclass__ = PoolMeta
_STATES = {
    'readonly': Eval('state') != 'draft',
}


class AccountPaymentJournal(ModelSQL, ModelView):
    'Account Payment Journal'
    __name__ = 'account.payment.journal'

    name = fields.Char('Name', required=True, translate=True)
    active = fields.Boolean('Active')
    company = fields.Many2One('company.company', 'Company', required=True,
        select=True, readonly=True)
    journal = fields.Many2One('account.journal', 'Journal', required=True)
    type = fields.Selection([], 'Type of payment file', required=False)

    @staticmethod
    def default_active():
        return True

    @staticmethod
    def default_company():
        return Transaction().context.get('company')


class AccountPayment(Workflow, ModelSQL, ModelView):
    'Account Payment'
    __name__ = 'account.payment'
    _rec_name = 'number'

    number = fields.Char('Number', required=True,
        states=_STATES, readonly=True)
    type = fields.Selection([
            ('payable', 'Payable'),
            ('receivable', 'Receivable'),
            ('both', 'Both'),
        ], 'Type', states=_STATES)
    company = fields.Many2One('company.company', 'Company', required=True,
        select=True, readonly=True, states=_STATES)
    payment_journal = fields.Many2One('account.payment.journal',
        'Payment Journal', required=True, states=_STATES)
    planned_date = fields.Date('Planned Date', states=_STATES,
        help='Date when the payment entity must process the payment order.')
    done_date = fields.Date('Done Date', states=_STATES, readonly=True,
        help='Date when the payment order is done.')
    currency_digits = fields.Function(fields.Integer('Currency Digits'),
        'get_currency_digits')
    total_amount = fields.Numeric('Amount', depends=['currency_digits'],
        digits=(16, Eval('currency_digits', 2)), states=_STATES)
    lines = fields.One2Many('account.move.line', 'payment', 'Lines',
        states=_STATES, depends=['state', 'id', 'type'], domain=[
            If(Equal(Eval('state'), 'draft'),
                ('reconciliation', '=', False),
                ()),
            If(Equal(Eval('type'), 'payable'),
                ('account.kind', '=', 'payable'),
                If(Equal(Eval('type'), 'receivable'),
                    ('account.kind', '=', 'receivable'),
                    ('account.kind', 'in', ['payable', 'receivable']))
                ),
            ['OR',
                ('payment', '=', False),
                ('payment', '=', Eval('id')),
                ],
            ])
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
        ], 'State', readonly=True, required=True)

    @classmethod
    def __setup__(cls):
        super(AccountPayment, cls).__setup__()
        cls._transitions |= set((
            ('draft', 'done'),
            ('done', 'draft'),
        ))
        cls._buttons.update({
                'draft': {
                    'invisible': Eval('state') == 'draft',
                    },
                'confirm': {
                    'invisible': Eval('state') == 'done',
                    },
                })

    @staticmethod
    def default_company():
        return Transaction().context.get('company')

    @staticmethod
    def default_state():
        return 'draft'

    @staticmethod
    def default_type():
        return 'both'

    @staticmethod
    def default_total_amount():
        return Decimal('0.0')

    def get_currency_digits(self, name):
        return self.company.currency.digits

    @classmethod
    def create(cls, vlist):
        Sequence = Pool().get('ir.sequence')
        sequence, = Sequence.search(['code', '=', cls.__name__])
        vlist = [x.copy() for x in vlist]
        for values in vlist:
            if not values.get('number'):
                values['number'] = Sequence.get_id(sequence.id)
        payments = super(AccountPayment, cls).create(vlist)
        return payments

    @classmethod
    def copy(cls, payments, default=None):
        if default is None:
            default = {}
        Sequence = Pool().get('ir.sequence')
        sequence, = Sequence.search(['code', '=', cls.__name__])
        new_payments = []
        for payment in payments:
            default['number'] = Sequence.get_id(sequence.id)
            default['state'] = 'draft'
            new_payments.extend(super(AccountPayment,
                cls).copy([payment], default=default))
        return new_payments

    @classmethod
    @ModelView.button
    @Workflow.transition('done')
    def confirm(cls, payments):
        Date = Pool().get('ir.date')
        cls.write(payments, {'done_date': Date.today()})

    @classmethod
    @ModelView.button
    @Workflow.transition('draft')
    def draft(cls, payments):
        pass


class Line:
    __name__ = 'account.move.line'

    payment = fields.Many2One('account.payment',
        'Payment')

    @classmethod
    def __setup__(cls):
        super(Line, cls).__setup__()
        if hasattr(cls, '_check_modify_exclude'):
            cls._check_modify_exclude.append('payment')
