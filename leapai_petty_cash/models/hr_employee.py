from odoo import models, fields, api, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    petty_cash_fund_ids = fields.One2many('petty.cash.fund', 'employee_id', string='Petty Cash Funds')
    petty_cash_fund_count = fields.Integer(compute='_compute_petty_cash_count', string='Petty Cash Funds')
    has_petty_cash = fields.Boolean(compute='_compute_petty_cash_count', string='Has Petty Cash Fund')

    def _compute_petty_cash_count(self):
        for emp in self:
            count = len(emp.petty_cash_fund_ids)
            emp.petty_cash_fund_count = count
            emp.has_petty_cash = count > 0

    def action_petty_cash_setup(self):
        """Open wizard to set up petty cash fund for the employee."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Petty Cash Setup'),
            'res_model': 'petty.cash.fund',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_employee_id': self.id,
                'default_name': f'Petty Cash - {self.name}',
            },
        }

    def action_view_petty_cash(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Petty Cash Funds'),
            'res_model': 'petty.cash.fund',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id},
        }
