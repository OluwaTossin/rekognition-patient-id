import os, json, base64, boto3
reko = boto3.client('rekognition')
ddb  = boto3.client('dynamodb')

COLLECTION_ID = os.environ['COLLECTION_ID']
TABLE_NAME    = os.environ['TABLE_NAME']
THRESHOLD     = float(os.environ.get('MATCH_THRESHOLD','95'))

def _resp(code, obj):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(obj)
    }

def handler(event, context):
    try:
        body_raw = event.get("body")
        body = json.loads(body_raw) if isinstance(body_raw, str) else (body_raw or {})
        image_b64 = body["image_base64"]
        img_bytes = base64.b64decode(image_b64)

        # Search for best face match
        res = reko.search_faces_by_image(
            CollectionId=COLLECTION_ID,
            Image={'Bytes': img_bytes},
            FaceMatchThreshold=THRESHOLD,
            MaxFaces=1
        )

        if not res.get('FaceMatches'):
            return _resp(404, {"message": "No confident match"})

        match = res['FaceMatches'][0]
        face_id = match['Face']['FaceId']
        similarity = match['Similarity']

        q = ddb.query(
            TableName=TABLE_NAME,
            IndexName='face_id-index',
            KeyConditionExpression='face_id = :f',
            ExpressionAttributeValues={':f': {'S': face_id}},
            Limit=1
        )
        if not q.get('Items'):
            return _resp(404, {"message": "Face mapped but no patient record"})

        item = q['Items'][0]
        result = {k: list(v.values())[0] for k,v in item.items()}
        result['similarity'] = similarity

        return _resp(200, result)

    except Exception as e:
        return _resp(500, {"error": str(e)})
