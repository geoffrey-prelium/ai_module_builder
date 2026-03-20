# -*- coding: utf-8 -*-
from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ai_builder_gemini_api_key = fields.Char(
        string='Gemini API Key (Module Builder)',
        config_parameter='ai_module_builder.gemini_api_key',
        help='Google Vertex / AI Studio API Key for Gemini models'
    )
    
    ai_builder_openai_api_key = fields.Char(
        string='OpenAI API Key (Module Builder)',
        config_parameter='ai_module_builder.openai_api_key',
        help='OpenAI API Key for GPT-4o'
    )
