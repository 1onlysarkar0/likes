import asyncio
import json
import jwt
import threading
import time
import logging
from datetime import datetime, timedelta
from filelock import FileLock
from pathlib import Path
from typing import Dict, List, Tuple
from token_generator import generate_jwt_token

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TokenManager:
    def __init__(self):
        self.regions = {
            "IND": {
                "token_file": "token_ind.json",
                "account_file": "accounts_ind.json"
            }
        }
        
        self.stats = {
            "total_generated": 0,
            "total_failed": 0,
            "last_refresh": None,
            "per_region": {
                "IND": {"valid": 0, "failed": 0}
            }
        }
        
        self.concurrent_limit = 15
        self.refresh_check_interval = 1800
        self.expiry_buffer_hours = 1
        self.is_running = False
        
    def load_accounts(self, filename: str) -> List[Tuple[str, str]]:
        """Load accounts from JSON file"""
        try:
            if not Path(filename).exists():
                logger.warning(f"Account file {filename} does not exist")
                return []
                
            with open(filename, 'r') as f:
                accounts_data = json.load(f)
                
            accounts = []
            for account in accounts_data:
                uid = account.get("uid")
                password = account.get("password")
                if uid and password:
                    accounts.append((str(uid), str(password)))
                    
            logger.info(f"Loaded {len(accounts)} accounts from {filename}")
            return accounts
            
        except Exception as e:
            logger.error(f"Error loading accounts from {filename}: {e}")
            return []
    
    def save_tokens(self, tokens: List[Dict], filename: str):
        """Save tokens to JSON file with file locking"""
        lock = FileLock(f"{filename}.lock", timeout=10)
        try:
            with lock:
                with open(filename, 'w') as f:
                    json.dump(tokens, f, indent=2)
                logger.info(f"Saved {len(tokens)} tokens to {filename}")
        except Exception as e:
            logger.error(f"Error saving tokens to {filename}: {e}")
    
    def append_token(self, token: Dict, filename: str):
        """Append a single token to JSON file with file locking"""
        lock = FileLock(f"{filename}.lock", timeout=10)
        try:
            with lock:
                existing_tokens = []
                if Path(filename).exists():
                    with open(filename, 'r') as f:
                        existing_tokens = json.load(f)
                
                existing_tokens.append(token)
                
                with open(filename, 'w') as f:
                    json.dump(existing_tokens, f, indent=2)
        except Exception as e:
            logger.error(f"Error appending token to {filename}: {e}")
    
    def load_tokens(self, filename: str) -> List[Dict]:
        """Load tokens from JSON file"""
        try:
            if not Path(filename).exists():
                return []
                
            with open(filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading tokens from {filename}: {e}")
            return []
    
    def check_token_expiry(self, token_str: str) -> bool:
        """
        Check if token needs refresh (expires within buffer time)
        
        Returns:
            True if token needs refresh, False otherwise
        """
        try:
            decoded = jwt.decode(token_str, options={"verify_signature": False})
            exp = decoded.get("exp")
            
            if exp:
                exp_time = datetime.fromtimestamp(exp)
                time_until_expiry = exp_time - datetime.now()
                
                needs_refresh = time_until_expiry < timedelta(hours=self.expiry_buffer_hours)
                
                if needs_refresh:
                    logger.info(f"Token expires in {time_until_expiry}, needs refresh")
                    
                return needs_refresh
            else:
                logger.warning("Token has no exp field, marking for refresh")
                return True
                
        except jwt.DecodeError:
            logger.warning("Failed to decode token, marking for refresh")
            return True
        except Exception as e:
            logger.error(f"Error checking token expiry: {e}")
            return True
    
    def needs_refresh(self, region: str) -> bool:
        """Check if tokens for a region need refreshing"""
        token_file = self.regions[region]["token_file"]
        
        try:
            tokens = self.load_tokens(token_file)
            
            if not tokens:
                logger.info(f"No tokens found for {region}, needs generation")
                return True
            
            sample_size = min(5, len(tokens))
            sample_tokens = tokens[:sample_size]
            
            expired_count = sum(1 for t in sample_tokens if self.check_token_expiry(t["token"]))
            
            needs_refresh = expired_count > (sample_size // 2)
            
            if needs_refresh:
                logger.info(f"Region {region}: {expired_count}/{sample_size} sample tokens expired, refreshing all")
            else:
                logger.info(f"Region {region}: {expired_count}/{sample_size} sample tokens expired, no refresh needed")
                
            return needs_refresh
            
        except Exception as e:
            logger.error(f"Error checking refresh status for {region}: {e}")
            return True
    
    async def generate_token_with_limit(self, semaphore: asyncio.Semaphore, uid: str, password: str) -> dict:
        """Generate token with concurrency limit"""
        async with semaphore:
            token = await generate_jwt_token(uid, password)
            return {"token": token, "uid": uid, "generated_at": datetime.now().isoformat()}
    
    async def generate_all_tokens(self, region: str, progress_callback=None) -> Tuple[int, int]:
        """
        Generate tokens for all accounts in a region with real-time progress
        
        Args:
            region: Region name
            progress_callback: Optional callback function(uid, success, total_accounts, current_index)
        
        Returns:
            Tuple of (successful_count, failed_count)
        """
        account_file = self.regions[region]["account_file"]
        token_file = self.regions[region]["token_file"]
        
        accounts = self.load_accounts(account_file)
        
        if not accounts:
            logger.warning(f"No accounts to process for region {region}")
            return 0, 0
        
        logger.info(f"Starting token generation for {len(accounts)} accounts in region {region}")
        
        # Clear existing tokens file for fresh generation
        Path(token_file).write_text('[]')
        
        success_count = 0
        failed_count = 0
        total_accounts = len(accounts)
        
        semaphore = asyncio.Semaphore(self.concurrent_limit)
        
        async def generate_and_save(index, uid, password):
            nonlocal success_count, failed_count
            async with semaphore:
                try:
                    result = await generate_jwt_token(uid, password)
                    if result:
                        token_dict = {"token": result}
                        self.append_token(token_dict, token_file)
                        success_count += 1
                        if progress_callback:
                            await progress_callback(uid, True, total_accounts, index + 1, success_count, failed_count)
                        return True
                    else:
                        failed_count += 1
                        if progress_callback:
                            await progress_callback(uid, False, total_accounts, index + 1, success_count, failed_count)
                        return False
                except Exception as e:
                    logger.error(f"Error generating token for UID {uid}: {e}")
                    failed_count += 1
                    if progress_callback:
                        await progress_callback(uid, False, total_accounts, index + 1, success_count, failed_count)
                    return False
        
        tasks = [
            generate_and_save(idx, uid, password)
            for idx, (uid, password) in enumerate(accounts)
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        self.stats["total_generated"] += success_count
        self.stats["total_failed"] += failed_count
        self.stats["per_region"][region]["valid"] = success_count
        self.stats["per_region"][region]["failed"] = failed_count
        self.stats["last_refresh"] = datetime.now().isoformat()
        
        logger.info(f"Region {region}: Generated {success_count} tokens, {failed_count} failed")
        
        return success_count, failed_count
    
    async def refresh_tokens_async(self, region: str = None):
        """Async token refresh for one or all regions"""
        if region:
            regions_to_refresh = [region]
        else:
            regions_to_refresh = list(self.regions.keys())
        
        for reg in regions_to_refresh:
            if self.needs_refresh(reg):
                logger.info(f"Refreshing tokens for region {reg}")
                await self.generate_all_tokens(reg)
            else:
                logger.info(f"Region {reg} tokens are still valid, skipping refresh")
    
    def refresh_tokens_sync(self, region: str = None):
        """Synchronous wrapper for token refresh"""
        try:
            asyncio.run(self.refresh_tokens_async(region))
        except Exception as e:
            logger.error(f"Error in synchronous token refresh: {e}")
    
    def auto_refresh_loop(self):
        """Background loop for automatic token refresh"""
        logger.info("Token auto-refresh service started")
        
        while self.is_running:
            try:
                logger.info("Running scheduled token refresh check...")
                
                for region in self.regions.keys():
                    try:
                        if self.needs_refresh(region):
                            logger.info(f"Auto-refreshing tokens for {region}")
                            asyncio.run(self.generate_all_tokens(region))
                    except Exception as e:
                        logger.error(f"Error refreshing {region}: {e}")
                
                logger.info(f"Refresh check complete. Next check in {self.refresh_check_interval} seconds")
                
            except Exception as e:
                logger.error(f"Error in auto-refresh loop: {e}")
            
            time.sleep(self.refresh_check_interval)
        
        logger.info("Token auto-refresh service stopped")
    
    def start_background_service(self):
        """Start the background token refresh service"""
        if self.is_running:
            logger.warning("Background service already running")
            return
        
        self.is_running = True
        
        thread = threading.Thread(target=self.auto_refresh_loop, daemon=True, name="TokenRefreshService")
        thread.start()
        
        logger.info("Token auto-refresh background service started successfully")
    
    def stop_background_service(self):
        """Stop the background service"""
        self.is_running = False
        logger.info("Token auto-refresh service stop requested")
    
    def get_status(self) -> dict:
        """Get current status of token system"""
        status = {
            "service_running": self.is_running,
            "stats": self.stats,
            "regions": {}
        }
        
        for region, config in self.regions.items():
            tokens = self.load_tokens(config["token_file"])
            token_count = len(tokens)
            
            if tokens and token_count > 0:
                sample_token = tokens[0]["token"]
                try:
                    decoded = jwt.decode(sample_token, options={"verify_signature": False})
                    exp = decoded.get("exp")
                    if exp:
                        exp_time = datetime.fromtimestamp(exp)
                        time_until_expiry = exp_time - datetime.now()
                        next_refresh = exp_time - timedelta(hours=self.expiry_buffer_hours)
                        status["regions"][region] = {
                            "token_count": token_count,
                            "expires_at": exp_time.isoformat(),
                            "time_until_expiry": str(time_until_expiry),
                            "next_refresh_at": next_refresh.isoformat()
                        }
                    else:
                        status["regions"][region] = {
                            "token_count": token_count,
                            "status": "No expiry info"
                        }
                except:
                    status["regions"][region] = {
                        "token_count": token_count,
                        "status": "Cannot decode token"
                    }
            else:
                status["regions"][region] = {
                    "token_count": 0,
                    "status": "No tokens available"
                }
        
        return status

token_manager = TokenManager()
