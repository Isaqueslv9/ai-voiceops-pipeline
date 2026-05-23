# Fluxo do Pipeline

## 1. Input
O usuário faz upload de um arquivo de áudio (MP3, WAV, OGG) para o bucket `voiceops-input` no S3.

## 2. Trigger
O evento `ObjectCreated` do S3 aciona automaticamente a função Lambda.
Um `job_id` único (UUID) é gerado para rastrear todos os arquivos dessa execução.

## 3. Transcribe
A Lambda chama o Amazon Transcribe com diarização de falantes ativada.
Polling a cada 5 segundos até o job ser concluído.
JSON bruto da transcrição salvo em `voiceops-transcripts/raw/{job_id}.json`.

## 4. Comprehend
O texto transcrito é analisado para:
- Sentimento (POSITIVE, NEGATIVE, NEUTRAL, MIXED)
- Entidades nomeadas
- Frases-chave
- Detecção de PII

Resultado salvo em `voiceops-output/results/{job_id}/analysis.json`.

## 5. Polly
A resposta é selecionada com base no sentimento detectado.
O Amazon Polly sintetiza a fala usando engine Neural, voz Camila (pt-BR).
Áudio salvo em `voiceops-output/results/{job_id}/response.mp3`.

## 6. Output
Estrutura final no S3:
```
results/{job_id}/
├── transcript.json
├── analysis.json
└── response.mp3
```