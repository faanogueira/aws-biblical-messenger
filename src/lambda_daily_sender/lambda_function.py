import json
import os
import boto3
from datetime import datetime
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr
from config import MODEL_ID, SYSTEM_PROMPT, THEMES_ROTATION

# Clientes inicializados fora do handler (reduz latência de cold start)
bedrock_runtime = boto3.client(service_name='bedrock-runtime', region_name='us-east-1')
ses_client      = boto3.client('ses', region_name='us-east-1')
dynamodb        = boto3.resource('dynamodb', region_name='us-east-1')

TABLE_NAME = os.environ.get('DYNAMODB_TABLE', 'biblical-recipients')
SES_SENDER  = os.environ.get('SES_SENDER')


def buscar_destinatarios() -> list[dict]:
    """Retorna todos os destinatários ativos da tabela DynamoDB."""
    tabela = dynamodb.Table(TABLE_NAME)
    resposta = tabela.scan(FilterExpression=Attr('ativo').eq(True))
    return resposta.get('Items', [])


def gerar_mensagem_biblica() -> str:
    """Invoca o Bedrock para gerar a mensagem bíblica do dia."""
    hoje        = datetime.now().strftime('%d/%m/%Y')
    dia_semana  = datetime.now().weekday()
    tema        = THEMES_ROTATION.get(dia_semana, 'fé')

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "messages": [{
            "role": "user",
            "content": f"Gere a mensagem bíblica para o dia {hoje}. Tema sugerido: {tema}."
        }]
    }
    response = bedrock_runtime.invoke_model(
        body=json.dumps(payload),
        modelId=MODEL_ID,
        contentType='application/json',
        accept='application/json'
    )
    body = json.loads(response['body'].read())
    return body['content'][0]['text']


def montar_html(nome: str, mensagem: str) -> str:
    """Monta o corpo HTML do e-mail personalizado."""
    hoje = datetime.now().strftime('%d/%m/%Y')
    return f"""
    <html>
    <body style="font-family:Georgia,serif;max-width:600px;margin:auto;padding:24px;color:#333;">
      <h2 style="color:#5a3e2b;border-bottom:2px solid #c8a96e;padding-bottom:8px;">
        ✝️ Mensagem Bíblica do Dia — {hoje}
      </h2>
      <p style="color:#888;font-size:13px;">
        Olá, <strong>{nome}</strong>! Que esta mensagem abençoe o seu dia.
      </p>
      <pre style="white-space:pre-wrap;font-family:Georgia,serif;font-size:15px;line-height:1.8;
                  background:#fdf8f0;border-left:4px solid #c8a96e;padding:16px;border-radius:4px;">
{mensagem}
      </pre>
      <hr style="border:none;border-top:1px solid #e0c88a;margin-top:30px;">
      <p style="font-size:11px;color:#aaa;text-align:center;">
        Enviado automaticamente · AWS Lambda + Amazon Bedrock + DynamoDB
      </p>
    </body>
    </html>
    """


def enviar_email(destinatario: dict, mensagem: str) -> str:
    """Envia e-mail personalizado para um destinatário. Retorna o SES MessageId."""
    hoje  = datetime.now().strftime('%d/%m/%Y')
    nome  = destinatario.get('nome', 'Amigo(a)')
    email = destinatario['email']

    resposta = ses_client.send_email(
        Source=SES_SENDER,
        Destination={'ToAddresses': [email]},
        Message={
            'Subject': {
                'Data': f"✝️ Mensagem Bíblica do Dia — {hoje}",
                'Charset': 'UTF-8'
            },
            'Body': {
                'Text': {'Data': mensagem, 'Charset': 'UTF-8'},
                'Html': {'Data': montar_html(nome, mensagem), 'Charset': 'UTF-8'}
            }
        }
    )
    return resposta['MessageId']


def registrar_envio(destinatario: dict, message_id: str, status: str):
    """Atualiza o registro no DynamoDB com o resultado do envio."""
    tabela = dynamodb.Table(TABLE_NAME)
    tabela.update_item(
        Key={'email': destinatario['email']},
        UpdateExpression='SET ultimo_envio = :data, ultimo_status = :status, ultimo_message_id = :mid',
        ExpressionAttributeValues={
            ':data':   datetime.now().isoformat(),
            ':status': status,
            ':mid':    message_id
        }
    )


def lambda_handler(event, context):
    """Handler principal — invocado pelo EventBridge Scheduler."""
    print("INFO: Buscando destinatários ativos no DynamoDB...")
    destinatarios = buscar_destinatarios()

    if not destinatarios:
        print("AVISO: Nenhum destinatário ativo encontrado. Encerrando.")
        return {'statusCode': 200, 'body': json.dumps({'enviados': 0})}

    print(f"INFO: {len(destinatarios)} destinatário(s) encontrado(s).")

    print("INFO: Gerando mensagem bíblica via Bedrock...")
    mensagem = gerar_mensagem_biblica()
    print(f"INFO: Mensagem gerada ({len(mensagem)} caracteres).")

    enviados, falhas = 0, 0

    for dest in destinatarios:
        try:
            message_id = enviar_email(dest, mensagem)
            registrar_envio(dest, message_id, 'ENVIADO')
            print(f"INFO: E-mail enviado → {dest['email']} | MessageId={message_id}")
            enviados += 1
        except ClientError as e:
            codigo = e.response['Error']['Code']
            print(f"ERRO [{codigo}]: Falha ao enviar para {dest['email']}")
            registrar_envio(dest, '', f"ERRO:{codigo}")
            falhas += 1

    print(f"INFO: Concluído. Enviados={enviados} | Falhas={falhas}")
    return {
        'statusCode': 200,
        'body': json.dumps({'enviados': enviados, 'falhas': falhas})
    }
