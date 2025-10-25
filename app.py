from flask import Flask, request, jsonify, render_template, Response, stream_with_context
import asyncio
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from google.protobuf.json_format import MessageToJson
import binascii
import aiohttp
import requests
import json
import os
from proto import like_pb2
from proto import like_count_pb2
from proto import uid_generator_pb2
from google.protobuf.message import DecodeError
from token_manager import token_manager

app = Flask(__name__)

AES_KEY_STR = os.getenv('AES_ENCRYPTION_KEY')
AES_IV_STR = os.getenv('AES_ENCRYPTION_IV')

if not AES_KEY_STR or not AES_IV_STR:
    app.logger.warning("⚠️  Using default encryption keys! Set AES_ENCRYPTION_KEY and AES_ENCRYPTION_IV as Replit Secrets for better security")
    AES_KEY_STR = 'Yg&tc%DEuh6%Zc^8'
    AES_IV_STR = '6oyZDr22E3ychjM%'

AES_KEY = AES_KEY_STR.encode('utf-8')
AES_IV = AES_IV_STR.encode('utf-8')

token_manager.start_background_service()

def load_tokens(server_name):
    try:
        # Only IND server is supported
        if server_name == "IND":
            with open("token_ind.json", "r") as f:
                tokens = json.load(f)
            return tokens
        else:
            app.logger.error(f"Only IND server is supported. Requested: {server_name}")
            return None
    except Exception as e:
        app.logger.error(f"Error loading tokens for server {server_name}: {e}")
        return None

def encrypt_message(plaintext):
    try:
        cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
        padded_message = pad(plaintext, AES.block_size)
        encrypted_message = cipher.encrypt(padded_message)
        return binascii.hexlify(encrypted_message).decode('utf-8')
    except Exception as e:
        app.logger.error(f"Error encrypting message: {e}")
        return None

def create_protobuf_message(user_id, region):
    try:
        message = like_pb2.like()
        message.uid = int(user_id)
        message.region = region
        return message.SerializeToString()
    except Exception as e:
        app.logger.error(f"Error creating protobuf message: {e}")
        return None

