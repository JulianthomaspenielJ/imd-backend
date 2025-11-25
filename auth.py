import boto3
import os
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel, EmailStr, Field, validator
from fastapi.middleware.cors import CORSMiddleware

from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field, validator
from jose import JWTError, jwt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# AWS Cognito configuration
COGNITO_CLIENT = boto3.client('cognito-idp', region_name=os.getenv('AWS_REGION', 'ap-south-1'))
USER_POOL_ID = os.getenv('COGNITO_USER_POOL_ID', 'ap-south-1_vNL3BkjGt')
CLIENT_ID = os.getenv('COGNITO_CLIENT_ID', '4sgvj6d8us0ujbqi7ddo75t8nq')

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")  # In production, use a strong secret key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 90

# Initialize FastAPI app
app = FastAPI(title="Authentication API", version="1.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)

class UserInfo(BaseModel):
    username: str
    email: str
    user_role: str

class TemporaryPasswordResponse(BaseModel):
    isTemporaryPassword: bool
    user: dict

class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: str
    user: UserInfo

class ChangePasswordRequest(BaseModel):
    email: EmailStr
    temporary_password: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)
    confirm_new_password: str = Field(..., min_length=8)

    @validator('confirm_new_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('New passwords do not match')
        return v


class StatusChangeRequest(BaseModel):
    email: EmailStr
    status: str

    @validator('status')
    def validate_status(cls, v):
        status_lower = v.lower()
        if status_lower not in ['approved', 'rejected']:
            raise ValueError('Status must be either "Approved" or "Rejected"')
        return v  # Return the original value to preserve case

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ConfirmForgotPasswordRequest(BaseModel):
    email: EmailStr
    verification_code: str
    new_password: str = Field(..., min_length=8)
    confirm_new_password: str = Field(..., min_length=8)

    @validator('confirm_new_password')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('New passwords do not match')
        return v


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """
    Create a JWT token with the provided data and expiration time
    Returns a string containing the JWT token
    """
    try:
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
        to_encode.update({"exp": expire})
        
        # Ensure SECRET_KEY is a string and not None
        if not isinstance(SECRET_KEY, str) or not SECRET_KEY:
            raise ValueError("SECRET_KEY must be a non-empty string")
            
        # Encode the JWT token
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        
        # Ensure the result is a string
        if isinstance(encoded_jwt, bytes):
            return encoded_jwt.decode('utf-8')
        return str(encoded_jwt)
        
    except Exception as e:
        print(f"Error creating access token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create access token"
        )

# Function to verify temporary password
def verify_temporary_password(email: str, temp_password: str) -> bool:
    try:
        # First try to authenticate with the temporary password
        COGNITO_CLIENT.admin_initiate_auth(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': temp_password
            }
        )
        return True
    except COGNITO_CLIENT.exceptions.NotAuthorizedException:
        return False
    except Exception as e:
        print(f"Error verifying temporary password: {str(e)}")
        raise HTTPException(status_code=400, detail="Error verifying temporary password")

# Function to update password in Cognito
def update_cognito_password(email: str, temp_password: str, new_password: str):
    try:
        # First authenticate to get the session
        auth_response = COGNITO_CLIENT.admin_initiate_auth(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID,
            AuthFlow='ADMIN_NO_SRP_AUTH',
            AuthParameters={
                'USERNAME': email,
                'PASSWORD': temp_password
            }
        )
        
        # If authentication is successful, respond with challenge
        if auth_response.get('ChallengeName') == 'NEW_PASSWORD_REQUIRED':
            # Respond to the new password required challenge
            COGNITO_CLIENT.respond_to_auth_challenge(
                ClientId=CLIENT_ID,
                ChallengeName='NEW_PASSWORD_REQUIRED',
                Session=auth_response['Session'],
                ChallengeResponses={
                    'USERNAME': email,
                    'NEW_PASSWORD': new_password
                }
            )
        else:
            # If no challenge is required, just update the password
            COGNITO_CLIENT.admin_set_user_password(
                UserPoolId=USER_POOL_ID,
                Username=email,
                Password=new_password,
                Permanent=True
            )
        
        return True
    except COGNITO_CLIENT.exceptions.NotAuthorizedException:
        raise HTTPException(status_code=400, detail="Invalid temporary password")
    except Exception as e:
        print(f"Error updating password in Cognito: {str(e)}")
        raise HTTPException(status_code=400, detail="Error updating password")


