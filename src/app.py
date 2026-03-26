import json
import boto3
import os

TABLE_NAME = os.environ.get("TABLE_NAME")
dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(TABLE_NAME)

comprehend = boto3.client("comprehend", region_name="eu-central-1")

def handler(event, context):
    try:
        http_method = event.get("requestContext", {}).get("httpMethod")
        
        path = event.get("path", "")
        path_parts = path.strip("/").split("/")
        
        if len(path_parts) == 2 and path_parts[0] == "views":
            page_id = path_parts[1]

            if http_method == "POST":
                response = table.update_item(
                    Key={"id": page_id},
                    UpdateExpression="ADD view_count :inc",
                    ExpressionAttributeValues={":inc": 1},
                    ReturnValues="UPDATED_NEW"
                )
                count = response["Attributes"]["view_count"]
                return {
                    "statusCode": 201,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"message": "View recorded", "count": int(count)})
                }

            elif http_method == "GET":
                response = table.get_item(Key={"id": page_id})
                item = response.get("Item", {})
                count = item.get("view_count", 0)
                sentiment = item.get("sentiment", "unknown")
                return {
                    "statusCode": 200,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"page_id": page_id, "count": int(count), "sentiment": sentiment})
                }
            
        elif len(path_parts) == 3 and path_parts[0] == "views" and path_parts[2] == "analyze" and http_method == "POST":
            page_id = path_parts[1]

            body = json.loads(event.get("body", "{}"))
            text = body.get("text", "")
            
            if not text:
                return {
                    "statusCode": 400,
                    "body": json.dumps({"message": "Text is required"})
                }
            
            sentiment_response = comprehend.detect_sentiment(Text=text, LanguageCode="en")
            sentiment = sentiment_response['Sentiment']
            
            table.update_item(
                Key={"id": page_id},
                UpdateExpression="SET sentiment = :s",
                ExpressionAttributeValues={":s": sentiment}
            )
            
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"message": "Sentiment analyzed", "sentiment": sentiment, "scores": sentiment_response['SentimentScore']})
            }

        return {
            "statusCode": 405,
            "body": json.dumps({"message": "Method Not Allowed"})
        }
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Internal Server Error"})
        }