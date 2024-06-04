Twitter Clone API Documentation

Overview
This document provides details on the authentication and API endpoints available in the Twitter Clone application. The application uses JSON Web Tokens (JWT) for handling user authentication and securing access to various endpoints.

Authentication
The application uses JWT for authentication. The following endpoints are used for obtaining and refreshing tokens:

Obtain Token
URL: /auth/token/
Method: POST
Description: This endpoint is used for user login. It provides JWT access and refresh tokens upon successful authentication.
Data Params:
  username: User's username
  password: User's password
Success Response:
  Code: 200 OK
  Content: 
    {
      "refresh": "refresh_token_string",
      "access": "access_token_string"
    }
Error Response:
  Code: 401 Unauthorized
  Content: 
    {
      "detail": "No active account found with the given credentials"
    }

Refresh Token
URL: /auth/token/refresh/
Method: POST
Description: This endpoint is used to refresh the JWT access token using a refresh token.
Data Params:
  refresh: Refresh token
Success Response:
  Code: 200 OK
  Content: 
    {
      "access": "new_access_token_string"
    }
Error Response:
  Code: 401 Unauthorized
  Content: 
    {
      "detail": "Token is invalid or expired"
    }

User Registration
URL: /auth/register/
Method: POST
Description: Allows new users to register.
Data Params:
  username: Desired username
  email: User's email address
  password: Desired password
Success Response:
  Code: 201 Created
  Content: 
    {
      "username": "new_user",
      "email": "user@example.com"
    }
Error Response:
  Code: 400 Bad Request
  Content: 
    {
      "username": ["This field must be unique."]
    }

User Profile
URL: /auth/profile/
Method: GET
Description: Returns the profile information of the authenticated user along with the JWT token.
Headers:
  Authorization: Bearer {access_token}
Success Response:
  Code: 200 OK
  Content: 
    {
      "username": "user",
      "bio": "User biography"
    }
Error Response:
  Code: 401 Unauthorized
  Content: 
    {
      "detail": "Authentication credentials were not provided."
    }

Active Users
URL: /active-users/
Method: GET
Description: Lists the most active users based on the last login time.
Success Response:
  Code: 200 OK
  Content: 
    [
      {"username": "user1", "last_login": "2023-10-05T14:48:00Z"},
      {"username": "user2", "last_login": "2023-10-04T12:34:00Z"}
    ]
Error Response:
  Code: 401 Unauthorized
  Content: 
    {
      "detail": "Authentication credentials were not provided."
    }