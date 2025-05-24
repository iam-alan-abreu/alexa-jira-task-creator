# Alexa Jira Task Creator Skill

Skill da Alexa para criar tasks no Jira Cloud usando comandos de voz.

## ✨ Funcionalidades

- ✅ Configuração individual por usuário via voz
- ✅ Criar tasks no Jira por voz
- ✅ Captura de título, descrição e projeto
- ✅ Integração com Jira Cloud API
- ✅ Persistência segura no DynamoDB
- ✅ Suporte a múltiplos usuários e empresas

## 🚀 Como Usar

### Primeira configuração
1. **Abrir skill**: "Alexa, Jira"
2. **Configurar**: "configurar Jira"
3. **Fornecer dados**:
   - Domínio: "minha-empresa ponto atlassian ponto net"
   - Email do Jira
   - Token de API
   - ID do usuário

### Criar tasks
1. **Iniciar**: "Alexa, pedir para Jira criar uma task"
2. **Seguir instruções**: Alexa pedirá título, descrição e projeto

### Exemplo de Configuração
```
👤 "Alexa, Jira"
🤖 "Primeiro, vamos configurar sua conta. Diga: configurar Jira"

👤 "configurar Jira"  
🤖 "Qual é o domínio da sua empresa? Ex: empresa ponto atlassian ponto net"

👤 "minha empresa ponto atlassian ponto net"
🤖 "Agora, qual é o seu email do Jira?"

👤 "joao@empresa.com"
🤖 "Agora o token de API do Jira"

👤 "[token-api-aqui]"
🤖 "Por último, seu ID de usuário no Jira"

👤 "123456"
🤖 "Perfeito! Conta configurada. Agora pode dizer: criar uma task"
```

## 📦 Deploy

### 1. Preparar Repositório GitHub
```bash
git init
git add .
git commit -m "Initial Alexa Jira Skill"
git branch -M main
git remote add origin https://github.com/seu-usuario/alexa-jira-skill.git
git push -u origin main
```

### 2. Configurar no Alexa Developer Console
1. Ir para [developer.amazon.com](https://developer.amazon.com/alexa/console/ask)
2. Create Skill → Import Skill
3. Colar URL do seu repositório GitHub
4. Aguardar importação

### 3. Configurar AWS DynamoDB
```bash
aws dynamodb create-table \
    --table-name JiraSkillUsers \
    --attribute-definitions \
        AttributeName=user_id,AttributeType=S \
    --key-schema \
        AttributeName=user_id,KeyType=HASH \
    --provisioned-throughput \
        ReadCapacityUnits=5,WriteCapacityUnits=5
```

## 🔧 Configuração DynamoDB

A tabela `JiraSkillUsers` armazenará:
```json
{
  "user_id": "amzn1.ask.account.xxx",
  "jira_base_url": "https://empresa.atlassian.net",
  "jira_email": "user@empresa.com", 
  "jira_api_token": "ATATT3xFfGF0...",
  "jira_user_id": "123456",
  "configured": true,
  "created_at": "2025-01-01T00:00:00Z"
}
```

## 🔐 Configurações Adicionais

### Permissões IAM Necessárias
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/JiraSkillUsers"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        }
    ]
}
```

## 📁 Estrutura de Arquivos

```
JiraTaskCreator/
├── lambda/
│   ├── lambda_function.py      # Código principal
│   └── requirements.txt        # Dependências Python
└── skill-package/
    ├── skill.json             # Configuração do skill
    ├── interactionModels/
    │   └── custom/
    │       └── en-US.json     # Modelo de interação
    └── assets/
        └── images/            # Ícones do skill (adicionar manualmente)
```

## ⚠️ Próximos Passos

1. **Adicionar ícones**: Coloque imagens PNG em `skill-package/assets/images/`
   - `en-US_smallIcon.png` (108x108 pixels)
   - `en-US_largeIcon.png` (512x512 pixels)

2. **Configurar URLs**: Atualize `skill.json` com suas URLs de privacidade

3. **Testar no simulador**: Use o Alexa Developer Console para testar

4. **Deploy produção**: Publicar na Alexa Skills Store

## 🔗 Links Úteis

- [Alexa Developer Console](https://developer.amazon.com/alexa/console/ask)
- [Jira API Documentation](https://developer.atlassian.com/cloud/jira/platform/rest/v3/)
- [AWS DynamoDB Console](https://console.aws.amazon.com/dynamodb/)

---

**Desenvolvido com ❤️ para facilitar o gerenciamento de tasks via voz**
