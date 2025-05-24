"""
Alexa Skill para criação de tasks no Jira Cloud
Autor: Alan Abreu
Versão: 1.0.0
"""

import json
import logging
import os
import requests
import base64
from typing import Dict, Any, Optional
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler, AbstractExceptionHandler
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from ask_sdk_model.ui import SimpleCard
import boto3
from botocore.exceptions import ClientError
from datetime import datetime

# Configuração de logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Cliente DynamoDB para persistência
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
USER_TABLE = 'JiraSkillUsers'

class JiraAPIClient:
    """Cliente para interação com a API do Jira Cloud"""
    
    def __init__(self, base_url: str, email: str, api_token: str):
        self.base_url = base_url
        self.email = email
        self.api_token = api_token
        self.auth_header = self._create_auth_header()
    
    def _create_auth_header(self) -> str:
        """Cria header de autenticação Basic Auth para Jira API"""
        credentials = f"{self.email}:{self.api_token}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded_credentials}"
    
    def create_issue(self, title: str, description: str, project_key: str, assignee_id: str) -> Dict[str, Any]:
        """
        Cria uma nova issue no Jira
        
        Args:
            title: Título da task
            description: Descrição da task
            project_key: Chave do projeto/board
            assignee_id: ID do usuário responsável
            
        Returns:
            Dict com dados da issue criada ou erro
        """
        url = f"{self.base_url}/rest/api/3/issue"
        
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": title,
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [{
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}]
                    }]
                },
                "issuetype": {"name": "Task"},
                "assignee": {"id": assignee_id}
            }
        }
        
        headers = {
            "Authorization": self.auth_header,
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro ao criar issue no Jira: {e}")
            return {"error": str(e)}

class UserDataManager:
    """Gerenciador de dados do usuário no DynamoDB"""
    
    @staticmethod
    def get_user_config(user_id: str) -> Optional[Dict[str, Any]]:
        """Busca configuração completa do usuário"""
        try:
            table = dynamodb.Table(USER_TABLE)
            response = table.get_item(Key={'user_id': user_id})
            return response.get('Item')
        except ClientError as e:
            logger.error(f"Erro ao buscar configuração do usuário: {e}")
            return None
    
    @staticmethod
    def save_jira_config(user_id: str, jira_base_url: str, jira_email: str, 
                        jira_api_token: str, jira_user_id: str) -> bool:
        """Salva configuração completa do Jira do usuário"""
        try:
            table = dynamodb.Table(USER_TABLE)
            table.put_item(
                Item={
                    'user_id': user_id,
                    'jira_base_url': jira_base_url,
                    'jira_email': jira_email,
                    'jira_api_token': jira_api_token,
                    'jira_user_id': jira_user_id,
                    'configured': True,
                    'created_at': str(datetime.utcnow()),
                    'updated_at': str(datetime.utcnow())
                }
            )
            return True
        except ClientError as e:
            logger.error(f"Erro ao salvar configuração do usuário: {e}")
            return False
    
    @staticmethod
    def is_user_configured(user_id: str) -> bool:
        """Verifica se o usuário já está configurado"""
        config = UserDataManager.get_user_config(user_id)
        return config is not None and config.get('configured', False)

def create_jira_client(user_config: Dict[str, Any]) -> JiraAPIClient:
    """Cria cliente Jira baseado na configuração do usuário"""
    return JiraAPIClient(
        base_url=user_config['jira_base_url'],
        email=user_config['jira_email'],
        api_token=user_config['jira_api_token']
    )

class LaunchRequestHandler(AbstractRequestHandler):
    """Handler para inicialização do skill"""
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("LaunchRequest")(handler_input)
    
    def handle(self, handler_input: HandlerInput) -> Response:
        """Resposta inicial ao abrir o skill"""
        user_id = handler_input.request_envelope.session.user.user_id
        
        # Verificar se usuário já está configurado
        if UserDataManager.is_user_configured(user_id):
            speak_output = ("Olá! Bem-vindo de volta ao criador de tasks do Jira. "
                           "Você pode dizer: 'criar uma task' para começar. "
                           "Como posso ajudar?")
        else:
            speak_output = ("Olá! Bem-vindo ao criador de tasks do Jira. "
                           "Para começar, precisamos configurar sua conta do Jira. "
                           "Diga: 'configurar Jira' para iniciar a configuração.")
        
        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )

class SetupJiraIntentHandler(AbstractRequestHandler):
    """Handler para configuração inicial do Jira"""
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("SetupJiraIntent")(handler_input)
    
    def handle(self, handler_input: HandlerInput) -> Response:
        """Inicia o processo de configuração do Jira"""
        session_attr = handler_input.attributes_manager.session_attributes
        session_attr['setup_step'] = 'domain'
        
        speak_output = ("Vamos configurar sua conta do Jira. "
                       "Primeiro, qual é o domínio da sua empresa no Jira? "
                       "Por exemplo: 'minha empresa ponto atlassian ponto net'")
        
        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask("Qual é o domínio do seu Jira?")
            .response
        )

