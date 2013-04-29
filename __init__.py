# This file is part of account_payment module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from .account_payment import *


def register():
    Pool.register(
        AccountPaymentJournalType,
        AccountPaymentJournal,
        AccountPayment,
        Line,
        module='account_payment', type_='model')
