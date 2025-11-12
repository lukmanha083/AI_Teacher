#!/usr/bin/env python3
"""
Verify AI Teacher POC Setup
Checks that all dependencies and databases are properly installed
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_python_version():
    """Check Python version >= 3.10"""
    print("Checking Python version...")
    if sys.version_info < (3, 10):
        print(f"  ✗ Python {sys.version_info.major}.{sys.version_info.minor} found")
        print(f"  ✓ Python 3.10+ required")
        return False
    print(f"  ✓ Python {sys.version_info.major}.{sys.version_info.minor}")
    return True


def check_dependencies():
    """Check required Python packages"""
    print("\nChecking Python dependencies...")

    packages = {
        "duckdb": "DuckDB database",
        "neo4j": "Neo4j driver",
        "langchain": "LangChain",
        "llama_index": "LlamaIndex",
        "requests": "HTTP requests",
        "pydantic": "Pydantic",
        "pydantic_settings": "Pydantic Settings",
        "loguru": "Loguru logger",
        "numpy": "NumPy",
    }

    all_ok = True
    for package, description in packages.items():
        try:
            __import__(package)
            print(f"  ✓ {description} ({package})")
        except ImportError:
            print(f"  ✗ {description} ({package}) - NOT INSTALLED")
            all_ok = False

    return all_ok


def check_duckdb_vss():
    """Check DuckDB VSS extension"""
    print("\nChecking DuckDB VSS extension...")
    try:
        import duckdb

        conn = duckdb.connect(":memory:")

        # Try to install and load vss
        try:
            conn.execute("INSTALL vss;")
            conn.execute("LOAD vss;")
            print("  ✓ VSS extension installed and loaded")
            conn.close()
            return True
        except Exception as e:
            print(f"  ✗ VSS extension failed: {e}")
            conn.close()
            return False

    except ImportError:
        print("  ✗ DuckDB not installed")
        return False


def check_neo4j_connection():
    """Check Neo4j connection"""
    print("\nChecking Neo4j connection...")
    try:
        from neo4j import GraphDatabase

        # Try to connect to Neo4j
        try:
            driver = GraphDatabase.driver(
                "bolt://localhost:7687", auth=("neo4j", "password")
            )

            # Test connection
            with driver.session() as session:
                result = session.run("RETURN 1 as test")
                _ = result.single()

            driver.close()
            print("  ✓ Neo4j connection successful")
            print("  ✓ Using default credentials (neo4j/password)")
            return True

        except Exception as e:
            print(f"  ⚠ Neo4j connection failed: {e}")
            print("  ℹ Make sure Neo4j is running:")
            print("    FreeBSD: service neo4j start")
            print("    Docker: docker run -p 7474:7474 -p 7687:7687 neo4j")
            return False

    except ImportError:
        print("  ✗ Neo4j Python driver not installed")
        return False


def check_directories():
    """Check project directories exist"""
    print("\nChecking project directories...")

    project_root = Path(__file__).parent.parent
    directories = [
        "config",
        "src/llm",
        "src/rag",
        "src/graph",
        "src/memory",
        "data/models",
        "data/textbooks",
        "data/databases",
        "data/embeddings",
        "docs/setup",
        "tests/unit",
        "scripts",
    ]

    all_ok = True
    for directory in directories:
        path = project_root / directory
        if path.exists():
            print(f"  ✓ {directory}/")
        else:
            print(f"  ✗ {directory}/ - NOT FOUND")
            all_ok = False

    return all_ok


def check_config_files():
    """Check configuration files"""
    print("\nChecking configuration files...")

    project_root = Path(__file__).parent.parent
    files = {
        ".env.example": "Environment variables template",
        "requirements.txt": "Python dependencies",
        "config/settings.py": "Configuration module",
        "src/rag/duckdb_store.py": "DuckDB vector store",
        "src/llm/client.py": "LLM client",
    }

    all_ok = True
    for file_path, description in files.items():
        path = project_root / file_path
        if path.exists():
            print(f"  ✓ {description} ({file_path})")
        else:
            print(f"  ✗ {description} ({file_path}) - NOT FOUND")
            all_ok = False

    # Check if .env exists
    env_path = project_root / ".env"
    if env_path.exists():
        print(f"  ✓ .env file exists")
    else:
        print(f"  ⚠ .env file not found (copy from .env.example)")

    return all_ok


def check_llama_server():
    """Check llama-server connection"""
    print("\nChecking llama-server connection...")
    try:
        import requests

        # Try to connect to llama-server
        try:
            response = requests.get("http://localhost:8080/health", timeout=5)
            if response.status_code == 200:
                print("  ✓ llama-server is running")
                return True
            else:
                print(f"  ⚠ llama-server returned status {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"  ⚠ llama-server not reachable: {e}")
            print("  ℹ Start llama-server:")
            print("    ./llama-server -m models/model.gguf --host 0.0.0.0 --no-webui")
            return False

    except ImportError:
        print("  ✗ requests library not installed")
        return False


def test_duckdb_vector_store():
    """Test DuckDB vector store"""
    print("\nTesting DuckDB vector store...")
    try:
        import sys
        from pathlib import Path
        import numpy as np

        # Import the vector store
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from src.rag.duckdb_store import DuckDBVectorStore

        # Create test database in memory
        store = DuckDBVectorStore(":memory:")

        # Insert test document
        test_embedding = np.random.rand(768).tolist()
        doc_id = store.insert(
            content="Test document",
            embedding=test_embedding,
            metadata={"subject": "Test", "grade": 8},
        )

        # Search
        query_embedding = np.random.rand(768).tolist()
        results = store.search(query_embedding, k=1)

        store.close()

        if len(results) > 0:
            print("  ✓ DuckDB vector store working")
            return True
        else:
            print("  ✗ DuckDB vector store search failed")
            return False

    except Exception as e:
        print(f"  ✗ DuckDB vector store test failed: {e}")
        return False


def main():
    """Run all checks"""
    print("=" * 60)
    print("AI Teacher POC Setup Verification")
    print("=" * 60)

    checks = [
        ("Python Version", check_python_version),
        ("Python Dependencies", check_dependencies),
        ("DuckDB VSS Extension", check_duckdb_vss),
        ("Neo4j Connection", check_neo4j_connection),
        ("Project Directories", check_directories),
        ("Configuration Files", check_config_files),
        ("llama-server Connection", check_llama_server),
        ("DuckDB Vector Store", test_duckdb_vector_store),
    ]

    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"  ✗ Unexpected error: {e}")
            results[name] = False

    # Summary
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status:8} {name}")

    print(f"\nTotal: {passed}/{total} checks passed")

    if passed == total:
        print("\n✓ All checks passed! Setup is complete.")
        return 0
    else:
        print("\n⚠ Some checks failed. Please review the errors above.")
        print("\nNext steps:")
        print("  1. Install missing dependencies: pip install -r requirements.txt")
        print("  2. Copy .env.example to .env and configure")
        print("  3. Start Neo4j: service neo4j start (FreeBSD)")
        print("  4. Start llama-server with a model")
        return 1


if __name__ == "__main__":
    sys.exit(main())
