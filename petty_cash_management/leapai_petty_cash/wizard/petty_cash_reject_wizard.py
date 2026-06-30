from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PettyCashRejectWizard(models.TransientModel):
    _name = 'petty.cash.reject.wizard'
    _description = 'Reject Petty Cash Request'

    request_id = fields.Many2one('petty.cash.request', string='Request', required=True)
    rejection_reason = fields.Text(string='Rejection Reason', required=True)

    def action_reject(self):
        self.ensure_one()
        self.request_id.rejection_reason = self.rejection_reason
        self.request_id.state = 'rejected'
        self.request_id.message_post(
            body=_('Request rejected. Reason: %s') % self.rejection_reason
        )
        return {'type': 'ir.actions.act_window_close'}
