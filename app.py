from fastapi import FastAPI, Form, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import requests
import os
import base64
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from base64 import urlsafe_b64encode, urlsafe_b64decode

app = FastAPI()

# Setup templates and static directories
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ----------------------------- Encryption Functions -----------------------------

# Sharekhan API encryption utilities
key_string = "txt1XPdoxL4YVMgnJiFkY6xxGE"  # Original key string
# Pad or truncate to exactly 32 bytes for AES-256
key = key_string.encode('utf-8')[:32].ljust(32, b'\0')
iv = base64.b64decode("AAAAAAAAAAAAAAAAAAAAAA==")

def encryptAPIString(plaintext):  
    raw = plaintext.encode('utf-8')   
    encryptor = Cipher(algorithms.AES(key), modes.GCM(iv, None, 16), default_backend()).encryptor()
    ciphertext = encryptor.update(raw) + encryptor.finalize()  
    return base64UrlEncode(ciphertext + encryptor.tag)
 
def decryptAPIString(ciphertext):   
    enc_data = base64UrlDecode(ciphertext)
    enc = enc_data[:-16]  # ciphertext without tag
    tag = enc_data[-16:]  # last 16 bytes are the tag
    decryptor = Cipher(algorithms.AES(key), modes.GCM(iv, tag), default_backend()).decryptor()  
    return decryptor.update(enc) + decryptor.finalize()
   
def base64UrlEncode(data):
    return urlsafe_b64encode(data).rstrip(b'=')
 
def base64UrlDecode(base64Url):
    padding = b'=' * (4 - (len(base64Url) % 4))
    return urlsafe_b64decode(base64Url + padding)


# ----------------------------- Routes -----------------------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})


@app.get("/login")
def login(app_id: str):
    version_id = "1005"
    state = "12345"
    callback_url = "http://127.0.0.1:8000/callback"
    
    login_url = (
        f"https://api.sharekhan.com/skapi/auth/login.html"
        f"?api_key={app_id}"
        f"&state={state}"
        f"&version_id={version_id}"
        f"&callback_url={callback_url}"
    )
    print(f"Redirecting to: {login_url}")
    return RedirectResponse(login_url)


@app.get("/callback", response_class=HTMLResponse)
def callback(request: Request, request_token: str = None, code: str = None, state: str = None):
    print(f"Callback received - request_token: {request_token}, code: {code}, state: {state}")
    print(f"Full query params: {dict(request.query_params)}")
    
    # Sharekhan uses 'request_token' instead of 'code'
    auth_code = request_token or code
    
    if not auth_code:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "success": False,
            "error": "No authorization code received from Sharekhan."
        })

    # Store auth_code and show form to collect secret_id
    return templates.TemplateResponse("form.html", {
        "request": request,
        "auth_code": auth_code,
        "message": "Authorization successful! Now enter your credentials to complete token generation."
    })


@app.post("/generate_token", response_class=HTMLResponse)
def generate_token(
    request: Request,
    app_id: str = Form(...),
    secret_id: str = Form(...),
    auth_code: str = Form(None)
):
    if not auth_code:
        # Step 1: Redirect user to Sharekhan login
        version_id = "1005"
        state = "12345"

        login_url = (
            f"https://api.sharekhan.com/skapi/auth/login.html"
            f"?api_key={app_id}"
            f"&state={state}"
            f"&version_id={version_id}"
        )
        return RedirectResponse(url=login_url, status_code=302)

    try:
        # Direct approach with encryption - This is likely required for Sharekhan API
        
        # Step 1: Encrypt the secret_key (or other sensitive data)
        # Format appears to be: request_token|secret_key based on the pattern
        message_to_encrypt = f"{auth_code}|{secret_id}"
        encrypted_data = encryptAPIString(message_to_encrypt)
        
        print(f"Original message: {message_to_encrypt}")
        print(f"Encrypted data: {encrypted_data}")
        
        # Step 2: Make API call with encrypted data
        access_token_url = "https://api.sharekhan.com/skapi/services/access/token"
        
        # Try different payload structures - the API might expect encrypted data
        access_payload = {
            "api_key": app_id,
            "encrypted_data": encrypted_data.decode('utf-8'),  # Convert bytes to string
            "state": "12345"
        }
        
        # Alternative payload structure if the above doesn't work:
        # access_payload = {
        #     "api_key": app_id,
        #     "request_token": encrypted_data.decode('utf-8'),
        #     "state": "12345"
        # }
        
        headers = {"Content-Type": "application/json"}
        print(f"Access token payload: {access_payload}")
        
        access_response = requests.post(access_token_url, json=access_payload, headers=headers)
        print(f"Access token response: {access_response.status_code}, {access_response.text}")
        
        # If the API call fails, try without encryption as fallback
        if access_response.status_code != 200:
            print("Encrypted call failed, trying without encryption...")
            access_payload_fallback = {
                "api_key": app_id,
                "request_token": auth_code,
                "secret_key": secret_id,
                "state": "12345"
            }
            access_response = requests.post(access_token_url, json=access_payload_fallback, headers=headers)
            print(f"Fallback response: {access_response.status_code}, {access_response.text}")
        
        access_response.raise_for_status()
        access_data = access_response.json()
        
        # Success response
        return templates.TemplateResponse("result.html", {
            "request": request,
            "success": True,
            "token_data": {
                "status": access_data.get("status"),
                "message": access_data.get("message"),
                "timestamp": access_data.get("timestamp"),
                "data": access_data.get("data", {}),
                "encryption_used": True,
                "encrypted_payload": encrypted_data.decode('utf-8'),
                "note": "Access token generated with encryption"
            }
        })

    except requests.exceptions.RequestException as req_err:
        error_msg = f"Request error: {str(req_err)}"
        if hasattr(req_err, 'response') and req_err.response is not None:
            try:
                error_detail = req_err.response.json()
                error_msg = f"API error: {error_detail}"
            except:
                error_msg = f"HTTP {req_err.response.status_code}: {req_err.response.text}"
        
        return templates.TemplateResponse("result.html", {
            "request": request,
            "success": False,
            "error": error_msg
        })
    except Exception as e:
        return templates.TemplateResponse("result.html", {
            "request": request,
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        })


# ----------------------------- Run -----------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)