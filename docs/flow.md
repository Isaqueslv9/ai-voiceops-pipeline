# Fluxo do Pipeline

## 1. Input
O usuário faz upload de um arquivo de áudio (MP3, WAV ou OGG) para o bucket `voiceops-input` no Amazon S3.

---

## 2. Trigger
O evento `ObjectCreated` do S3 aciona automaticamente a função AWS Lambda responsável pela orquestração do pipeline.

Um `job_id` único (UUID) é gerado para rastrear todos os arquivos relacionados à execução.

---

## 3. Amazon Transcribe
A Lambda inicia um job no Amazon Transcribe utilizando boto3.

Recursos utilizados:
- Diarização de falantes
- Processamento assíncrono
- Polling a cada 5 segundos até conclusão

O resultado bruto da transcrição é salvo em:
voiceops-transcripts/raw/{job_id}.json

## 4. Amazon Comprehend

O texto transcrito é analisado utilizando Amazon Comprehend.

Análises realizadas:

Sentimento (POSITIVE, NEGATIVE, NEUTRAL, MIXED)
Entidades nomeadas
Frases-chave
Detecção de PII

Resultado salvo em:
voiceops-output/results/{job_id}/analysis.json

## 5. Amazon Bedrock

A Lambda envia:

texto transcrito
sentimento detectado
contexto da conversa

para o Amazon Bedrock utilizando o modelo Claude 3 Haiku.

O modelo gera uma resposta personalizada baseada no conteúdo real do cliente e na análise de sentimento.

Resposta gerada:
generated_response.txt

## 6. Amazon Polly

A resposta gerada pelo Bedrock é convertida em voz utilizando Amazon Polly.

Configuração utilizada:

Engine Neural
Voz Camila (pt-BR)
Saída em MP3

Arquivo salvo em:
voiceops-output/results/{job_id}/response.mp3

## 7. Output

Estrutura final armazenada no S3:

results/{job_id}/
├── transcript.json
├── analysis.json
└── response.mp3

## 8. Observabilidade

Logs, erros e métricas da execução são centralizados no Amazon CloudWatch Logs.

## 9. CI/CD

O deploy da AWS Lambda é automatizado utilizando GitHub Actions.

Fluxo:

Push na branch main
Workflow iniciado automaticamente
Empacotamento do código
Atualização da Lambda via AWS CLI