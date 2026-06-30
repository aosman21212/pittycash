from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PettyCashRequest(models.Model):
    _name = 'petty.cash.request'
    _description = 'Petty Cash Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'date desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False,
        default='New', readonly=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True,
        tracking=True, default=lambda self: self.env.user.employee_id)
    fund_id = fields.Many2one('petty.cash.fund', string='Petty Cash Fund', required=True,
        domain="[('employee_id', '=', employee_id), ('state', '=', 'active')]", tracking=True)
    date = fields.Date(string='Request Date', required=True, default=fields.Date.today, tracking=True)
    amount = fields.Monetary(string='Amount', required=True, tracking=True,
        currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='fund_id.currency_id', store=True)
    reason = fields.Text(string='Purpose / Reason', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', tracking=True)
    approved_by = fields.Many2one('res.users', string='Approved By', tracking=True, readonly=True)
    approved_date = fields.Datetime(string='Approval Date', readonly=True)
    paid_date = fields.Date(string='Payment Date', readonly=True)
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True, copy=False)
    company_id = fields.Many2one('res.company', related='fund_id.company_id', store=True)
    notes = fields.Text(string='Internal Notes')
    rejection_reason = fields.Text(string='Rejection Reason', readonly=True)
    current_balance = fields.Monetary(related='fund_id.current_balance', string='Fund Balance',
        currency_field='currency_id')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('petty.cash.request') or 'New'
        return super().create(vals_list)

    def action_submit(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError(_('Amount must be greater than zero.'))
            if not rec.fund_id.journal_id:
                raise UserError(_('Please complete the fund setup first (create account and journal).'))
            rec.state = 'submitted'
            rec.message_post(body=_('Request submitted for approval.'))

    def action_approve(self):
        for rec in self:
            if rec.fund_id.current_balance < rec.amount:
                raise UserError(_('Insufficient balance in the petty cash fund.\nAvailable: %s, Requested: %s') % (
                    rec.fund_id.current_balance, rec.amount))
            # Create journal entry
            move = rec._create_journal_entry()
            rec.move_id = move
            rec.state = 'approved'
            rec.approved_by = self.env.user
            rec.approved_date = fields.Datetime.now()
            # Create transaction record
            self.env['petty.cash.transaction'].create({
                'fund_id': rec.fund_id.id,
                'date': rec.date,
                'description': f'[{rec.name}] {rec.reason[:50] if rec.reason else ""}',
                'credit': rec.amount,
                'debit': 0.0,
                'request_id': rec.id,
                'move_id': move.id,
            })
            rec.message_post(body=_('Request approved by %s.') % self.env.user.name)

    def action_mark_paid(self):
        for rec in self:
            rec.state = 'paid'
            rec.paid_date = fields.Date.today()
            rec.message_post(body=_('Payment registered on %s.') % rec.paid_date)

    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Request'),
            'res_model': 'petty.cash.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_request_id': self.id},
        }

    def action_reset_draft(self):
        for rec in self:
            if rec.move_id:
                rec.move_id.button_cancel()
                rec.move_id.unlink()
            rec.state = 'draft'
            # Remove related transaction
            self.env['petty.cash.transaction'].search([('request_id', '=', rec.id)]).unlink()

    def _create_journal_entry(self):
        """Create accounting journal entry for approved request."""
        self.ensure_one()
        company = self.company_id or self.env.company
        # Get default expense account
        expense_account = self.env['account.account'].search([
            ('account_type', '=', 'expense'),
            ('company_ids', 'in', company.id),
        ], limit=1)
        if not expense_account:
            raise UserError(_('No expense account found. Please configure an expense account.'))

        move_vals = {
            'journal_id': self.fund_id.journal_id.id,
            'date': self.date,
            'ref': f'{self.name} - {self.reason[:50] if self.reason else ""}',
            'line_ids': [
                (0, 0, {
                    'account_id': expense_account.id,
                    'name': f'Petty Cash: {self.reason[:50] if self.reason else self.name}',
                    'debit': self.amount,
                    'credit': 0.0,
                }),
                (0, 0, {
                    'account_id': self.fund_id.account_id.id,
                    'name': f'Petty Cash: {self.name}',
                    'debit': 0.0,
                    'credit': self.amount,
                }),
            ],
        }
        move = self.env['account.move'].create(move_vals)
        move.action_post()
        return move

    def action_view_journal_entry(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Journal Entry'),
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.move_id.id,
        }
