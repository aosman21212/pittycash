from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PettyCashFund(models.Model):
    _name = 'petty.cash.fund'
    _description = 'Petty Cash Fund'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'

    name = fields.Char(string='Fund Name', required=True, tracking=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True)
    account_id = fields.Many2one('account.account', string='Cash Account', tracking=True,
        help='Dedicated account for this petty cash fund')
    journal_id = fields.Many2one('account.journal', string='Cash Journal', tracking=True,
        help='Dedicated journal for petty cash transactions')
    initial_balance = fields.Monetary(string='Initial Balance', currency_field='currency_id', tracking=True)
    current_balance = fields.Monetary(string='Current Balance', compute='_compute_current_balance',
        currency_field='currency_id', store=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
        default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one('res.company', string='Company',
        default=lambda self: self.env.company)
    state = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], string='Status', default='active', tracking=True)
    request_ids = fields.One2many('petty.cash.request', 'fund_id', string='Requests')
    transaction_ids = fields.One2many('petty.cash.transaction', 'fund_id', string='Transactions')
    request_count = fields.Integer(compute='_compute_request_count', string='Requests')
    transaction_count = fields.Integer(compute='_compute_transaction_count', string='Transactions')
    notes = fields.Text(string='Notes')

    @api.depends('transaction_ids', 'transaction_ids.debit', 'transaction_ids.credit', 'initial_balance')
    def _compute_current_balance(self):
        for fund in self:
            total_debit = sum(fund.transaction_ids.mapped('debit'))
            total_credit = sum(fund.transaction_ids.mapped('credit'))
            fund.current_balance = fund.initial_balance + total_debit - total_credit

    def _compute_request_count(self):
        for fund in self:
            fund.request_count = self.env['petty.cash.request'].search_count([('fund_id', '=', fund.id)])

    def _compute_transaction_count(self):
        for fund in self:
            fund.transaction_count = len(fund.transaction_ids)

    def action_setup_fund(self):
        """Create account and journal automatically for this fund."""
        self.ensure_one()
        if not self.account_id:
            # Create a dedicated cash account
            account_vals = {
                'name': f'Petty Cash - {self.employee_id.name}',
                'code': self._get_next_account_code(),
                'account_type': 'asset_cash',
                'company_ids': [(4, self.company_id.id)],
                'currency_id': self.currency_id.id,
            }
            account = self.env['account.account'].create(account_vals)
            self.account_id = account

        if not self.journal_id:
            # Create a dedicated journal
            journal_vals = {
                'name': f'Petty Cash - {self.employee_id.name}',
                'code': self._get_next_journal_code(),
                'type': 'cash',
                'default_account_id': self.account_id.id,
                'company_id': self.company_id.id,
                'currency_id': self.currency_id.id,
            }
            journal = self.env['account.journal'].create(journal_vals)
            self.journal_id = journal

        # Create initial balance transaction if set
        if self.initial_balance and not self.transaction_ids:
            self.env['petty.cash.transaction'].create({
                'fund_id': self.id,
                'date': fields.Date.today(),
                'description': _('Initial Balance'),
                'debit': self.initial_balance,
                'credit': 0.0,
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Fund Setup Complete'),
                'message': _('Petty cash account and journal have been created successfully.'),
                'type': 'success',
            }
        }

    def _get_next_account_code(self):
        """Generate unique account code for petty cash."""
        existing = self.env['account.account'].search([('code', 'like', 'PC')], order='code desc', limit=1)
        if existing:
            try:
                num = int(existing.code.replace('PC', '')) + 1
            except Exception:
                num = 1
        else:
            num = 1
        return f'PC{num:03d}'

    def _get_next_journal_code(self):
        """Generate unique journal code for petty cash."""
        existing = self.env['account.journal'].search([('code', 'like', 'PC')], order='code desc', limit=1)
        if existing:
            try:
                num = int(existing.code.replace('PC', '')) + 1
            except Exception:
                num = 1
        else:
            num = 1
        return f'PC{num:02d}'

    def action_view_requests(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Petty Cash Requests'),
            'res_model': 'petty.cash.request',
            'view_mode': 'list,form',
            'domain': [('fund_id', '=', self.id)],
            'context': {'default_fund_id': self.id, 'default_employee_id': self.employee_id.id},
        }

    def action_view_transactions(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Transactions'),
            'res_model': 'petty.cash.transaction',
            'view_mode': 'list,form',
            'domain': [('fund_id', '=', self.id)],
        }

    def action_set_inactive(self):
        self.state = 'inactive'

    def action_set_active(self):
        self.state = 'active'
