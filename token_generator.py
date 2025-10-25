import asyncio
import aiohttp
import ssl
import logging
import os
from datetime import datetime
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from Pb2 import MajoRLoGinrEq_pb2, MajoRLoGinrEs_pb2
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

AES_KEY_STR = os.getenv('AES_ENCRYPTION_KEY')
AES_IV_STR = os.getenv('AES_ENCRYPTION_IV')

if not AES_KEY_STR or not AES_IV_STR:
    logger.warning("⚠️  Using default encryption keys! Set AES_ENCRYPTION_KEY and AES_ENCRYPTION_IV as Replit Secrets for better security")
    AES_KEY_STR = 'Yg&tc%DEuh6%Zc^8'
    AES_IV_STR = '6oyZDr22E3ychjM%'

AES_KEY = AES_KEY_STR.encode('utf-8')
AES_IV = AES_IV_STR.encode('utf-8')

Hr = {
    'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 11; ASUS_Z01QD Build/PI)",
    'Connection': "Keep-Alive",
    'Accept-Encoding': "gzip",
    'Content-Type': "application/x-www-form-urlencoded",
    'Expect': "100-continue",
    'X-Unity-Version': "2018.4.11f1",
    'X-GA': "v1 1",
    'ReleaseVersion': "OB50"
}

async def get_random_ua():
    versions = ['4.0.18P6', '4.0.19P7', '4.0.20P1', '4.1.0P3', '4.1.5P2', '5.5.2P3']
    models = ['SM-A125F', 'SM-A225F', 'Redmi 9A', 'POCO M3', 'ASUS_Z01QD']
    android_versions = ['9', '10', '11', '12']
    version = random.choice(versions)
    model = random.choice(models)
    android = random.choice(android_versions)
    return f"GarenaMSDK/{version}({model};Android {android};en-US;USA;)"

async def encrypted_proto(encoded_hex):
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_IV)
    padded_message = pad(encoded_hex, AES.block_size)
    encrypted_payload = cipher.encrypt(padded_message)
    return encrypted_payload

