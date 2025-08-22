import os, json, base64, boto3, time
reko = boto3.client('rekognition')
ddb  = boto3.client('dynamodb')

COLLECTION_ID = os.environ['COLLECTION_ID']
TABLE_NAME    = os.environ['TABLE_NAME']

def _now_ms():
    return int(time.time()*1000)

def _resp(code, obj):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(obj)
    }

def handler(event, context):
    # Minimal defensive parsing for API Gateway HTTP API v2
    try:
        body_raw = event.get("body")
        body = json.loads(body_raw) if isinstance(body_raw, str) else (body_raw or {})
        image_b64  = body["image_base64"]      # base64 JPEG/PNG
        patient_id = body["patient_id"]        # canonical ID
        attrs      = body.get("attributes", {})

        img_bytes = base64.b64decode(image_b64)

        # Index face
        idx = reko.index_faces(
            CollectionId=COLLECTION_ID,
            Image={'Bytes': img_bytes},
            ExternalImageId=patient_id,
            DetectionAttributes=['DEFAULT'],
            MaxFaces=1,
            QualityFilter='AUTO'
        )

        if not idx.get('FaceRecords'):
            return _resp(422, {"message": "No face detected or poor quality."})

        face_id = idx['FaceRecords'][0]['Face']['FaceId']

        item = {
            'patient_id': {'S': patient_id},
            'face_id':    {'S': face_id},
            'created_at': {'N': str(_now_ms())},
            'updated_at': {'N': str(_now_ms())},
        }
        for k, v in attrs.items():
            if isinstance(v, str):
                item[k] = {'S': v}

        ddb.put_item(TableName=TABLE_NAME, Item=item)
        return _resp(201, {"patient_id": patient_id, "face_id": face_id})

    except Exception as e:
        return _resp(500, {"error": str(e)})
