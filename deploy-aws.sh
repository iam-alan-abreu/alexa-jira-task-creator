#!/bin/bash

# Script para deploy da infraestrutura AWS necessária
set -e

echo "🚀 Configurando infraestrutura AWS para Alexa Jira Skill..."

# Verificar se AWS CLI está configurado
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS CLI não está configurado. Execute: aws configure"
    exit 1
fi

# Criar tabela DynamoDB
echo "📊 Criando tabela DynamoDB..."
aws dynamodb create-table \
    --table-name JiraSkillUsers \
    --attribute-definitions \
        AttributeName=user_id,AttributeType=S \
    --key-schema \
        AttributeName=user_id,KeyType=HASH \
    --provisioned-throughput \
        ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --region us-east-1 || echo "Tabela já existe"

echo "✅ Tabela DynamoDB configurada"

# Criar política IAM
echo "🔐 Criando política IAM..."
cat > /tmp/jira-skill-policy.json << 'POLICY_EOF'
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
POLICY_EOF

aws iam create-policy \
    --policy-name AlexaJiraSkillPolicy \
    --policy-document file:///tmp/jira-skill-policy.json || echo "Política já existe"

echo "✅ Política IAM criada"

echo "🎉 Infraestrutura AWS configurada com sucesso!"
echo ""
echo "Próximos passos:"
echo "1. Suba este código para um repositório GitHub"
echo "2. Importe o skill no Alexa Developer Console"
echo "3. Configure as permissões IAM da Lambda function"
echo "4. Teste o skill no simulador"
