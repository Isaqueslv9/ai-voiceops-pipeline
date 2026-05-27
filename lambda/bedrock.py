import boto3
import json

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")

def generate_response(transcript_text, sentiment):
    prompt = f"""Você é um assistente de atendimento ao cliente.

O cliente enviou a seguinte mensagem:
"{transcript_text}"

O sentimento detectado foi: {sentiment}

Responda de forma empática, profissional e personalizada em português brasileiro.
Máximo 2 frases."""

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 200,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    })

    response = bedrock.invoke_model(
        modelId="us.anthropic.claude-haiku-4-5-20251001-v1:0",
        body=body,
        contentType="application/json",
        accept="application/json"
    )

    result = json.loads(response["body"].read())
    return result["content"][0]["text"]