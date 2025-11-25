import boto3
import os
import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, validator
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from dotenv import load_dotenv
import secrets
import string

# Load environment variables
load_dotenv()

# AWS Cognito configuration
COGNITO_CLIENT = boto3.client('cognito-idp', region_name=os.getenv('AWS_REGION', 'ap-south-1'))
USER_POOL_ID = os.getenv('COGNITO_USER_POOL_ID', 'ap-south-1_vNL3BkjGt')
CLIENT_ID = os.getenv('COGNITO_CLIENT_ID', '4sgvj6d8us0ujbqi7ddo75t8nq')

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "dbname": "ims_db",
    "user": "postgres",
    "password": "*Postgres16",  # Change to your password
    "port": 5432
}

# Initialize FastAPI
app = FastAPI(title="Registration API", version="1.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class AccountIn(BaseModel):
    accountId: str = Field(..., alias="accountId")
    accountName: str
    accessKey: str
    secretKey: str
    bucketName: Optional[str] = None
    prefix: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

class DetailsIn(BaseModel):
    companyName: str
    adminName: str
    userName: str
    mailId: EmailStr
    features: List[str]

class RegistrationRequest(BaseModel):
    details: DetailsIn
    accounts: List[AccountIn]

class RegisterResponse(BaseModel):
    user_id: str
    username: str
    email: str
    message: str

# Database connection
def get_db_conn():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        raise

# Helper function to execute database queries
def execute_query(query: str, params: tuple = (), fetch: bool = False):
    conn = None
    try:
        conn = get_db_conn()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            if fetch:
                result = cursor.fetchall()
                return result
            conn.commit()
            return cursor.rowcount
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"Database error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if conn:
            conn.close()

# Register user endpoint
@app.post("/register", response_model=RegisterResponse)
async def register_user(registration: RegistrationRequest):
    # Generate a new user ID
    user_id = str(uuid.uuid4())
    current_time = datetime.utcnow()
    
    try:
        # Generate a temporary password that meets AWS Cognito requirements:
        # - At least 8 characters long
        # - Contains a lowercase letter
        # - Contains an uppercase letter
        # - Contains a number
        # - Contains a special character
        import random
        
        # Ensure we have at least one of each required character type
        lowercase = random.choice(string.ascii_lowercase)
        uppercase = random.choice(string.ascii_uppercase)
        digit = random.choice(string.digits)
        special = random.choice('!@#$%^&*()_+-=[]{}|;:,.<>?')
        
        # Generate remaining characters
        remaining = ''.join(secrets.choice(string.ascii_letters + string.digits + '!@#$%^&*()_+-=[]{}|;:,.<>?') 
                          for _ in range(8))  # 8 + 4 = 12 characters total
        
        # Combine and shuffle
        temp_password = list(lowercase + uppercase + digit + special + remaining)
        random.shuffle(temp_password)
        temp_password = ''.join(temp_password)

        # Register user in Cognito with a temporary password
        cognito_response = COGNITO_CLIENT.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=registration.details.mailId,
            TemporaryPassword=temp_password,
            UserAttributes=[
                {'Name': 'email', 'Value': registration.details.mailId},
                {'Name': 'email_verified', 'Value': 'true'},
                {'Name': 'custom:role', 'Value': 'company_admin'},
                {'Name': 'name', 'Value': registration.details.adminName},
            ],
            MessageAction='SUPPRESS'  # Suppress the default welcome email
        )
        
        
        # Store user in tb_users
        user_query = """
        INSERT INTO tb_users (
            id, company_name, admin_name, email_address, user_role,
            user_name, features, created_at, created_by, 
            updated_at, updated_by
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        user_params = [
            user_id,
            registration.details.companyName,
            registration.details.adminName,
            registration.details.mailId,
            'company_admin',
            registration.details.userName,
            registration.details.features,
            current_time,
            user_id,
            current_time,
            user_id,
        ]
        execute_query(user_query, user_params)
        
        # Process each account
        for account in registration.accounts:
            if 'Cost' in registration.details.features and (
                'Security' in registration.details.features or 
                'Performance' in registration.details.features
            ):
                # Store in both tables if all features are selected
                store_in_cur_multiple_user(account, user_id, current_time)
                store_in_master_credentials_mvp(account, user_id, current_time)
            elif 'Cost' in registration.details.features:
                # Store only in cur_multiple_user
                store_in_cur_multiple_user(account, user_id, current_time)
            elif 'Security' in registration.details.features or 'Performance' in registration.details.features:
                # Store only in master_credentials_mvp
                store_in_master_credentials_mvp(account, user_id, current_time)
        
        return {
            "user_id": user_id,
            "username": registration.details.userName,
            "email": registration.details.mailId,
            "message": "User registered successfully"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")

def store_in_cur_multiple_user(account: AccountIn, user_id: str, created_at: datetime):
    query = """
    INSERT INTO cur_multiple_user (
        account_id, account_name, access_key, secret_key, 
        prefix, bucket_name, user_id, created_at, created_by, 
        updated_at, updated_by
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        account.accountId,
        account.accountName,
        account.accessKey,
        account.secretKey,
        account.prefix or '',
        account.bucketName or '',
        user_id,
        created_at,
        user_id,
        created_at,
        user_id
    )
    execute_query(query, params)

def store_in_master_credentials_mvp(account: AccountIn, user_id: str, created_at: datetime):
    query = """
    INSERT INTO master_credentials_mvp (
        account_id, account_name, access_key, secret_key, 
        username, password, user_id, created_at, created_by, 
        updated_at, updated_by
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (
        account.accountId,
        account.accountName,
        account.accessKey,
        account.secretKey,
        account.username or '',
        account.password or '',
        user_id,
        created_at,
        user_id,
        created_at,
        user_id
    )
    execute_query(query, params)

