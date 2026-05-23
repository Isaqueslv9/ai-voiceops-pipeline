import json
import uuid
import time
import urllib.request
import logging
import boto3
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

transcribe = boto3.client("transcribe")
comprehend = boto3.client("comprehend")
polly      = boto3.client("polly")
s3         = boto3.client("s3")

TRANSCRIPTS_BUCKET = os.getenv("TRANSCRIPTS_BUCKET")
OUTPUT_BUCKET      = os.getenv("OUTPUT_BUCKET")

# Respostas automáticas por sentimento
RESPONSES = {
    "NEGATIVE": "Detectamos um problema e iremos priorizar seu atendimento. Em breve entraremos em contato.",
    "POSITIVE": "Obrigado pelo seu feedback positivo! Ficamos felizes em ajudar.",
    "NEUTRAL":  "Recebemos sua mensagem e iremos analisá-la em breve.",
    "MIXED":    "Agradecemos seu contato. Nossa equipe irá avaliar sua solicitação."
}

def lambda_handler(event, context):
    job_id = str(uuid.uuid4())

    bucket    = event["Records"][0]["s3"]["bucket"]["name"]
    key       = event["Records"][0]["s3"]["object"]["key"]
    audio_uri = f"s3://{bucket}/{key}"

    logger.info(json.dumps({
        "job_id": job_id,
        "status": "RECEIVED",
        "bucket": bucket,
        "key":    key
    }))

    
    # Transcribe
    
    job_name = f"voiceops-{job_id}"

    transcribe.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={"MediaFileUri": audio_uri},
        MediaFormat=key.split(".")[-1],
        LanguageCode="pt-BR",
        Settings={
            "ShowSpeakerLabels": True,
            "MaxSpeakerLabels": 2
        }
    )

    logger.info(json.dumps({"job_id": job_id, "status": "TRANSCRIBE_STARTED"}))

    while True:
        response = transcribe.get_transcription_job(TranscriptionJobName=job_name)
        status   = response["TranscriptionJob"]["TranscriptionJobStatus"]

        logger.info(json.dumps({"job_id": job_id, "status": f"TRANSCRIBE_{status}"}))

        if status == "COMPLETED":
            break
        if status == "FAILED":
            raise Exception(f"Transcribe job falhou: {job_name}")

        time.sleep(5)

    transcript_uri = response["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
    with urllib.request.urlopen(transcript_uri) as r:
        transcript_data = json.loads(r.read().decode("utf-8"))

    transcript_text = transcript_data["results"]["transcripts"][0]["transcript"]

    s3.put_object(
        Bucket=TRANSCRIPTS_BUCKET,
        Key=f"raw/{job_id}.json",
        Body=json.dumps(transcript_data),
        ContentType="application/json"
    )

    logger.info(json.dumps({
        "job_id":     job_id,
        "status":     "TRANSCRIBE_SAVED",
        "transcript": transcript_text[:100]
    }))

  
    # Comprehend
    
    sentiment_response  = comprehend.detect_sentiment(Text=transcript_text, LanguageCode="pt")
    entities_response   = comprehend.detect_entities(Text=transcript_text, LanguageCode="pt")
    keyphrases_response = comprehend.detect_key_phrases(Text=transcript_text, LanguageCode="pt")
    pii_response        = comprehend.detect_pii_entities(Text=transcript_text, LanguageCode="en")

    sentiment = sentiment_response["Sentiment"]

    analysis = {
        "job_id":           job_id,
        "transcript":       transcript_text,
        "sentiment":        sentiment,
        "sentiment_scores": sentiment_response["SentimentScore"],
        "entities":         [e["Text"] for e in entities_response["Entities"]],
        "key_phrases":      [k["Text"] for k in keyphrases_response["KeyPhrases"]],
        "pii_detected":     len(pii_response["Entities"]) > 0,
        "pii_types":        [p["Type"] for p in pii_response["Entities"]]
    }

    s3.put_object(
        Bucket=OUTPUT_BUCKET,
        Key=f"results/{job_id}/analysis.json",
        Body=json.dumps(analysis, ensure_ascii=False),
        ContentType="application/json"
    )

    logger.info(json.dumps({
        "job_id":    job_id,
        "status":    "COMPREHEND_SAVED",
        "sentiment": sentiment,
        "entities":  analysis["entities"],
        "pii":       analysis["pii_detected"]
    }))

   
    # Polly: escolhe a resposta pelo sentimento e gera o MP3
   
    response_text = RESPONSES.get(sentiment, RESPONSES["NEUTRAL"])

    polly_response = polly.synthesize_speech(
        Text=response_text,
        OutputFormat="mp3",
        VoiceId="Camila",        # voz brasileira Neural do lab
        Engine="neural",
        LanguageCode="pt-BR"
    )

    # AudioStream é um objeto streaming — lê os bytes e salva no S3
    audio_bytes = polly_response["AudioStream"].read()

    s3.put_object(
        Bucket=OUTPUT_BUCKET,
        Key=f"results/{job_id}/response.mp3",
        Body=audio_bytes,
        ContentType="audio/mpeg"
    )

    # Salva também o transcript limpo
    s3.put_object(
        Bucket=OUTPUT_BUCKET,
        Key=f"results/{job_id}/transcript.json",
        Body=json.dumps({"job_id": job_id, "transcript": transcript_text}, ensure_ascii=False),
        ContentType="application/json"
    )

    logger.info(json.dumps({
        "job_id":        job_id,
        "status":        "POLLY_SAVED",
        "response_text": response_text,
        "sentiment":     sentiment
    }))

    return {
        "statusCode":    200,
        "job_id":        job_id,
        "transcript":    transcript_text,
        "sentiment":     sentiment,
        "response_text": response_text
    }