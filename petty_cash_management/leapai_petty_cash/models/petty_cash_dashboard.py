from odoo import models, fields, api
from datetime import date


class PettyCashDashboard(models.AbstractModel):
    _name = 'petty.cash.dashboard'
    _description = 'Petty Cash Dashboard'

    @api.model
    def get_dashboard_data(self):
        Request = self.env['petty.cash.request']
        Fund = self.env['petty.cash.fund']
        Transaction = self.env['petty.cash.transaction']

        today = date.today()
        month_start = today.replace(day=1)

        total_funds = Fund.search_count([('state', '=', 'active')])
        total_balance = sum(Fund.search([('state', '=', 'active')]).mapped('current_balance'))

        requests_draft = Request.search_count([('state', '=', 'draft')])
        requests_submitted = Request.search_count([('state', '=', 'submitted')])
        requests_approved = Request.search_count([('state', '=', 'approved')])
        requests_paid = Request.search_count([('state', '=', 'paid')])
        requests_rejected = Request.search_count([('state', '=', 'rejected')])
        requests_this_month = Request.search_count([
            ('date', '>=', month_start.strftime('%Y-%m-%d'))
        ])

        amount_this_month = sum(Request.search([
            ('date', '>=', month_start.strftime('%Y-%m-%d')),
            ('state', 'in', ['approved', 'paid'])
        ]).mapped('amount'))

        # Recent requests
        recent_requests = []
        for req in Request.search([], order='date desc, id desc', limit=10):
            recent_requests.append({
                'id': req.id,
                'name': req.name,
                'employee': req.employee_id.name or '',
                'date': req.date.strftime('%Y-%m-%d') if req.date else '',
                'amount': req.amount,
                'currency_symbol': req.currency_id.symbol or '$',
                'state': req.state,
                'reason': (req.reason or '')[:50],
            })

        # Recent transactions
        recent_transactions = []
        for txn in Transaction.search([], order='date desc, id desc', limit=8):
            recent_transactions.append({
                'id': txn.id,
                'date': txn.date.strftime('%Y-%m-%d') if txn.date else '',
                'description': txn.description or '',
                'debit': txn.debit,
                'credit': txn.credit,
                'employee': txn.employee_id.name or '',
                'currency_symbol': txn.currency_id.symbol or '$',
            })

        return {
            'total_funds': total_funds,
            'total_balance': total_balance,
            'requests_draft': requests_draft,
            'requests_submitted': requests_submitted,
            'requests_approved': requests_approved,
            'requests_paid': requests_paid,
            'requests_rejected': requests_rejected,
            'requests_this_month': requests_this_month,
            'amount_this_month': amount_this_month,
            'recent_requests': recent_requests,
            'recent_transactions': recent_transactions,
            'currency_symbol': self.env.company.currency_id.symbol or '$',
        }
