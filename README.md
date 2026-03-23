# EXAM PORTAL - High Performance FastAPI Structure

This project provides a professional, production-ready structure for a FastAPI application.

## Key Features
- **FastAPI**: Modern, high-performance web framework for Python.
- **Pydantic V2**: Type-safe settings and data validation.
- **Asynchronous**: Built to handle asynchronous requests for high concurrency.
- **V1 API Versioning**: Pre-configured structure for versioning.
- **CORS Middleware**: Pre-configured for cross-origin resource sharing.

## Setup Instructions

### 1. Create a Virtual Environment (Optional but Recommended)
```bash
python -m venv venv
source venv/bin/activate  # On Linux/macOS
# OR
.\venv\Scripts\activate     # On Windows
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the Application
```bash
uvicorn app.main:app --reload
```

## API Access
- **Welcome Page**: [http://localhost:8000/](http://localhost:8000/)
- **Hello World**: [http://localhost:8000/api/v1/hello/](http://localhost:8000/api/v1/hello/)
- **Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