async def send_request(encrypted_uid, token, url):
    try:
        edata = bytes.fromhex(encrypted_uid)
        headers = {
            'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'Expect': "100-continue",
            'X-Unity-Version': "2018.4.11f1",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB50"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=edata, headers=headers) as response:
                if response.status != 200:
                    app.logger.error(f"Request failed with status code: {response.status}")
                    return response.status
                return await response.text()
    except Exception as e:
        app.logger.error(f"Exception in send_request: {e}")
        return None

async def send_multiple_requests(uid, server_name, url):
    try:
        region = server_name
        protobuf_message = create_protobuf_message(uid, region)
        if protobuf_message is None:
            app.logger.error("Failed to create protobuf message.")
            return None
        encrypted_uid = encrypt_message(protobuf_message)
        if encrypted_uid is None:
            app.logger.error("Encryption failed.")
            return None
        tasks = []
        tokens = load_tokens(server_name)
        if tokens is None:
            app.logger.error("Failed to load tokens.")
            return None
        for i in range(1000):
            token = tokens[i % len(tokens)]["token"]
            tasks.append(send_request(encrypted_uid, token, url))
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    except Exception as e:
        app.logger.error(f"Exception in send_multiple_requests: {e}")
        return None

def create_protobuf(uid):
    try:
        message = uid_generator_pb2.uid_generator()
        message.saturn_ = int(uid)
        message.garena = 1
        return message.SerializeToString()
    except Exception as e:
        app.logger.error(f"Error creating uid protobuf: {e}")
        return None

def enc(uid):
    protobuf_data = create_protobuf(uid)
    if protobuf_data is None:
        return None
    encrypted_uid = encrypt_message(protobuf_data)
    return encrypted_uid

def make_request(encrypt, server_name, token):
    try:
        if server_name == "IND":
            url = "https://client.ind.freefiremobile.com/GetPlayerPersonalShow"
        elif server_name in {"BR", "US", "SAC", "NA"}:
            url = "https://client.us.freefiremobile.com/GetPlayerPersonalShow"
        else:
            url = "https://clientbp.ggblueshark.com/GetPlayerPersonalShow"
        edata = bytes.fromhex(encrypt)
        headers = {
            'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'Expect': "100-continue",
            'X-Unity-Version': "2018.4.11f1",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB50"
        }
        response = requests.post(url, data=edata, headers=headers, verify=False)
        hex_data = response.content.hex()
        binary = bytes.fromhex(hex_data)
        decode = decode_protobuf(binary)
        if decode is None:
            app.logger.error("Protobuf decoding returned None.")
        return decode
    except Exception as e:
        app.logger.error(f"Error in make_request: {e}")
        return None

def decode_protobuf(binary):
    try:
        items = like_count_pb2.Info()
        items.ParseFromString(binary)
        return items
    except DecodeError as e:
        app.logger.error(f"Error decoding Protobuf data: {e}")
        return None
    except Exception as e:
        app.logger.error(f"Unexpected error during protobuf decoding: {e}")
        return None

@app.route('/like', methods=['GET'])
def handle_requests():
    uid = request.args.get("uid")
    server_name = request.args.get("server_name", "").upper()
    if not uid or not server_name:
        return jsonify({"error": "UID and server_name are required"}), 400
    
    if server_name != "IND":
        return jsonify({"error": "Only IND server is supported"}), 400

    try:
        def process_request():
            tokens = load_tokens(server_name)
            if tokens is None:
                raise Exception("Failed to load tokens.")
            token = tokens[0]['token']
            encrypted_uid = enc(uid)
            if encrypted_uid is None:
                raise Exception("Encryption of UID failed.")

            before = make_request(encrypted_uid, server_name, token)
            if before is None:
                raise Exception("Failed to retrieve initial player info.")
            try:
                jsone = MessageToJson(before)
            except Exception as e:
                raise Exception(f"Error converting 'before' protobuf to JSON: {e}")
            data_before = json.loads(jsone)
            before_like = data_before.get('AccountInfo', {}).get('Likes', 0)
            try:
                before_like = int(before_like)
            except Exception:
                before_like = 0
            app.logger.info(f"Likes before command: {before_like}")

            if server_name == "IND":
                url = "https://client.ind.freefiremobile.com/LikeProfile"
            elif server_name in {"BR", "US", "SAC", "NA"}:
                url = "https://client.us.freefiremobile.com/LikeProfile"
            else:
                url = "https://clientbp.ggblueshark.com/LikeProfile"

            asyncio.run(send_multiple_requests(uid, server_name, url))

            after = make_request(encrypted_uid, server_name, token)
            if after is None:
                raise Exception("Failed to retrieve player info after like requests.")
            try:
                jsone_after = MessageToJson(after)
            except Exception as e:
                raise Exception(f"Error converting 'after' protobuf to JSON: {e}")
            data_after = json.loads(jsone_after)
            after_like = int(data_after.get('AccountInfo', {}).get('Likes', 0))
            player_uid = int(data_after.get('AccountInfo', {}).get('UID', 0))
            player_name = str(data_after.get('AccountInfo', {}).get('PlayerNickname', ''))
            like_given = after_like - before_like
            status = 1 if like_given != 0 else 2
            result = {
                "LikesGivenByAPI": like_given,
                "LikesbeforeCommand": before_like,
                "LikesafterCommand": after_like,
                "PlayerNickname": player_name,
                "UID": player_uid,
                "status": status
            }
            return result

        result = process_request()
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error processing request: {e}")
        return jsonify({"error": str(e)}), 500
@app.route("/", methods=["GET"])
def home():
    return render_template('dashboard.html')

@app.route("/api", methods=["GET"])
def api_info():
    return jsonify({
        "credits": "Dev By Flexbase",
        "Telegram": "@Flexbaseu",
        "supported_server": "IND only",
        "endpoints": {
            "/like": "Process like requests (IND server only)",
            "/token-status": "Check token health and status",
            "/stats": "View token generation statistics",
            "/refresh-tokens": "Manually trigger token refresh (IND only)"
        }
    })

@app.route("/token-status", methods=["GET"])
def token_status():
    """Get current token system status"""
    try:
        status = token_manager.get_status()
        return jsonify(status), 200
    except Exception as e:
        app.logger.error(f"Error getting token status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/stats", methods=["GET"])
def get_stats():
    """Get token generation statistics"""
    try:
        stats = {
            "service_running": token_manager.is_running,
            "total_tokens_generated": token_manager.stats["total_generated"],
            "total_failures": token_manager.stats["total_failed"],
            "last_refresh": token_manager.stats["last_refresh"],
            "per_region_stats": token_manager.stats["per_region"],
            "refresh_interval_seconds": token_manager.refresh_check_interval,
            "concurrent_limit": token_manager.concurrent_limit
        }
        return jsonify(stats), 200
    except Exception as e:
        app.logger.error(f"Error getting stats: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/refresh-tokens", methods=["POST"])
def refresh_tokens():
    """Manually trigger token refresh for IND region only"""
    try:
        region = request.args.get("region", "IND").upper()
        
        if region != "IND":
            return jsonify({"error": "Only IND region is supported"}), 400
        
        app.logger.info(f"Manual token refresh triggered for region: IND")
        
        token_manager.refresh_tokens_sync("IND")
        
        return jsonify({
            "message": "Token refresh completed for IND region",
            "stats": token_manager.get_status()
        }), 200
        
    except Exception as e:
        app.logger.error(f"Error refreshing tokens: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/generate-all-tokens-stream")
def generate_all_tokens_stream():
    """Stream token generation progress with Server-Sent Events"""
    region = request.args.get("region", "IND").upper()
    
    if region != "IND":
        return jsonify({"error": "Only IND region is supported"}), 400
    
    def generate():
        import asyncio
        import queue
        
        progress_queue = queue.Queue()
        
        async def progress_callback(uid, success, total, current, success_count, failed_count):
            progress_queue.put({
                'uid': uid,
                'success': success,
                'total': total,
                'current': current,
                'success_count': success_count,
                'failed_count': failed_count
            })
        
        async def run_generation():
            try:
                success_count, failed_count = await token_manager.generate_all_tokens(region, progress_callback)
                progress_queue.put({
                    'done': True,
                    'success': success_count,
                    'failed': failed_count,
                    'total': success_count + failed_count
                })
            except Exception as e:
                progress_queue.put({
                    'error': str(e)
                })
        
        import threading
        def run_async():
            asyncio.run(run_generation())
        
        thread = threading.Thread(target=run_async)
        thread.start()
        
        while True:
            try:
                data = progress_queue.get(timeout=1)
                yield f"data: {json.dumps(data)}\n\n"
                
                if data.get('done') or data.get('error'):
                    break
            except:
                yield f"data: {json.dumps({'ping': True})}\n\n"
        
        thread.join()
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

@app.route("/refresh-tokens-stream")
def refresh_tokens_stream():
    """Stream token refresh progress with Server-Sent Events"""
    region = request.args.get("region", "IND").upper()
    
    if region != "IND":
        return jsonify({"error": "Only IND region is supported"}), 400
    
    def generate():
        import queue
        
        progress_queue = queue.Queue()
        
        async def progress_callback(uid, success, total, current, success_count, failed_count):
            progress_queue.put({
                'uid': uid,
                'success': success,
                'total': total,
                'current': current,
                'success_count': success_count,
                'failed_count': failed_count
            })
        
        async def run_refresh():
            try:
                if token_manager.needs_refresh(region):
                    success_count, failed_count = await token_manager.generate_all_tokens(region, progress_callback)
                    progress_queue.put({
                        'done': True,
                        'success': success_count,
                        'failed': failed_count,
                        'total': success_count + failed_count
                    })
                else:
                    progress_queue.put({
                        'done': True,
                        'message': 'Tokens are still valid, no refresh needed'
                    })
            except Exception as e:
                progress_queue.put({
                    'error': str(e)
                })
        
        import threading
        def run_async():
            asyncio.run(run_refresh())
        
        thread = threading.Thread(target=run_async)
        thread.start()
        
        while True:
            try:
                data = progress_queue.get(timeout=1)
                yield f"data: {json.dumps(data)}\n\n"
                
                if data.get('done') or data.get('error'):
                    break
            except:
                yield f"data: {json.dumps({'ping': True})}\n\n"
        
        thread.join()
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

if __name__ == '__main__':
    import os
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=5000, debug=debug_mode)
