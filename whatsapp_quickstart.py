import json
from dotenv import load_dotenv
import os
import aiohttp
import asyncio
from flask import Flask, request

# ----------------------------------------------------------------------------------
# CRITICAL FIX: Only import the function needed to process the message.
# Data loading happens automatically when 'chatbot.py' is imported.
from chatbot import get_chatbot_response 
# ----------------------------------------------------------------------------------

# --------------------------------------------------------------
# Load environment variables
# --------------------------------------------------------------

load_dotenv()
# Load the correct environment variable name from your .env
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
VERSION = os.getenv("VERSION")

# --------------------------------------------------------------
# Flask App Initialization
# --------------------------------------------------------------

app = Flask(__name__)

# --------------------------------------------------------------
# WhatsApp Message Sending Function
# --------------------------------------------------------------

async def send_message(data):
    """Sends a message back to the WhatsApp user via the Cloud API."""
    headers = {
        "Content-type": "application/json",
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}", 
    }

    async with aiohttp.ClientSession() as session:
        url = "https://graph.facebook.com" + f"/{VERSION}/{PHONE_NUMBER_ID}/messages"
        
        try:
            async with session.post(url, data=data, headers=headers) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    print(f"\n✅ Message Sent Successfully (Status: {response.status})")
                    print("Body:", response_text)
                else:
                    # CRITICAL: Print the error details if the API call fails
                    print(f"\n❌ API Error Sending Message (Status: {response.status})")
                    print("Response:", response_text)

        except aiohttp.ClientConnectorError as e:
            print(f"\n❌ Connection Error: {str(e)}")


def get_text_message_input(recipient, text):
    """Formats the JSON payload for a text message reply."""
    return json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }
    )


# --------------------------------------------------------------
# Webhook Route Handlers
# --------------------------------------------------------------

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    """Handles the Meta Verification Request."""
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("\n✅ WEBHOOK_VERIFIED")
            return challenge, 200
        else:
            print("\n❌ Verification Failed: Token mismatch")
            return "Verification token mismatch", 403
    return "Missing parameters", 400


@app.route("/webhook", methods=["POST"])
def webhook():
    """Handles incoming message notifications from WhatsApp."""
    try:
        data = request.get_json()
        
        if "object" in data and data["object"] == "whatsapp_business_account":
            for entry in data["entry"]:
                for change in entry["changes"]:
                    if change["field"] == "messages":
                        message_data = change["value"]
                        
                        # 1. Check for incoming text message
                        if message_data.get("messages") and message_data["messages"][0]["type"] == "text":
                            
                            message = message_data["messages"][0]
                            wa_id = message["from"]
                            user_message = message["text"]["body"]
                            
                            print(f"\n--- INCOMING MESSAGE ---")
                            print(f"From: {wa_id}")
                            print(f"Message: {user_message}")
                            
                            # 2. Get the Chatbot Response
                            reply_text = get_chatbot_response(user_message)
                            
                            print(f"🤖 Chatbot Reply: {reply_text[:100]}...")
                            
                            # 3. Format and Send the Reply
                            data_to_send = get_text_message_input(recipient=wa_id, text=reply_text)
                            
                            # Run the async send function
                            asyncio.run(send_message(data_to_send))

                        # Optionally, handle status updates (read, delivered)
                        elif message_data.get("statuses"):
                            status = message_data["statuses"][0]
                            print(f"\n--- STATUS UPDATE ---")
                            print(f"Message ID: {status['id']}, Status: {status['status']}")
                            
    except Exception as e:
        print(f"\n❌ Error processing webhook data: {e}")
    
    # Meta requires a 200 OK response quickly regardless of processing success
    return "OK", 200


if __name__ == "__main__":
    print("\nStarting Flask app on port 5000...")
    app.run(host="0.0.0.0", port=5000)