@app.post("/login", response_model=None, responses={
    200: {"model": Token},
    202: {"model": TemporaryPasswordResponse, "description": "Temporary password detected"}
}, tags=["Authentication"])
async def login(login_data: LoginRequest):
    """
    Authenticate user with email and password against Cognito
    and return JWT tokens with 90-day expiration along with user info
    """
    try:
        # Authenticate with Cognito
        response = COGNITO_CLIENT.initiate_auth(
            ClientId=CLIENT_ID,
            AuthFlow='USER_PASSWORD_AUTH',
            AuthParameters={
                'USERNAME': login_data.email,
                'PASSWORD': login_data.password
            }
        )
        
        # Check for NEW_PASSWORD_REQUIRED challenge (temporary password)
        if response.get('ChallengeName') == 'NEW_PASSWORD_REQUIRED':
            # Get user details from Cognito
            try:
                user_info = COGNITO_CLIENT.admin_get_user(
                    UserPoolId=USER_POOL_ID,
                    Username=login_data.email
                )
                user_attrs = {attr['Name']: attr['Value'] for attr in user_info['UserAttributes']}
                username = user_info['Username']
                user_role = user_attrs.get('custom:role', 'user')
                
                return JSONResponse(
                    status_code=status.HTTP_202_ACCEPTED,
                    content={
                        "isTemporaryPassword": True,
                        "user": {
                            "id": username,
                            "email": login_data.email,
                            "user_role": user_role,
                            "username": username  # Add username to match UserInfo model
                        }
                    }
                )
            except Exception as e:
                print(f"Error getting user details: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Temporary password detected but failed to get user details"
                )
        
        # If authentication is successful, create a JWT token
        if 'AuthenticationResult' in response:
            auth_result = response['AuthenticationResult']
            
            # Get user details from Cognito
            user_info = COGNITO_CLIENT.get_user(
                AccessToken=auth_result['AccessToken']
            )
            
            # Extract user attributes
            user_attrs = {attr['Name']: attr['Value'] for attr in user_info['UserAttributes']}
            username = user_info['Username']
            email = user_attrs.get('email', login_data.email)
            user_role = user_attrs.get('custom:role', 'user')  # Default role is 'user' if not specified
            
            # Create a JWT token with 90-day expiration
            access_token_expires = timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
            access_token = create_access_token(
                data={
                    "sub": login_data.email,
                    "username": username,
                    "role": user_role
                },
                expires_delta=access_token_expires
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": int(access_token_expires.total_seconds()),
                "refresh_token": auth_result.get('RefreshToken', ''),
                "user": {
                    "username": username,
                    "email": email,
                    "user_role": user_role
                }
            }
            
    except COGNITO_CLIENT.exceptions.NotAuthorizedException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except COGNITO_CLIENT.exceptions.UserNotConfirmedException:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please confirm your email address before logging in"
        )
    except Exception as e:
        print(f"Error during login: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during login"
        )
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

# Dependency to get the current user from the JWT token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    return email

@app.post("/logout", tags=["Authentication"])
async def logout(
    request: Request,
    current_user: str = Depends(get_current_user)
):
    """
    Logout user by invalidating the current access token
    """
    try:
        # Get the token from the Authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        token = auth_header.split(" ")[1]
        
        # In a production environment, you would want to:
        # 1. Add the token to a blacklist/denylist in Redis/Database
        # 2. Set a short expiration on the blacklisted token
        # 3. Check this blacklist in the get_current_user dependency
        
        # For now, we'll just return a success message
        # In a real app, you would invalidate the token server-side
        
        return {
            "status": "success",
            "message": "Successfully logged out"
        }
        
    except Exception as e:
        print(f"Logout error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not process logout"
        )

