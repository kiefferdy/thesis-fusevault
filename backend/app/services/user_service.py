from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timezone
from app.repositories.user_repo import UserRepository
from app.schemas.user_schema import UserCreate, UserResponse, UserProfileResponse

logger = logging.getLogger(__name__)

class UserService:
    """
    Service for user-related operations.
    Encapsulates business logic for user management.
    """
    
    def __init__(self, user_repository: UserRepository):
        """
        Initialize with user repository.
        
        Args:
            user_repository: Repository for user data access
        """
        self.user_repository = user_repository
        
    async def create_user(self, user_data: UserCreate) -> Dict[str, Any]:
        """
        Create a new user.
        
        Args:
            user_data: User data for creation
            
        Returns:
            Created user response
            
        Raises:
            ValueError: If user with wallet address already exists
        """
        try:
            # Check if user already exists
            existing_user = await self.user_repository.find_user(
                {"walletAddress": user_data.wallet_address}
            )
            
            if existing_user:
                # Return existing user
                return self._format_user_response(existing_user)
            
            # Prepare user data for insertion
            user_doc = {
                "walletAddress": user_data.wallet_address,
                "email": user_data.email,
                "role": user_data.role or "user",  # Default role
                "createdAt": datetime.now(timezone.utc),
                "lastLogin": None
            }
            
            # Add optional profile fields if provided
            if user_data.name:
                user_doc["name"] = user_data.name
            if user_data.organization:
                user_doc["organization"] = user_data.organization
            if user_data.job_title:
                user_doc["jobTitle"] = user_data.job_title
            if user_data.bio:
                user_doc["bio"] = user_data.bio
            if user_data.profile_image:
                user_doc["profileImage"] = str(user_data.profile_image)
            if user_data.location:
                user_doc["location"] = user_data.location
            if user_data.twitter:
                user_doc["twitter"] = user_data.twitter
            if user_data.linkedin:
                user_doc["linkedin"] = user_data.linkedin
            if user_data.github:
                user_doc["github"] = user_data.github
            
            # Create new user
            user_id = await self.user_repository.insert_user(user_doc)
            
            # Add ID to user document
            user_doc["_id"] = user_id
            
            return self._format_user_response(user_doc)
            
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise
            
    async def get_user(self, wallet_address: str) -> Optional[Dict[str, Any]]:
        """
        Get a user by wallet address.
        
        Args:
            wallet_address: The wallet address to look up
            
        Returns:
            User response if found, None otherwise
        """
        try:
            user = await self.user_repository.find_user(
                {"walletAddress": wallet_address}
            )
            
            if not user:
                # Return a "not found" response instead of None
                return {
                    "status": "error",
                    "message": "User not found",
                    "user": {
                        "id": "none",
                        "wallet_address": wallet_address,
                        "email": "none@example.com",  # Default for schema validation
                        "role": "user"
                    }
                }
                
            return self._format_user_response(user)
            
        except Exception as e:
            logger.error(f"Error getting user: {str(e)}")
            # Return a default response instead of raising an error
            return {
                "status": "error",
                "message": f"Error retrieving user: {str(e)}",
                "user": {
                    "id": "none",
                    "wallet_address": wallet_address,
                    "email": "none@example.com",  # Default for schema validation
                    "role": "user"
                }
            }
            
    async def update_user(
        self, 
        wallet_address: str, 
        update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a user's information.
        
        Args:
            wallet_address: The wallet address of the user to update
            update_data: The data to update
            
        Returns:
            Updated user response if successful, None otherwise
        """
        try:
            # Check if user exists
            existing_user = await self.user_repository.find_user(
                {"walletAddress": wallet_address}
            )
            
            if not existing_user:
                return None
                
            # Format update data for MongoDB (convert keys to camelCase)
            formatted_data = {}
            
            # Map snake_case keys to camelCase for MongoDB
            field_mapping = {
                "wallet_address": "walletAddress",
                "email": "email",
                "role": "role",
                "name": "name",
                "organization": "organization",
                "job_title": "jobTitle",
                "bio": "bio",
                "profile_image": "profileImage",
                "location": "location",
                "twitter": "twitter",
                "linkedin": "linkedin",
                "github": "github",
                "preferences": "preferences"
            }
            
            for key, value in update_data.items():
                if key in field_mapping:
                    # Convert profile_image URL to string if it's a URL object
                    if key == "profile_image" and value is not None:
                        formatted_data[field_mapping[key]] = str(value)
                    else:
                        formatted_data[field_mapping[key]] = value
                else:
                    # Pass through any fields not in the mapping
                    formatted_data[key] = value
            
            # Add update timestamp
            formatted_data["updatedAt"] = datetime.now(timezone.utc)
            
            # Update user
            updated = await self.user_repository.update_user(
                {"walletAddress": wallet_address},
                {"$set": formatted_data}
            )
            
            if not updated:
                return None
                
            # Get updated user
            updated_user = await self.user_repository.find_user(
                {"walletAddress": wallet_address}
            )
            
            return self._format_user_response(updated_user)
            
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            raise
            
    def _format_user_response(self, user_doc: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a user document into a standardized response.
        
        Args:
            user_doc: User document from MongoDB
            
        Returns:
            Formatted user response
        """
        # Create the base user response
        user_response = {
            "id": user_doc["_id"],
            "wallet_address": user_doc["walletAddress"],
            "email": user_doc["email"],
            "role": user_doc["role"]
        }
        
        # Add optional profile fields if they exist
        if "name" in user_doc:
            user_response["name"] = user_doc["name"]
        if "organization" in user_doc:
            user_response["organization"] = user_doc["organization"]
        if "jobTitle" in user_doc:
            user_response["job_title"] = user_doc["jobTitle"]
        if "bio" in user_doc:
            user_response["bio"] = user_doc["bio"]
        if "profileImage" in user_doc:
            user_response["profile_image"] = user_doc["profileImage"]
        if "location" in user_doc:
            user_response["location"] = user_doc["location"]
        if "twitter" in user_doc:
            user_response["twitter"] = user_doc["twitter"]
        if "linkedin" in user_doc:
            user_response["linkedin"] = user_doc["linkedin"]
        if "github" in user_doc:
            user_response["github"] = user_doc["github"]
        if "preferences" in user_doc:
            user_response["preferences"] = user_doc["preferences"]
            
        # Add timestamps if they exist
        if "createdAt" in user_doc:
            user_response["created_at"] = user_doc["createdAt"].isoformat() if isinstance(user_doc["createdAt"], datetime) else user_doc["createdAt"]
        if "lastLogin" in user_doc and user_doc["lastLogin"]:
            user_response["last_login"] = user_doc["lastLogin"].isoformat() if isinstance(user_doc["lastLogin"], datetime) else user_doc["lastLogin"]
            
        return {
            "status": "success",
            "user": user_response
        }
            
    async def update_last_login(self, wallet_address: str) -> bool:
        """
        Update a user's last login timestamp.
        
        Args:
            wallet_address: The wallet address of the user
            
        Returns:
            True if user was updated, False otherwise
        """
        try:
            return await self.user_repository.update_user(
                {"walletAddress": wallet_address},
                {"$set": {"lastLogin": datetime.now(timezone.utc)}}
            )
            
        except Exception as e:
            logger.error(f"Error updating last login: {str(e)}")
            raise
            
    async def get_users_by_role(self, role: str) -> List[UserResponse]:
        """
        Get users by role.
        
        Args:
            role: The role to filter by
            
        Returns:
            List of user responses
        """
        try:
            users = await self.user_repository.find_users({"role": role})
            
            return [
                UserResponse(
                    id=user["_id"],
                    wallet_address=user["walletAddress"],
                    email=user["email"],
                    role=user["role"]
                )
                for user in users
            ]
            
        except Exception as e:
            logger.error(f"Error getting users by role: {str(e)}")
            raise
            
    async def delete_user(self, wallet_address: str) -> bool:
        """
        Delete a user.
        
        Args:
            wallet_address: The wallet address of the user to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            return await self.user_repository.delete_user(
                {"walletAddress": wallet_address}
            )
            
        except Exception as e:
            logger.error(f"Error deleting user: {str(e)}")
            raise
