# -*- coding: utf-8 -*-
from odoo import models, fields

class AiModuleMessage(models.Model):
    _name = 'ai.module.message'
    _description = 'AI Module Conversation Message'
    _order = 'create_date asc'

    project_id = fields.Many2one('ai.module.project', string='Project', required=True, ondelete='cascade')
    
    role = fields.Selection([
        ('user', 'User'),
        ('assistant', 'AI Architect'),
        ('system', 'System Instruction')
    ], string='Role', required=True)
    
    content = fields.Text(string='Content', required=True)
    is_code_payload = fields.Boolean(string='Is Code Payload', default=False, help="True if this message contains the final JSON structure of the module.")
