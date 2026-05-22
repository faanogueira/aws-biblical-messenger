import json
import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Adiciona o diretório lambda ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src/lambda_daily_sender'))


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def destinatarios_mock():
    return [
        {'email': 'dest1@email.com', 'nome': 'Fábio', 'ativo': True},
        {'email': 'dest2@email.com', 'nome': 'Maria', 'ativo': True},
    ]

@pytest.fixture
def mensagem_mock():
    return (
        "João 3:16 — Porque Deus amou o mundo de tal maneira...\n\n"
        "Reflexão: O amor de Deus é incondicional e eterno.\n\n"
        "Oração: Senhor, obrigado pelo Teu amor. Amém."
    )


# ── Testes unitários ───────────────────────────────────────────────────────

class TestBuscarDestinatarios:

    @patch('lambda_function.dynamodb')
    def test_retorna_apenas_ativos(self, mock_dynamo, destinatarios_mock):
        mock_table = MagicMock()
        mock_dynamo.Table.return_value = mock_table
        mock_table.scan.return_value = {'Items': destinatarios_mock}

        from lambda_function import buscar_destinatarios
        resultado = buscar_destinatarios()

        assert len(resultado) == 2
        assert resultado[0]['email'] == 'dest1@email.com'

    @patch('lambda_function.dynamodb')
    def test_retorna_lista_vazia_quando_nao_ha_ativos(self, mock_dynamo):
        mock_table = MagicMock()
        mock_dynamo.Table.return_value = mock_table
        mock_table.scan.return_value = {'Items': []}

        from lambda_function import buscar_destinatarios
        resultado = buscar_destinatarios()

        assert resultado == []


class TestGerarMensagemBiblica:

    @patch('lambda_function.bedrock_runtime')
    def test_retorna_texto_gerado(self, mock_bedrock, mensagem_mock):
        mock_bedrock.invoke_model.return_value = {
            'body': MagicMock(read=lambda: json.dumps({
                'content': [{'text': mensagem_mock}]
            }).encode())
        }

        from lambda_function import gerar_mensagem_biblica
        resultado = gerar_mensagem_biblica()

        assert isinstance(resultado, str)
        assert len(resultado) > 0
        assert 'João 3:16' in resultado

    @patch('lambda_function.bedrock_runtime')
    def test_chama_bedrock_com_parametros_corretos(self, mock_bedrock, mensagem_mock):
        mock_bedrock.invoke_model.return_value = {
            'body': MagicMock(read=lambda: json.dumps({
                'content': [{'text': mensagem_mock}]
            }).encode())
        }

        from lambda_function import gerar_mensagem_biblica
        gerar_mensagem_biblica()

        mock_bedrock.invoke_model.assert_called_once()
        call_kwargs = mock_bedrock.invoke_model.call_args[1]
        assert call_kwargs['contentType'] == 'application/json'
        assert call_kwargs['accept'] == 'application/json'


class TestEnviarEmail:

    @patch('lambda_function.ses_client')
    def test_envio_bem_sucedido(self, mock_ses, mensagem_mock):
        mock_ses.send_email.return_value = {'MessageId': 'abc-123'}

        from lambda_function import enviar_email
        dest = {'email': 'dest@email.com', 'nome': 'Fábio'}
        message_id = enviar_email(dest, mensagem_mock)

        assert message_id == 'abc-123'
        mock_ses.send_email.assert_called_once()

    @patch('lambda_function.ses_client')
    def test_email_sem_nome_usa_default(self, mock_ses, mensagem_mock):
        mock_ses.send_email.return_value = {'MessageId': 'abc-456'}

        from lambda_function import enviar_email
        dest = {'email': 'dest@email.com'}  # sem 'nome'
        message_id = enviar_email(dest, mensagem_mock)

        assert message_id == 'abc-456'
        call_args = mock_ses.send_email.call_args[1]
        assert 'Amigo(a)' in call_args['Message']['Body']['Html']['Data']


class TestLambdaHandler:

    @patch('lambda_function.registrar_envio')
    @patch('lambda_function.enviar_email')
    @patch('lambda_function.gerar_mensagem_biblica')
    @patch('lambda_function.buscar_destinatarios')
    def test_fluxo_completo_com_sucesso(
        self, mock_buscar, mock_gerar, mock_enviar, mock_registrar,
        destinatarios_mock, mensagem_mock
    ):
        mock_buscar.return_value = destinatarios_mock
        mock_gerar.return_value = mensagem_mock
        mock_enviar.return_value = 'msg-id-001'

        from lambda_function import lambda_handler
        resultado = lambda_handler({}, None)

        assert resultado['statusCode'] == 200
        body = json.loads(resultado['body'])
        assert body['enviados'] == 2
        assert body['falhas'] == 0

    @patch('lambda_function.buscar_destinatarios')
    def test_sem_destinatarios_encerra_sem_erro(self, mock_buscar):
        mock_buscar.return_value = []

        from lambda_function import lambda_handler
        resultado = lambda_handler({}, None)

        assert resultado['statusCode'] == 200
        body = json.loads(resultado['body'])
        assert body['enviados'] == 0

    @patch('lambda_function.registrar_envio')
    @patch('lambda_function.enviar_email')
    @patch('lambda_function.gerar_mensagem_biblica')
    @patch('lambda_function.buscar_destinatarios')
    def test_falha_em_um_nao_interrompe_os_demais(
        self, mock_buscar, mock_gerar, mock_enviar, mock_registrar,
        destinatarios_mock, mensagem_mock
    ):
        from botocore.exceptions import ClientError

        mock_buscar.return_value = destinatarios_mock
        mock_gerar.return_value = mensagem_mock

        # Primeiro destinatário falha, segundo vai bem
        mock_enviar.side_effect = [
            ClientError({'Error': {'Code': 'MessageRejected', 'Message': 'err'}}, 'SendEmail'),
            'msg-id-002'
        ]

        from lambda_function import lambda_handler
        resultado = lambda_handler({}, None)

        body = json.loads(resultado['body'])
        assert body['enviados'] == 1
        assert body['falhas'] == 1


# ── Testes do config ───────────────────────────────────────────────────────

class TestConfig:

    def test_model_id_definido(self):
        from config import MODEL_ID
        assert MODEL_ID.startswith('anthropic.claude')

    def test_system_prompt_em_portugues(self):
        from config import SYSTEM_PROMPT
        assert 'português' in SYSTEM_PROMPT.lower() or 'português' in SYSTEM_PROMPT

    def test_themes_rotation_tem_7_dias(self):
        from config import THEMES_ROTATION
        assert len(THEMES_ROTATION) == 7
        assert all(k in THEMES_ROTATION for k in range(7))


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
