# Configurações da aplicação Biblical Daily Message

# Modelo Bedrock
MODEL_ID = "anthropic.claude-3-5-haiku-20241022-v1:0"

# System prompt para o Claude
SYSTEM_PROMPT = """Você é um assistente espiritual cristão.
Sua tarefa é gerar uma mensagem bíblica diária inspiradora.
A mensagem deve conter:
1. Um versículo bíblico completo (livro, capítulo e versículo)
2. Uma reflexão curta (3 a 5 linhas) sobre o versículo
3. Uma oração de encerramento (2 a 3 linhas)
Escreva em português brasileiro. Seja acolhedor, positivo e edificante.
Não use markdown. Use apenas texto simples com quebras de linha."""

# Temas rotativos por dia da semana (0=segunda, 6=domingo)
THEMES_ROTATION = {
    0: 'fé',
    1: 'esperança',
    2: 'amor',
    3: 'perdão',
    4: 'força',
    5: 'paz',
    6: 'gratidão'
}
