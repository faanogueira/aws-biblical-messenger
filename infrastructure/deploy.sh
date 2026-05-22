#!/bin/bash
# deploy.sh — Empacota e faz upload da Lambda para a AWS
# Uso: ./infrastructure/deploy.sh
# Pré-requisito: AWS CLI configurado com permissões adequadas

set -e

FUNCTION_NAME="biblical-daily-message"
REGION="us-east-1"
LAMBDA_DIR="src/lambda_daily_sender"
ZIP_FILE="lambda-code.zip"

echo "======================================"
echo " Biblical Daily Message — Deploy"
echo "======================================"
echo "Função  : $FUNCTION_NAME"
echo "Região  : $REGION"
echo ""

# Verifica se o AWS CLI está configurado
if ! aws sts get-caller-identity > /dev/null 2>&1; then
  echo "ERRO: AWS CLI não configurado. Execute 'aws configure' primeiro."
  exit 1
fi

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Conta AWS: $AWS_ACCOUNT_ID"
echo ""

# Empacota os arquivos da Lambda
echo "[1/3] Empacotando arquivos..."
cd "$LAMBDA_DIR"
zip -q "$ZIP_FILE" lambda_function.py config.py
echo "      Arquivos incluídos: lambda_function.py, config.py"
cd ..

# Faz upload do código para a Lambda
echo "[2/3] Enviando código para a AWS Lambda..."
aws lambda update-function-code \
  --function-name "$FUNCTION_NAME" \
  --zip-file "fileb://${LAMBDA_DIR}/${ZIP_FILE}" \
  --region "$REGION" \
  --output table

# Aguarda a atualização terminar
echo "[3/3] Aguardando atualização..."
aws lambda wait function-updated \
  --function-name "$FUNCTION_NAME" \
  --region "$REGION"

# Limpeza
rm -f "${LAMBDA_DIR}/${ZIP_FILE}"

echo ""
echo "======================================"
echo " Deploy concluído com sucesso!"
echo "======================================"
echo ""
echo "Para testar manualmente, execute:"
echo "  aws lambda invoke --function-name $FUNCTION_NAME --payload '{}' response.json"
echo "  cat response.json"