class CaptureSetupDataIntentHandler(AbstractRequestHandler):
    """Handler para capturar dados de configuração em etapas"""
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("CaptureSetupDataIntent")(handler_input)
    
    def handle(self, handler_input: HandlerInput) -> Response:
        """Processa configuração do Jira por etapas"""
        session_attr = handler_input.attributes_manager.session_attributes
        slots = handler_input.request_envelope.request.intent.slots
        
        # Capturar valor do slot 'setupData'
        setup_data = slots.get('setupData', {}).get('value', '')
        
        current_step = session_attr.get('setup_step', 'domain')
        
        if current_step == 'domain':
            # Processar domínio (converter pontos falados para . reais)
            domain = setup_data.replace(' ponto ', '.').replace(' ', '')
            if not domain.startswith('https://'):
                domain = f"https://{domain}"
            if not domain.endswith('.atlassian.net'):
                domain = f"{domain}.atlassian.net"
            
            session_attr['jira_domain'] = domain
            session_attr['setup_step'] = 'email'
            
            speak_output = f"Domínio configurado como {domain}. Agora, qual é o seu email do Jira?"
            reprompt = "Me diga seu email do Jira."
            
        elif current_step == 'email':
            session_attr['jira_email'] = setup_data
            session_attr['setup_step'] = 'token'
            
            speak_output = ("Email salvo. Agora preciso do seu token de API do Jira. "
                           "Você pode gerar um em: Configurações da conta, Segurança, Tokens de API. "
                           "Me diga o token.")
            reprompt = "Qual é o seu token de API?"
            
        elif current_step == 'token':
            session_attr['jira_token'] = setup_data
            session_attr['setup_step'] = 'user_id'
            
            speak_output = ("Token salvo. Por último, qual é o seu ID de usuário no Jira? "
                           "Geralmente é um número ou código único.")
            reprompt = "Qual é o seu ID de usuário no Jira?"
            
        elif current_step == 'user_id':
            session_attr['jira_user_id'] = setup_data
            
            # Salvar todas as configurações
            return self._save_jira_configuration(handler_input, session_attr)
        
        else:
            speak_output = "Desculpe, algo deu errado. Vamos começar a configuração novamente."
            session_attr['setup_step'] = 'domain'
            reprompt = "Qual é o domínio do seu Jira?"
        
        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(reprompt)
            .response
        )
    
    def _save_jira_configuration(self, handler_input: HandlerInput, session_attr: Dict[str, Any]) -> Response:
        """Salva a configuração completa do Jira"""
        user_id = handler_input.request_envelope.session.user.user_id
        
        success = UserDataManager.save_jira_config(
            user_id=user_id,
            jira_base_url=session_attr['jira_domain'],
            jira_email=session_attr['jira_email'],
            jira_api_token=session_attr['jira_token'],
            jira_user_id=session_attr['jira_user_id']
        )
        
        if success:
            speak_output = ("Perfeito! Sua conta do Jira foi configurada com sucesso. "
                           "Agora você pode dizer: 'criar uma task' para começar a usar.")
        else:
            speak_output = ("Houve um erro ao salvar sua configuração. "
                           "Tente configurar novamente dizendo: 'configurar Jira'.")
        
        # Limpar dados da sessão
        session_attr.clear()
        
        return (
            handler_input.response_builder
            .speak(speak_output)
            .set_card(SimpleCard("Jira Configurado", speak_output))
            .response
        )

class CreateTaskIntentHandler(AbstractRequestHandler):
    """Handler para criar nova task no Jira"""
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("CreateTaskIntent")(handler_input)
    
    def handle(self, handler_input: HandlerInput) -> Response:
        """Inicia o processo de criação de task"""
        user_id = handler_input.request_envelope.session.user.user_id
        
        # Verificar se usuário está configurado
        if not UserDataManager.is_user_configured(user_id):
            speak_output = ("Você precisa configurar sua conta do Jira primeiro. "
                           "Diga: 'configurar Jira' para começar.")
            return (
                handler_input.response_builder
                .speak(speak_output)
                .ask("Diga 'configurar Jira' para começar a configuração.")
                .response
            )
        
        session_attr = handler_input.attributes_manager.session_attributes
        session_attr['task_creation_step'] = 'title'
        
        speak_output = "Vamos criar uma nova task. Qual é o título da task?"
        
        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask("Por favor, me diga o título da task.")
            .response
        )

