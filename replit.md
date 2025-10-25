# Free Fire Like API

## Overview
This is a Flask-based REST API service that was migrated from Vercel to Replit. The application provides endpoints for managing Free Fire game profile likes and token management for the IND server.

## Recent Changes (October 25, 2025)
- **Migration from Vercel to Replit**: Complete platform migration
- **Security Enhancement**: Moved hardcoded AES encryption keys to environment variables (AES_ENCRYPTION_KEY, AES_ENCRYPTION_IV) with backward-compatible defaults
- **Environment Setup**: Configured Python 3.11 with all required dependencies
- **Deployment Configuration**: Set up Gunicorn with 4 workers for production deployment
- **Workflow Configuration**: Configured server to run on port 5000 with proper host binding (0.0.0.0)

## Project Architecture

### Main Components
1. **app.py**: Main Flask application with API endpoints
   - `/` - API information and available endpoints
   - `/like` - Process like requests for Free Fire profiles (IND server only)
   - `/token-status` - Check token system health and expiration status
   - `/stats` - View token generation statistics
   - `/refresh-tokens` - Manually trigger token refresh

2. **token_manager.py**: Background service for JWT token management
   - Auto-refresh tokens based on expiration
   - Concurrent token generation with rate limiting
   - File-based token storage with locking mechanism

3. **token_generator.py**: JWT token generation flow
   - Multi-step OAuth authentication with Garena
   - Protobuf message encryption
   - Retry logic for reliability

4. **proto/**: Protocol buffer definitions for API communication
5. **Pb2/**: Additional protobuf definitions for authentication

### Technology Stack
- **Framework**: Flask 3.1.2 with async support
- **Server**: Gunicorn 23.0.0 (4 workers, sync worker class)
- **Encryption**: AES-256 CBC mode (pycryptodome)
- **Auth**: JWT tokens with PyJWT
- **HTTP Client**: aiohttp for async requests, requests for sync
- **Protobuf**: Google Protocol Buffers for data serialization

### Security Features
- Environment variable-based encryption key management
- File locking for concurrent token access
- Background token refresh service
- Secure JWT token handling

### Deployment
- **Platform**: Replit
- **Deployment Type**: VM (stateful, always running)
- **Port**: 5000
- **Workers**: 4 Gunicorn workers
- **Timeout**: 120 seconds

## Environment Variables (Required)
- `AES_ENCRYPTION_KEY`: AES encryption key (exactly 16 characters, **REQUIRED**)
- `AES_ENCRYPTION_IV`: AES initialization vector (exactly 16 characters, **REQUIRED**)
- `FLASK_DEBUG`: Set to 'true' for debug mode (optional)

**Important**: The application will not start without valid AES_ENCRYPTION_KEY and AES_ENCRYPTION_IV environment variables. These must be set as Replit Secrets for security.

## Data Files
- `token_ind.json`: JWT tokens for IND server
- `accounts_ind.json`: Account credentials for token generation
- `token_ind.json.lock`: File lock for concurrent access control

## Server Support
Currently supports **IND server only** for Free Fire operations.
