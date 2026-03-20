# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AiModuleProject(models.Model):
    _name = 'ai.module.project'
    _description = 'AI Module Builder Project'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Module Concept', required=True, tracking=True)
    description = fields.Text(string='Initial Need')
    
    state = fields.Selection([
        ('draft', 'Draft / Conception'),
        ('conversing', 'In Discussion'),
        ('generating', 'Generating Source Code'),
        ('done', 'Module Ready / Installed')
    ], string='Status', default='draft', required=True, tracking=True)

    llm_provider = fields.Selection([
        ('gemini', 'Google Gemini 2.5 Pro'),
        ('gemini-2.5-flash', 'Google Gemini 2.5 Flash'),
        ('openai', 'OpenAI GPT-4o'),
    ], string='AI Model', default='gemini-2.5-flash', required=True)

    ai_message_ids = fields.One2many('ai.module.message', 'project_id', string='Conversation')
    
    technical_name = fields.Char(string='Technical Module Name', help='e.g., custom_crm_addon', tracking=True)
    zip_attachment_id = fields.Many2one('ir.attachment', string='Generated Module (.zip)', copy=False)
    
    new_message = fields.Text(string='Your Reply')
    
    def action_start_discussion(self):
        for rec in self:
            rec.state = 'conversing'
            # Instanciate the first system prompt
            self.env['ai.module.message'].create({
                'project_id': rec.id,
                'role': 'system',
                'content': "You are an Expert Odoo 19 Architect. Your job is to help the user build a complete Odoo module. Start by asking 1 or 2 precise questions about the models to create, the views, and security rules. Once they answer, ask more if needed. You MUST fully understand the requirement before writing any code."
            })
            
    def action_send_message(self):
        """ Send the user's message to the chat history and trigger the AI. """
        for rec in self:
            if not rec.new_message:
                continue
            
            # Save user message
            self.env['ai.module.message'].create({
                'project_id': rec.id,
                'role': 'user',
                'content': rec.new_message
            })
            rec.new_message = False
            
            # Call LLM with the full history
            response_text = rec._call_llm()
            
            # Save AI response
            if response_text:
                self.env['ai.module.message'].create({
                    'project_id': rec.id,
                    'role': 'assistant',
                    'content': response_text
                })
            
    def _call_llm(self):
        self.ensure_one()
        import requests
        import json
        from odoo.exceptions import UserError
        
        company = self.env.company
        model = self.llm_provider
        
        history = self.ai_message_ids.sorted('create_date')
        
        if model.startswith('gemini'):
            api_key = self.env['ir.config_parameter'].sudo().get_param('ai_module_builder.gemini_api_key') or company.ai_agent_gemini_api_key
            if not api_key:
                raise UserError("Please configure your Google Gemini API Key in Settings.")
            
            gemini_model = "gemini-2.5-flash" if "1.5" in model else model
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{gemini_model}:generateContent?key={api_key}"
            
            contents = []
            system_instruction = ""
            
            for msg in history:
                if msg.role == 'system':
                    system_instruction += msg.content + "\n"
                else:
                    role = "user" if msg.role == 'user' else "model"
                    contents.append({
                        "role": role,
                        "parts": [{"text": msg.content}]
                    })
            
            payload = {
                "systemInstruction": {"parts": [{"text": system_instruction}]},
                "contents": contents
            }
            
            try:
                response = requests.post(endpoint, headers={"Content-Type": "application/json"}, json=payload, timeout=60)
                response.raise_for_status()
                data = response.json()
                return data['candidates'][0]['content']['parts'][0]['text']
            except Exception as e:
                raise UserError(f"Gemini API Error: {str(e)}\nResponse: {response.text if 'response' in locals() else ''}")

        elif model.startswith('openai'):
            api_key = self.env['ir.config_parameter'].sudo().get_param('ai_module_builder.openai_api_key') or company.ai_agent_openai_api_key
            if not api_key:
                raise UserError("Please configure your OpenAI API Key in Settings.")
            
            messages = []
            for msg in history:
                messages.append({
                    "role": "system" if msg.role == 'system' else ("user" if msg.role == 'user' else "assistant"),
                    "content": msg.content
                })
                
            payload = {
                "model": "gpt-4o",
                "messages": messages
            }
            
            try:
                response = requests.post("https://api.openai.com/v1/chat/completions", headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, json=payload, timeout=60)
                response.raise_for_status()
                data = response.json()
                return data['choices'][0]['message']['content']
            except Exception as e:
                raise UserError(f"OpenAI API Error: {str(e)}\nResponse: {response.text if 'response' in locals() else ''}")
                
        return False
        
    def action_generate_code(self):
        for rec in self:
            rec.state = 'generating'
            
            # 1. Force the AI to output the final code as JSON
            extraction_prompt = "You have all the information required. Now, generate the complete source code for this Odoo 19 module. " \
                                "Your response MUST be exclusively a valid JSON object wrapped in a ```json ... ``` block. " \
                                "The JSON format must be strictly: {\"files\": [{\"path\": \"__manifest__.py\", \"content\": \"...\"}, {\"path\": \"models/model.py\", \"content\": \"...\"}]} " \
                                f"The technical name of the module is '{rec.technical_name or 'ai_generated_module'}'. Ensure all Odoo 19 standards are met."
             
            # Append this as a temporary system message to force the output
            temp_msg = self.env['ai.module.message'].create({
                'project_id': rec.id,
                'role': 'system',
                'content': extraction_prompt
            })
            
            try:
                response_text = rec._call_llm()
            finally:
                # Remove the temporary prompt to keep history clean
                temp_msg.unlink()
                
            if not response_text:
                raise self.env['res.exceptions'].UserError("The AI did not return any code.")
                
            # Save the raw payload to history
            self.env['ai.module.message'].create({
                'project_id': rec.id,
                'role': 'assistant',
                'content': "Here is the generated module architecture:\n\n" + response_text,
                'is_code_payload': True
            })
            
            # 2. Parse the JSON
            import re
            import json
            import io
            import zipfile
            import base64
            from odoo.exceptions import UserError
            
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if not json_match:
                # Fallback if no markdown block
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                
            if not json_match:
                raise UserError("Failed to extract JSON structure from the AI response.")
                
            try:
                module_data = json.loads(json_match.group(1) if r'```' in response_text else json_match.group(0))
            except json.JSONDecodeError as e:
                raise UserError(f"AI generated invalid JSON: {str(e)}")
                
            # 3. Build the ZIP file in memory
            module_name = rec.technical_name or 'ai_generated_module'
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_obj in module_data.get('files', []):
                    path = file_obj.get('path')
                    content = file_obj.get('content')
                    if path and content:
                        # Ensure the path is prefixed with the module name
                        full_path = f"{module_name}/{path}"
                        zip_file.writestr(full_path, content)
                        
            zip_content = zip_buffer.getvalue()
            zip_base64 = base64.b64encode(zip_content)
            
            # 4. Save Attachment
            attachment = self.env['ir.attachment'].create({
                'name': f"{module_name}.zip",
                'type': 'binary',
                'datas': zip_base64,
                'res_model': 'ai.module.project',
                'res_id': rec.id,
                'mimetype': 'application/zip'
            })
            rec.zip_attachment_id = attachment.id
            
            # 5. Install the module via Odoo native base_import_module
            IrModule = self.env['ir.module.module']
            if hasattr(IrModule, 'import_zipfile'):
                try:
                    # In newer Odoo versions, import_zipfile takes the file directly
                    IrModule.import_zipfile(zip_buffer, force=True)
                except Exception as e:
                    # Odoo 16/17 might take base64
                    try:
                        IrModule.import_zipfile(zip_base64, force=True)
                    except Exception as fallback_e:
                        pass # Installation failed, but ZIP is created.
            
            rec.state = 'done'
