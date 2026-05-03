from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DockerConfigTests(unittest.TestCase):
    def test_docker_files_define_local_compose_runtime(self):
        dockerfile = ROOT / "Dockerfile"
        compose = ROOT / "docker-compose.yml"
        dockerignore = ROOT / ".dockerignore"

        self.assertTrue(dockerfile.exists(), "Dockerfile should exist")
        self.assertTrue(compose.exists(), "docker-compose.yml should exist")
        self.assertTrue(dockerignore.exists(), ".dockerignore should exist")

        dockerfile_text = dockerfile.read_text()
        compose_text = compose.read_text()
        dockerignore_text = dockerignore.read_text()

        self.assertIn("python:3.11-slim", dockerfile_text)
        self.assertIn('CMD ["python", "main.py"]', dockerfile_text)

        self.assertIn("itchfinder", compose_text)
        self.assertIn('"18081:8000"', compose_text)
        self.assertIn("ITCHFINDER_HOST=0.0.0.0", compose_text)
        self.assertIn("ITCHFINDER_PORT=8000", compose_text)
        self.assertIn("ITCHFINDER_PUBLIC_URL=http://127.0.0.1:18081", compose_text)
        self.assertIn("env_file:", compose_text)
        self.assertIn(".env", compose_text)
        self.assertIn(".:/app", compose_text)

        self.assertIn(".venv/", dockerignore_text)
        self.assertIn("data.db*", dockerignore_text)
