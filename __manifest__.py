# -*- coding: utf-8 -*-
{
    'name': 'AI Module Builder',
    'version': '1.0',
    'category': 'Productivity/AI',
    'summary': 'Conversational AI to generate and install complete Odoo modules.',
    'description': """
        AI Module Builder
        =================
        Discuss with an AI Architect to generate complete Odoo modules.
        - Conversational requirement gathering
        - Generates models, views, and security files
        - Auto-installs generated module via base_import_module
    """,
    'author': 'Geoffrey LPDE',
    'depends': ['base', 'mail', 'base_import_module'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/menus.xml',
        'views/ai_module_project_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
