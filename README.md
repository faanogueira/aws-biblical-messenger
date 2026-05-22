# ✝️ Mensageiro Bíblico Generativo

<p align="center">
  <img src="docs/img/aws_biblical_messenger.png" alt="AWS Biblical Messenger" width="500px">
</p>

Automação serverless que gera e envia mensagens bíblicas diárias por e-mail, utilizando IA Generativa na AWS.

![AWS](https://img.shields.io/badge/AWS-Serverless-orange?logo=amazonaws)
![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)
![Bedrock](https://img.shields.io/badge/Amazon-Bedrock-purple)
![License](https://img.shields.io/badge/License-MIT-green)

---

## Arquitetura

```
EventBridge Scheduler
        │
        ▼ (cron diário)
   AWS Lambda
   ┌────────────┐
   │ 1. Busca   │──► DynamoDB (destinatários ativos)
   │ 2. Gera    │──► Amazon Bedrock (Claude 3.5 Haiku)
   │ 3. Envia   │──► Amazon SES (e-mail personalizado)
   │ 4. Registra│──► DynamoDB (histórico de envio)
   └────────────┘
        │
        ▼
  CloudWatch Logs
```

## Serviços AWS

| Serviço                         | Função                              | Custo              |
| ------------------------------- | ----------------------------------- | ------------------ |
| EventBridge Scheduler           | Disparo diário automático           | Free Tier          |
| AWS Lambda (Python 3.12)        | Lógica central da aplicação         | < $0.01/mês        |
| Amazon DynamoDB                 | Destinatários + histórico de envios | Free Tier          |
| Amazon Bedrock (Claude 3.5 Haiku) | Geração da mensagem bíblica         | ~$0.01–$0.05/mês   |
| Amazon SES                      | Envio de e-mail personalizado       | Free Tier (1k/mês) |
| CloudWatch Logs                 | Monitoramento e logs                | Free Tier          |

## Estrutura do Repositório

```
aws-biblical-messenger/
├── docs/                             ← Documentos de referência e apresentações
│   ├── apresentacao.pptx
│   ├── documentacao_v2.docx
│   ├── manual_daily_message.docx
│   └── img/                          ← Diagramas e capturas do projeto
├── infrastructure/                   ← Infraestrutura como Código (IaC) e Scripts
│   ├── cloudformation.yaml           ← Template CloudFormation principal
│   ├── deploy.sh                     ← Script bash de empacotamento e deploy
│   ├── dynamodb-schema.json          ← Referência do Schema do DynamoDB
│   ├── eventbridge-schedule.json     ← Referência do Agendamento Cron
│   └── iam-policy.json               ← Referência da Política IAM (menor privilégio)
├── src/                              ← Código-fonte da aplicação (Lambdas)
│   ├── lambda_daily_sender/          ← Lambda do envio diário de e-mails
│   │   ├── lambda_function.py        ← Handler principal
│   │   ├── config.py                 ← Rotação de temas e prompt
│   │   └── requirements.txt          
│   └── lambda_api_generator/         ← Lambda do gerador on-demand via API
│       ├── generate_message.py       ← Handler principal HTTP
│       ├── client.py                 ← Script exemplo de cliente HTTP
│       └── requirements.txt          
├── tests/                            ← Testes automatizados
│   ├── requirements-test.txt         
│   ├── test_daily_sender.py          ← Testes unitários da Lambda de e-mails
│   └── test_api_generator.py         ← Testes unitários da Lambda da API
├── .env.example                      ← Exemplo de variáveis de ambiente
├── .gitignore                        ← Regras de arquivos ignorados no Git
└── README.md
```

## Variáveis de Ambiente (Lambda)

| Variável         | Exemplo                                  | Descrição                          |
| ---------------- | ---------------------------------------- | ---------------------------------- |
| `MODEL_ID`       | `anthropic.claude-3-5-haiku-20241022-v1:0` | Modelo Bedrock                     |
| `SES_SENDER`     | `voce@email.com`                         | E-mail remetente verificado no SES |
| `DYNAMODB_TABLE` | `biblical-recipients`                    | Nome da tabela DynamoDB            |

## Modelo da Tabela DynamoDB

**Tabela:** `biblical-recipients` | **Chave primária:** `email` (String)

| Atributo            | Tipo        | Obrigatório | Descrição                          |
| ------------------- | ----------- | ----------- | ---------------------------------- |
| `email`             | String (PK) | Sim         | Identificador único                |
| `nome`              | String      | Sim         | Personalização do e-mail           |
| `ativo`             | Boolean     | Sim         | `true` = recebe, `false` = pausado |
| `data_cadastro`     | String      | Sim         | ISO 8601                           |
| `ultimo_envio`      | String      | Não         | Preenchido pela Lambda             |
| `ultimo_status`     | String      | Não         | `ENVIADO` ou `ERRO:código`         |
| `ultimo_message_id` | String      | Não         | ID do SES para rastreio            |

## Deploy

```bash
# 1. Configure o AWS CLI
aws configure

# 2. Crie a função Lambda no console AWS (primeira vez)
# Veja o passo a passo completo na documentação técnica

# 3. Para atualizações de código — use o script
chmod +x infrastructure/deploy.sh
./infrastructure/deploy.sh
```

## Testes

```bash
cd tests
pip install -r requirements-test.txt
pytest test_daily_sender.py -v
pytest test_api_generator.py -v
```

## Autor

**Fábio Nogueira**

- GitHub: [github.com/faanogueira](https://github.com/faanogueira)
- LinkedIn: [linkedin.com/in/faanogueira](https://linkedin.com/in/faanogueira)
- E-mail: faanogueira@gmail.com

---

_Projeto desenvolvido como parte do portfólio de Data Science & IA Generativa — IPOG 2026_
