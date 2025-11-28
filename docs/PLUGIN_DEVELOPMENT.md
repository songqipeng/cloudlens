# Plugin Development Guide

## Overview

CloudLens supports a plugin-based architecture that allows third-party developers to extend the CLI with custom resource analyzers for new cloud providers or resource types.

## Plugin Architecture

Plugins are discovered via Python's `entry_points` mechanism and loaded automatically at startup.

## Creating a Plugin

### 1. Project Structure

```
cloudlens-aws/
├── cloudlens_aws/
│   ├── __init__.py
│   ├── ec2_analyzer.py
│   └── s3_analyzer.py
├── setup.py
└── README.md
```

### 2. Implement Analyzer

Your analyzer must inherit from `BaseResourceAnalyzer`:

```python
from core.base_analyzer import BaseResourceAnalyzer
from core.analyzer_registry import AnalyzerRegistry

@AnalyzerRegistry.register(
    resource_type="ec2",
    display_name="AWS EC2",
    emoji="🖥️"
)
class EC2Analyzer(BaseResourceAnalyzer):
    def get_resource_type(self) -> str:
        return "ec2"
    
    def get_all_regions(self) -> list:
        return ["us-east-1", "us-west-2", "eu-west-1"]
    
    def get_instances(self, region: str) -> list:
        # Call AWS SDK to fetch EC2 instances
        return []
    
    def get_metrics(self, instance_id: str, region: str) -> dict:
        # Fetch CloudWatch metrics
        return {}
    
    def is_idle(self, instance_id: str, region: str, days: int = 7) -> bool:
        # Implement idle detection logic
        return False
```

### 3. Configure setup.py

```python
from setuptools import setup, find_packages

setup(
    name="cloudlens-aws",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "cloudlens>=1.0.0",
        "boto3>=1.20.0"
    ],
    entry_points={
        "cloudlens.analyzers": [
            "ec2 = cloudlens_aws.ec2_analyzer:EC2Analyzer",
            "s3 = cloudlens_aws.s3_analyzer:S3Analyzer"
        ]
    }
)
```

### 4. Install Plugin

```bash
pip install cloudlens-aws
```

The plugin will be automatically discovered and loaded by CloudLens.

## Testing Your Plugin

```bash
# List all registered analyzers (should include your plugin)
cl query --help

# Test query
cl query ec2 --account myaccount
```

## Best Practices

1. **Error Handling**: Always wrap API calls in try-except blocks
2. **Rate Limiting**: Respect cloud provider API rate limits
3. **Caching**: Consider using `CacheManager` for frequently accessed data
4. **Documentation**: Provide clear README with setup instructions
5. **Testing**: Include unit tests and integration tests

## Example Plugins

- `cloudlens-aws`: AWS EC2, S3, RDS support
- `cloudlens-gcp`: Google Cloud Compute, Storage support
- `cloudlens-azure`: Azure VM, Blob Storage support

## Publishing

Publish your plugin to PyPI:

```bash
python setup.py sdist bdist_wheel
twine upload dist/*
```

Users can then install via:

```bash
pip install cloudlens-aws
```
