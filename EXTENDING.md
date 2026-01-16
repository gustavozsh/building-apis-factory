# Extending the API Factory

This guide shows how to add new endpoints and features to your API.

## Adding a New Endpoint

1. **Create a new module** (optional, for organization)
   ```python
   # src/routers/users.py
   from fastapi import APIRouter
   
   router = APIRouter(prefix="/users", tags=["users"])
   
   @router.get("/")
   async def list_users():
       return {"users": []}
   ```

2. **Include the router in main.py**
   ```python
   from src.routers import users
   
   app.include_router(users.router)
   ```

## Adding Database Support

1. **Add SQLAlchemy to requirements.txt**
   ```
   sqlalchemy==2.0.23
   alembic==1.13.1
   ```

2. **Create database configuration**
   ```python
   # src/database.py
   from sqlalchemy import create_engine
   from sqlalchemy.orm import sessionmaker
   
   DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./api.db")
   engine = create_engine(DATABASE_URL)
   SessionLocal = sessionmaker(bind=engine)
   ```

## Adding Authentication

1. **Add JWT dependencies**
   ```
   python-jose[cryptography]==3.3.0
   passlib[bcrypt]==1.7.4
   ```

2. **Implement authentication middleware**
   ```python
   from fastapi.security import OAuth2PasswordBearer
   
   oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
   ```

## Adding Background Tasks

```python
from fastapi import BackgroundTasks

def send_notification(email: str):
    # Send email logic
    pass

@app.post("/items/")
async def create_item(background_tasks: BackgroundTasks):
    background_tasks.add_task(send_notification, "user@example.com")
    return {"message": "Item created"}
```

## Environment Configuration

Create a `.env` file:
```
ENV=development
DATABASE_URL=postgresql://user:pass@localhost/dbname
SECRET_KEY=your-secret-key
API_KEY=your-api-key
```

Load with python-dotenv (already included).

## Testing New Endpoints

```python
# tests/test_users.py
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_list_users():
    response = client.get("/users/")
    assert response.status_code == 200
```

## Best Practices

1. **Use dependency injection** for database sessions
2. **Implement proper error handling**
3. **Add request validation** with Pydantic models
4. **Document endpoints** with docstrings
5. **Write tests** for all endpoints
6. **Use environment variables** for configuration
7. **Implement rate limiting** for production
8. **Add logging** for debugging and monitoring
