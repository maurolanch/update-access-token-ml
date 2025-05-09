import os
import json
import requests
from flask import Flask, request
from google.cloud import secretmanager
import logging

app = Flask(__name__)

required_env_vars = ["PROJECT_ID", "CLIENT_ID", "CLIENT_SECRET", "REFRESH_TOKEN", "ACCESS_TOKEN"]
for var in required_env_vars:
    if var not in os.environ:
        raise EnvironmentError(f"Missing required environment variable: {var}")

PROJECT_ID =  os.environ["PROJECT_ID"]
CLIENT_ID_SECRET = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]
ACCESS_TOKEN_SECRET = os.environ["ACCESS_TOKEN"]

def get_secret(secret_id):
    try:
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        logging.error(f"Error al acceder al secreto '{secret_id}': {e}")
        raise

@app.route('/', methods=['POST'])
def refresh_token():
    client_id = get_secret(CLIENT_ID_SECRET)   
    client_secret = get_secret(CLIENT_SECRET)
    refresh_token = get_secret(REFRESH_TOKEN)
    
    token_url = "https://api.mercadolibre.com/oauth/token"
    payload = {
        'grant_type': 'refresh_token',
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token
    }
    try:
        response = requests.post(token_url, data=payload)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        return f"Error al renovar token: {err}", 500
    
    token_data = response.json()
    new_access_token = token_data.get('access_token')
    if not new_access_token:
        return "Error: No se pudo obtener el access token", 500
    
    client = secretmanager.SecretManagerServiceClient()
    parent = f"projects/{PROJECT_ID}/secrets/{ACCESS_TOKEN_SECRET}"
    response = client.add_secret_version(
        request={
            "parent": parent,
            "payload": {
                "data": new_access_token.encode("UTF-8")
            }
        }
    )
    logging.info("Token de acceso renovado y guardado exitosamente")
    return "Access token actualizado correctamente", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)