@app.post("/change-password", response_model=dict)
async def change_password(request: ChangePasswordRequest):
    # Verify that the new passwords match
    if request.new_password != request.confirm_new_password:
        raise HTTPException(status_code=400, detail="New passwords do not match")
    
    # Verify the temporary password
    if not verify_temporary_password(request.email, request.temporary_password):
        raise HTTPException(status_code=400, detail="Invalid email or temporary password")
    
    try:
        # Update password in Cognito
        update_cognito_password(request.email, request.temporary_password, request.new_password)
        
        return {
            "status": "success",
            "message": "Password updated successfully in Cognito"
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error in change_password: {str(e)}")
        raise HTTPException(status_code=500, detail="An error occurred while updating the password")


@app.post("/auth/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """
    Initiates the password reset process by sending a verification code to the user's email
    """
    try:
        # This will trigger the forgot password flow in Cognito
        COGNITO_CLIENT.forgot_password(
            ClientId=CLIENT_ID,
            Username=request.email
        )
        return {"message": "If your email is registered, you will receive a verification code"}
    except COGNITO_CLIENT.exceptions.UserNotFoundException:
        # Don't reveal if user exists or not for security reasons
        return {"message": "If your email is registered, you will receive a verification code"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post("/auth/confirm-forgot-password")
async def confirm_forgot_password(request: ConfirmForgotPasswordRequest):
    """
    Confirms the verification code and updates the password
    """
    try:
        # Confirm the password reset with the verification code
        COGNITO_CLIENT.confirm_forgot_password(
            ClientId=CLIENT_ID,
            Username=request.email,
            ConfirmationCode=request.verification_code,
            Password=request.new_password
        )
        return {"message": "Password has been reset successfully"}
    except COGNITO_CLIENT.exceptions.CodeMismatchException:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )
    except COGNITO_CLIENT.exceptions.ExpiredCodeException:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# Example protected route
@app.get("/users/me")
async def read_users_me(request: Request, current_user: str = Depends(get_current_user)):
    """
    Get current user's information from the JWT token
    """
    try:
        token = request.headers.get("authorization", "").split(" ")[1]
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        return {
            "username": payload.get("username"),
            "email": payload.get("sub"),
            "user_role": payload.get("role", "user")
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )

@app.put("/users/status", status_code=status.HTTP_200_OK, tags=["Users"])
async def update_user_status(
    status_data: StatusChangeRequest,
    current_user: str = Depends(get_current_user)
):
    """
    Update user status (Approved/Rejected)
    - Only accessible by admin users
    - If status is Rejected: Updates status in database and deletes user from Cognito
    - If status is Approved: Updates status in database (Cognito will send temp password email)
    """
    try:
        # Verify current user has admin privileges using Cognito
        try:
            # Get the username/email from the JWT token
            if isinstance(current_user, dict):
                username = current_user.get('username') or current_user.get('email') or current_user.get('sub')
            elif isinstance(current_user, str):
                username = current_user
            else:
                username = str(current_user)
            
            if not username:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Could not determine user identity from token"
                )
            
            # Get user details from Cognito
            try:
                response = COGNITO_CLIENT.admin_get_user(
                    UserPoolId=USER_POOL_ID,
                    Username=username
                )
                
                # Extract user attributes
                user_attrs = {attr['Name']: attr['Value'] for attr in response.get('UserAttributes', [])}
                
                # Check if user is admin
                # The role might be in custom attributes or groups
                user_role = None
                
                # Check custom:role attribute first
                if 'custom:role' in user_attrs:
                    user_role = user_attrs['custom:role']
                # Check if user is in admin group
                elif 'cognito:groups' in response:
                    if 'admin_ims' in response['cognito:groups']:
                        user_role = 'admin_ims'
                
                
                if user_role != 'admin_ims':
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Not authorized to perform this action. Admin access required."
                    )
                    
            except COGNITO_CLIENT.exceptions.UserNotFoundException:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found in Cognito"
                )
                
        except HTTPException:
            raise
            
        except Exception as e:
            print(f"Error verifying admin status in Cognito: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error verifying user permissions"
            )

        # Update status in database
        with psycopg2.connect(
            dbname=os.getenv("DB_NAME", "ims_db"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "*Postgres16"),
            host=os.getenv("DB_HOST", "localhost"),
            cursor_factory=RealDictCursor
        ) as conn:
            with conn.cursor() as cur:
                # Update user status in database
                update_query = """
                    UPDATE tb_users 
                    SET active_status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE email_address = %s
                    RETURNING id, email_address, active_status
                """
                # Use the status as provided (should already be validated as 'Approved' or 'Rejected')
                cur.execute(update_query, (status_data.status, status_data.email))
                updated_user = cur.fetchone()
                
                if not updated_user:
                    raise HTTPException(status_code=404, detail="User not found")
                
                conn.commit()

                # Handle status-specific actions
                if status_data.status.lower() == 'rejected':
                    # If status is Rejected, delete user from Cognito
                    try:
                        COGNITO_CLIENT.admin_delete_user(
                            UserPoolId=USER_POOL_ID,
                            Username=status_data.email
                        )
                    except COGNITO_CLIENT.exceptions.UserNotFoundException:
                        # User not found in Cognito, but we've already updated the database
                        pass
                    except Exception as e:
                        print(f"Error deleting user from Cognito: {str(e)}")
                        # We don't want to fail the entire operation if Cognito deletion fails
                        # as the database has already been updated
                
                elif status_data.status.lower() == 'approved':
                    # If status is Approved, resend the welcome email with the temporary password
                    try:
                        # Get user details from database
                        cur.execute("""
                            SELECT email_address, company_name, admin_name
                            FROM tb_users 
                            WHERE email_address = %s
                        """, (status_data.email,))
                        user_data = cur.fetchone()
                        
                        if not user_data:
                            raise HTTPException(status_code=404, detail="User not found in database")
                        
                        try:
                            # Check if user exists in Cognito
                            try:
                                # This will throw UserNotFoundException if user doesn't exist
                                COGNITO_CLIENT.admin_get_user(
                                    UserPoolId=USER_POOL_ID,
                                    Username=user_data['email_address']
                                )
                                
                                # User exists, resend the welcome message with temporary password
                                COGNITO_CLIENT.admin_create_user(
                                    UserPoolId=USER_POOL_ID,
                                    Username=user_data['email_address'],
                                    # These attributes are required but won't be updated since user exists
                                    UserAttributes=[],
                                    # This will resend the welcome email with the existing temporary password
                                    MessageAction='RESEND',
                                    DesiredDeliveryMediums=['EMAIL']
                                )
                                
                                # Make sure the user is enabled
                                COGNITO_CLIENT.admin_enable_user(
                                    UserPoolId=USER_POOL_ID,
                                    Username=user_data['email_address']
                                )
                                
                                print(f"Welcome email with temporary password resent to {user_data['email_address']}")
                                
                            except COGNITO_CLIENT.exceptions.UserNotFoundException:
                                # User doesn't exist in Cognito, this shouldn't normally happen
                                print(f"User {user_data['email_address']} not found in Cognito")
                                raise HTTPException(
                                    status_code=400, 
                                    detail="User not found in Cognito. Please register first."
                                )
                            
                        except COGNITO_CLIENT.exceptions.UsernameExistsException:
                            # This should not happen since we checked first, but handle it just in case
                            print(f"User {user_data['email_address']} already exists in Cognito")
                            # Try to resend the welcome email
                            COGNITO_CLIENT.admin_create_user(
                                UserPoolId=USER_POOL_ID,
                                Username=user_data['email_address'],
                                UserAttributes=[],
                                MessageAction='RESEND',
                                DesiredDeliveryMediums=['EMAIL']
                            )
                            
                    except Exception as e:
                        print(f"Error in Cognito operations: {str(e)}")
                        # Log the error but don't fail the operation
                        # The database has already been updated, so we don't want to roll that back
        
        return {"message": f"User status updated to {status_data.status} successfully"}
    
    except Exception as e:
        print(f"Error updating user status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating user status: {str(e)}")

@app.get("/users", response_model=Dict[str, Any], tags=["Users"])
async def get_users_list(request: Request, current_user: dict = Depends(get_current_user)):
    """
    Get list of all users with statistics
    - Only accessible by users with admin_ims role
    - Returns total users (status = 1)
    - Count by active_status (Pending, Approved, Rejected)
    - User details including company_name, admin_name, active_status, created_at
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        
        # Get token and decode it to verify role
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Check role in multiple possible locations in the JWT payload
            user_role = (
                payload.get("custom:role") or  # Cognito format
                payload.get("role") or         # Standard JWT
                payload.get("user_role") or    # Alternative custom claim
                ""
            )
    
            
            # Check if user has admin_ims role (case-insensitive check)
            if user_role.lower() != "admin_ims":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required role: admin_ims, found: {user_role}"
                )
                
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        # Get database connection using the same config as other functions
        DB_CONFIG = {
            "host": "localhost",
            "dbname": "ims_db",  # Changed from ims_db to ims based on your DB_CONFIG
            "user": "postgres",
            "password": "*Postgres16"
        }
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        # Get total active users (status = 1)
        cursor.execute("""
            SELECT COUNT(*) as total_users 
            FROM tb_users 
            WHERE status = 1
        """)
        total_users = cursor.fetchone()['total_users']

        # Get count by active_status
        cursor.execute("""
            SELECT 
                active_status,
                COUNT(*) as count
            FROM tb_users
            WHERE status = 1
            GROUP BY active_status
        """)
        status_counts = {}
        for row in cursor.fetchall():
            status_counts[row['active_status'].lower()] = row['count']

        # Get user details
        cursor.execute("""
            SELECT 
                id,
                admin_name,
                email_address,
                company_name,
                user_name,
                features,
                active_status,
                created_at,
                user_role
            FROM tb_users
            WHERE status = 1
            ORDER BY created_at DESC
        """)
        users = cursor.fetchall()

        # Convert datetime to ISO format for JSON serialization
        for user in users:
            if user['created_at']:
                user['created_at'] = user['created_at'].isoformat()

        cursor.close()
        conn.close()

        return {
            "total_users": total_users,
            "pending": status_counts.get('pending', 0),
            "approved": status_counts.get('approved', 0),
            "rejected": status_counts.get('rejected', 0),
            "users": users
        }

    except Exception as e:
        print(f"Error fetching users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching users list"
        )

@app.get("/users/features", tags=["Users"])
async def get_user_features(request: Request):
    """
    Get features details of a user.
    - Requires Authorization header with Bearer token (from localStorage).
    - Only accessible by users with custom:role == company_admin.
    """
    try:
        # Get token from Authorization header
        auth_header = request.headers.get("authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
        token = auth_header.split(" ")[1]

        # Decode JWT token
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

        # Get email and role from token
        email = payload.get("sub")
        user_role = payload.get("custom:role") or payload.get("role") or ""

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not found in token"
            )

        # Check if user is company_admin
        if user_role.lower() != "company_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions. Required role: company_admin"
            )

        # Fetch features from tb_users
        DB_CONFIG = {
            "host": "localhost",
            "dbname": "ims_db",
            "user": "postgres",
            "password": "*Postgres16"
        }
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(
            "SELECT features FROM tb_users WHERE email_address = %s AND status = 1",
            (email,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        return {"email": email, "features": row["features"]}

    except Exception as e:
        print(f"Error fetching user features: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching user features"
        )