async def generate_access_token(uid, password):
    """Step 1: Get access token from Garena OAuth"""
    url = "https://100067.connect.garena.com/oauth/guest/token/grant"
    headers = {
        "Host": "100067.connect.garena.com",
        "User-Agent": await get_random_ua(),
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "close"
    }
    data = {
        "uid": uid,
        "password": password,
        "response_type": "token",
        "client_type": "2",
        "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
        "client_id": "100067"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=data, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status != 200:
                    logger.error(f"Failed to get access token for UID {uid}: HTTP {response.status}")
                    return None, None
                    
                data_response = await response.json()
                open_id = data_response.get("open_id")
                access_token = data_response.get("access_token")
                
                if open_id and access_token:
                    return open_id, access_token
                else:
                    logger.error(f"Missing open_id or access_token for UID {uid}")
                    return None, None
    except Exception as e:
        logger.error(f"Exception getting access token for UID {uid}: {e}")
        return None, None

async def encrypt_major_login(open_id, access_token):
    """Step 2: Create encrypted MajorLogin protobuf"""
    major_login = MajoRLoGinrEq_pb2.MajorLogin()
    major_login.event_time = str(datetime.now())[:-7]
    major_login.game_name = "free fire"
    major_login.platform_id = 1
    major_login.client_version = "1.114.1"
    major_login.system_software = "Android OS 9 / API-28 (PQ3B.190801.10101846/G9650ZHU2ARC6)"
    major_login.system_hardware = "Handheld"
    major_login.telecom_operator = "Verizon"
    major_login.network_type = "WIFI"
    major_login.screen_width = 1920
    major_login.screen_height = 1080
    major_login.screen_dpi = "280"
    major_login.processor_details = "ARM64 FP ASIMD AES VMH | 2865 | 4"
    major_login.memory = 3003
    major_login.gpu_renderer = "Adreno (TM) 640"
    major_login.gpu_version = "OpenGL ES 3.1 v1.46"
    major_login.unique_device_id = "Google|34a7dcdf-a7d5-4cb6-8d7e-3b0e448a0c57"
    major_login.client_ip = "223.191.51.89"
    major_login.language = "en"
    major_login.open_id = open_id
    major_login.open_id_type = "4"
    major_login.device_type = "Handheld"
    
    memory_available = major_login.memory_available
    memory_available.version = 55
    memory_available.hidden_value = 81
    
    major_login.access_token = access_token
    major_login.platform_sdk_id = 1
    major_login.network_operator_a = "Verizon"
    major_login.network_type_a = "WIFI"
    major_login.client_using_version = "7428b253defc164018c604a1ebbfebdf"
    major_login.external_storage_total = 36235
    major_login.external_storage_available = 31335
    major_login.internal_storage_total = 2519
    major_login.internal_storage_available = 703
    major_login.game_disk_storage_available = 25010
    major_login.game_disk_storage_total = 26628
    major_login.external_sdcard_avail_storage = 32992
    major_login.external_sdcard_total_storage = 36235
    major_login.login_by = 3
    major_login.library_path = "/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/lib/arm64"
    major_login.reg_avatar = 1
    major_login.library_token = "5b892aaabd688e571f688053118a162b|/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/base.apk"
    major_login.channel_type = 3
    major_login.cpu_type = 2
    major_login.cpu_architecture = "64"
    major_login.client_version_code = "2019118695"
    major_login.graphics_api = "OpenGLES2"
    major_login.supported_astc_bitset = 16383
    major_login.login_open_id_type = 4
    major_login.analytics_detail = b"FwQVTgUPX1UaUllDDwcWCRBpWAUOUgsvA1snWlBaO1kFYg=="
    major_login.loading_time = 13564
    major_login.release_channel = "android"
    major_login.extra_info = "KqsHTymw5/5GB23YGniUYN2/q47GATrq7eFeRatf0NkwLKEMQ0PK5BKEk72dPflAxUlEBir6Vtey83XqF593qsl8hwY="
    major_login.android_engine_init_flag = 110009
    major_login.if_push = 1
    major_login.is_vpn = 1
    major_login.origin_platform_type = "4"
    major_login.primary_platform_type = "4"
    
    string = major_login.SerializeToString()
    return await encrypted_proto(string)

async def send_major_login(payload):
    """Step 3: Send MajorLogin request and get JWT token"""
    url = "https://loginbp.ggblueshark.com/MajorLogin"
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=payload, headers=Hr, ssl=ssl_context, timeout=aiohttp.ClientTimeout(total=15)) as response:
                if response.status == 200:
                    return await response.read()
                else:
                    logger.error(f"MajorLogin failed with status: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"Exception in send_major_login: {e}")
        return None

async def decode_major_login_response(response_data):
    """Step 4: Decode protobuf response to extract JWT token"""
    try:
        proto = MajoRLoGinrEs_pb2.MajorLoginRes()
        proto.ParseFromString(response_data)
        return proto.token if proto.token else None
    except Exception as e:
        logger.error(f"Error decoding MajorLogin response: {e}")
        return None

async def generate_jwt_token(uid, password, retry_count=3):
    """
    Complete JWT token generation flow with retry logic
    
    Args:
        uid: User ID
        password: User password
        retry_count: Number of retry attempts
        
    Returns:
        JWT token string or None if failed
    """
    for attempt in range(retry_count):
        try:
            # Step 1: Get access token
            open_id, access_token = await generate_access_token(uid, password)
            if not open_id or not access_token:
                logger.warning(f"Attempt {attempt + 1}/{retry_count}: Failed to get access token for UID {uid}")
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)
                continue
            
            # Step 2: Encrypt MajorLogin protobuf
            encrypted_payload = await encrypt_major_login(open_id, access_token)
            
            # Step 3: Send MajorLogin request
            response_data = await send_major_login(encrypted_payload)
            if not response_data:
                logger.warning(f"Attempt {attempt + 1}/{retry_count}: Failed to send MajorLogin for UID {uid}")
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)
                continue
            
            # Step 4: Decode response and extract JWT
            jwt_token = await decode_major_login_response(response_data)
            if jwt_token:
                logger.info(f"Successfully generated JWT token for UID {uid}")
                return jwt_token
            else:
                logger.warning(f"Attempt {attempt + 1}/{retry_count}: Failed to decode JWT for UID {uid}")
                if attempt < retry_count - 1:
                    await asyncio.sleep(2 ** attempt)
                
        except Exception as e:
            logger.error(f"Attempt {attempt + 1}/{retry_count}: Exception generating token for UID {uid}: {e}")
            if attempt < retry_count - 1:
                await asyncio.sleep(2 ** attempt)
    
    logger.error(f"Failed to generate JWT token for UID {uid} after {retry_count} attempts")
    return None
