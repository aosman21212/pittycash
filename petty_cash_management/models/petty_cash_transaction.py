from odoo import models, fields, api, _


class PettyCashTransaction(models.Model):
    _name = 'petty.cash.transaction'
    _description = 'Petty Cash Transaction'
    _order = 'date desc, id desc'
    _rec_name = 'description'

    fund_id = fields.Many2one('petty.cash.fund', string='Petty Cash Fund', required=True, ondelete='cascade')
    employee_id = fields.Many2one(related='fund_id.employee_id', string='Employee', store=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.today)
    description = fields.Char(string='Description', required=True)
    debit = fields.Monetary(string='Debit (In)', currency_field='currency_id', default=0.0)
    credit = fields.Monetary(string='Credit (Out)', currency_field='currency_id', default=0.0)
    currency_id = fields.Many2one(related='fund_id.currency_id', store=True)
    request_id = fields.Many2one('petty.cash.request', string='Request', ondelete='set null')
    move_id = fields.Many2one('account.move', string='Journal Entry')
    company_id = fields.Many2one(related='fund_id.company_id', store=True)
    balance = fields.Monetary(string='Balance', compute='_compute_balance', currency_field='currency_id', store=False)

    @api.depends('fund_id', 'fund_id.initial_balance', 'fund_id.transaction_ids',
                 'fund_id.transaction_ids.debit', 'fund_id.transaction_ids.credit')
    def _compute_balance(self):
        for txn in self:
            if not txn.fund_id:
                txn.balance = 0.0
                continue
            balance = txn.fund_id.initial_balance
            for t in txn.fund_id.transaction_ids.sorted('id'):
                balance += t.debit - t.credit
                if t.id == txn.id:
                    break
            txn.balance = balance
