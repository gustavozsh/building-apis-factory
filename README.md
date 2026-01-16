# Building APIs Factory

A comprehensive factory for building and deploying cloud-ready APIs. This repository provides a standardized structure and tooling for developing high-quality APIs that can be easily deployed to major cloud platforms (AWS, Azure, Google Cloud).

## Features

- 🚀 **FastAPI Framework** - Modern, fast Python web framework
- 🐳 **Docker Support** - Containerized for easy deployment
- ☁️ **Multi-Cloud Ready** - Configurations for AWS, Azure, and GCP
- 🧪 **Testing Suite** - Comprehensive test coverage with pytest
- 🔄 **CI/CD Pipeline** - Automated testing and deployment with GitHub Actions
- 📊 **Health Monitoring** - Built-in health check endpoints
- 🔒 **CORS Enabled** - Ready for cross-origin requests

## Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/gustavozsh/building-apis-factory.git
   cd building-apis-factory
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the API**
   ```bash
   uvicorn src.main:app --reload
   ```

5. **Access the API**
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - Alternative docs: http://localhost:8000/redoc

### Using Docker

1. **Build the Docker image**
   ```bash
   docker build -t building-apis-factory .
   ```

2. **Run the container**
   ```bash
   docker run -p 8000:8000 building-apis-factory
   ```

### Using Docker Compose

```bash
docker-compose up
```

## API Endpoints

- `GET /` - Welcome message
- `GET /health` - Health check endpoint for monitoring
- `GET /api/info` - API information and features

## Testing

Run tests with pytest:

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ --cov=src --cov-report=term-missing
```

## Cloud Deployment

This API is ready for deployment to major cloud platforms:

### AWS
- **ECS (Elastic Container Service)** - Recommended for production
- **Lambda** - Serverless option
- **EC2** - Traditional VM deployment

See [cloud/AWS.md](cloud/AWS.md) for detailed instructions.

### Azure
- **Container Instances** - Quick deployment
- **App Service** - Managed platform
- **AKS** - Kubernetes option

See [cloud/AZURE.md](cloud/AZURE.md) for detailed instructions.

### Google Cloud Platform
- **Cloud Run** - Recommended (easiest)
- **GKE** - Kubernetes option
- **Compute Engine** - VM deployment

See [cloud/GCP.md](cloud/GCP.md) for detailed instructions.

## Project Structure

```
building-apis-factory/
├── src/                    # Source code
│   ├── __init__.py
│   └── main.py            # Main FastAPI application
├── tests/                 # Test suite
│   ├── __init__.py
│   └── test_main.py
├── cloud/                 # Cloud deployment configurations
│   ├── AWS.md
│   ├── AZURE.md
│   ├── GCP.md
│   ├── ecs-task-definition.json
│   ├── k8s-deployment.yaml
│   └── k8s-service.yaml
├── .github/
│   └── workflows/
│       └── ci-cd.yml      # CI/CD pipeline
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose configuration
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development dependencies
├── .gitignore
└── README.md
```

## Development

### Code Style

This project follows Python best practices:
- PEP 8 style guide
- Type hints where appropriate
- Comprehensive docstrings

### Linting

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run flake8
flake8 src/ tests/

# Format with black
black src/ tests/
```

## CI/CD

The project includes a GitHub Actions workflow that:
- Runs tests on every push and pull request
- Builds Docker images
- Tests containerized application
- Can be extended for automatic deployment

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License - See [LICENSE](LICENSE) file for details

## Support

For issues and questions, please open an issue on GitHub.