class CaptureTaskDataIntentHandler(AbstractRequestHandler):
    """Handler para capturar dados da task em etapas"""
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("CaptureTaskDataIntent")(handler_input)
    
    def handle(self, handler_input: HandlerInput) -> Response:
        """Processa dados da task por etapas"""
        session_attr = handler_input.attributes_manager.session_attributes
        slots = handler_input.request_envelope.request.intent.slots
        
        # Capturar valor do slot 'data'
        task_data = slots.get('data', {}).get('value', '')
        
        current_step = session_attr.get('task_creation_step', 'title')
        
        if current_step == 'title':
            session_attr['task_title'] = task_data
            session_attr['task_creation_step'] = 'description'
            speak_output = f"Título definido como '{task_data}'. Agora, qual é a descrição da task?"
            reprompt = "Me diga a descrição da task."
            
        elif current_step == 'description':
            session_attr['task_description'] = task_data
            session_attr['task_creation_step'] = 'project'
            speak_output = f"Descrição salva. Em qual projeto ou board você quer criar esta task?"
            reprompt = "Qual é o código do projeto? Por exemplo: PROJ ou DEV."
            
        elif current_step == 'project':
            session_attr['task_project'] = task_data.upper()
            
            # Tentar criar a task
            return self._create_jira_task(handler_input, session_attr)
        
        else:
            speak_output = "Desculpe, algo deu errado. Vamos começar novamente. Qual é o título da task?"
            session_attr['task_creation_step'] = 'title'
            reprompt = "Me diga o título da task."
        
        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(reprompt)
            .response
        )
    
    def _create_jira_task(self, handler_input: HandlerInput, session_attr: Dict[str, Any]) -> Response:
        """Cria a task no Jira com os dados coletados"""
        user_id = handler_input.request_envelope.session.user.user_id
        user_config = UserDataManager.get_user_config(user_id)
        
        if not user_config or not user_config.get('configured', False):
            speak_output = ("Sua configuração do Jira não foi encontrada. "
                           "Diga: 'configurar Jira' para configurar novamente.")
            return (
                handler_input.response_builder
                .speak(speak_output)
                .ask("Como você gostaria de prosseguir?")
                .response
            )
        
        # Criar cliente Jira com configuração do usuário
        jira_client = create_jira_client(user_config)
        
        # Criar task no Jira
        result = jira_client.create_issue(
            title=session_attr['task_title'],
            description=session_attr['task_description'],
            project_key=session_attr['task_project'],
            assignee_id=user_config['jira_user_id']
        )
        
        if 'error' in result:
            speak_output = f"Desculpe, houve um erro ao criar a task: {result['error']}"
        else:
            task_key = result.get('key', 'N/A')
            speak_output = (f"Perfeito! Task '{session_attr['task_title']}' "
                           f"criada com sucesso no Jira com o código {task_key}.")
        
        # Limpar dados da sessão
        session_attr.clear()
        
        return (
            handler_input.response_builder
            .speak(speak_output)
            .set_card(SimpleCard("Task Criada", speak_output))
            .response
        )

class HelpIntentHandler(AbstractRequestHandler):
    """Handler para ajuda"""
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_intent_name("AMAZON.HelpIntent")(handler_input)
    
    def handle(self, handler_input: HandlerInput) -> Response:
        user_id = handler_input.request_envelope.session.user.user_id
        
        if UserDataManager.is_user_configured(user_id):
            speak_output = ("Este skill permite criar tasks no Jira por voz. "
                           "Você pode dizer: 'criar uma task' para criar uma nova task. "
                           "Como posso ajudar?")
        else:
            speak_output = ("Este skill permite criar tasks no Jira por voz. "
                           "Primeiro, você precisa configurar sua conta dizendo: 'configurar Jira'. "
                           "Depois pode criar tasks dizendo: 'criar uma task'. Como posso ajudar?")
        
        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )

class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Handler para cancelar ou parar"""
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return (is_intent_name("AMAZON.CancelIntent")(handler_input) or
                is_intent_name("AMAZON.StopIntent")(handler_input))
    
    def handle(self, handler_input: HandlerInput) -> Response:
        speak_output = "Até logo!"
        
        return handler_input.response_builder.speak(speak_output).response

class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler para fim de sessão"""
    
    def can_handle(self, handler_input: HandlerInput) -> bool:
        return is_request_type("SessionEndedRequest")(handler_input)
    
    def handle(self, handler_input: HandlerInput) -> Response:
        return handler_input.response_builder.response

class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Handler global para exceções"""
    
    def can_handle(self, handler_input: HandlerInput, exception: Exception) -> bool:
        return True
    
    def handle(self, handler_input: HandlerInput, exception: Exception):
        logger.error(f"Erro não tratado: {exception}", exc_info=True)
        
        speak_output = "Desculpe, houve um problema. Tente novamente."
        
        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )

# Skill Builder
sb = SkillBuilder()

# Registrar handlers
sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(SetupJiraIntentHandler())
sb.add_request_handler(CaptureSetupDataIntentHandler())
sb.add_request_handler(CreateTaskIntentHandler())
sb.add_request_handler(CaptureTaskDataIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())

# Registrar exception handler
sb.add_exception_handler(CatchAllExceptionHandler())

# Função lambda handler
lambda_handler = sb.lambda_handler()
