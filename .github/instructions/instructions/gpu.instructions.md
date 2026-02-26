---
description: "GPU computing patterns for AI/ML workloads"
applyTo: "**/*gpu*.py, **/*cuda*.py, **/*torch*.py, **/ml/**/*.py, **/training/**/*.py"
---

# GPU Integration Guidelines

## Overview

The project has on-premise GPU infrastructure for AI/ML workloads. This guide covers patterns for efficient GPU utilization.

## Current GPU Workloads

| Workload | Tool | GPU Usage |
|----------|------|-----------|
| Speech-to-Text | Whisper | High |
| Text Embeddings | Sentence Transformers | Medium |
| LLM Inference | Ollama | High |
| Data Processing | RAPIDS (optional) | Medium |

## Environment Setup

### Check GPU Availability

```python
import torch

def check_gpu():
    """Check GPU availability and print info."""
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        return True
    else:
        print("No GPU available, using CPU")
        return False

# Usage
HAS_GPU = check_gpu()
DEVICE = "cuda" if HAS_GPU else "cpu"
```

### Environment Variables

```bash
# .env file
CUDA_VISIBLE_DEVICES=0          # Which GPU to use (0, 1, etc.)
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512  # Memory optimization
OLLAMA_NUM_GPU=1                # For Ollama models
```

## Whisper Transcription

### Basic Usage

```python
import whisper
from pathlib import Path
from loguru import logger

def transcribe_audio(audio_path: str, model_size: str = "base") -> dict:
    """
    Transcribe audio using Whisper.
    
    Args:
        audio_path: Path to audio file (mp3, wav, m4a)
        model_size: tiny, base, small, medium, large
    
    Returns:
        Dict with 'text' and 'segments'
    """
    logger.info(f"Loading Whisper model: {model_size}")
    model = whisper.load_model(model_size)
    
    logger.info(f"Transcribing: {audio_path}")
    result = model.transcribe(
        audio_path,
        language="en",  # Force English
        verbose=False
    )
    
    return {
        'text': result['text'],
        'segments': result['segments'],
        'language': result['language']
    }

# Model size guide:
# - tiny:   ~1GB VRAM, fastest, lowest accuracy
# - base:   ~1GB VRAM, good balance for short audio
# - small:  ~2GB VRAM, better accuracy
# - medium: ~5GB VRAM, good for complex audio
# - large:  ~10GB VRAM, best accuracy, slowest
```

### Batch Processing

```python
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import whisper

class BatchTranscriber:
    """Batch audio transcription with GPU optimization."""
    
    def __init__(self, model_size: str = "base"):
        self.model = whisper.load_model(model_size)
    
    def transcribe_folder(self, folder: str, extensions: list = ['.mp3', '.wav']) -> list:
        """Transcribe all audio files in folder."""
        results = []
        files = [f for f in Path(folder).iterdir() 
                 if f.suffix.lower() in extensions]
        
        for audio_file in files:
            try:
                result = self.model.transcribe(str(audio_file))
                results.append({
                    'file': audio_file.name,
                    'text': result['text'],
                    'status': 'success'
                })
            except Exception as e:
                results.append({
                    'file': audio_file.name,
                    'error': str(e),
                    'status': 'failed'
                })
        
        return results
```

## Text Embeddings

### Sentence Transformers

```python
from sentence_transformers import SentenceTransformer
import numpy as np

class EmbeddingService:
    """Generate text embeddings using GPU."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        # Model will auto-use GPU if available
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
    
    def embed_texts(self, texts: list) -> np.ndarray:
        """Generate embeddings for list of texts."""
        return self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=True,
            convert_to_numpy=True
        )
    
    def embed_single(self, text: str) -> np.ndarray:
        """Generate embedding for single text."""
        return self.model.encode(text)

# Model recommendations:
# - all-MiniLM-L6-v2: Fast, 384 dims, good general purpose
# - all-mpnet-base-v2: Better quality, 768 dims
# - multi-qa-MiniLM-L6-cos-v1: Optimized for Q&A
```

## Ollama (Local LLM)

### Configuration

```bash
# Install Ollama
curl https://ollama.ai/install.sh | sh

# Pull models
ollama pull llama2
ollama pull codellama
ollama pull mistral
```

### Python Integration

```python
import requests
from typing import Generator

class OllamaClient:
    """Client for local Ollama LLM inference."""
    
    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host
    
    def generate(self, prompt: str, model: str = "llama2") -> str:
        """Generate response from LLM."""
        response = requests.post(
            f"{self.host}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            }
        )
        response.raise_for_status()
        return response.json()['response']
    
    def generate_stream(self, prompt: str, model: str = "llama2") -> Generator:
        """Stream response from LLM."""
        response = requests.post(
            f"{self.host}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": True
            },
            stream=True
        )
        
        for line in response.iter_lines():
            if line:
                import json
                data = json.loads(line)
                yield data.get('response', '')
    
    def list_models(self) -> list:
        """List available models."""
        response = requests.get(f"{self.host}/api/tags")
        return [m['name'] for m in response.json().get('models', [])]

# Usage
client = OllamaClient()
response = client.generate("Summarize this complaint: ...")
```

## GPU Memory Management

### Clearing GPU Memory

```python
import torch
import gc

def clear_gpu_memory():
    """Clear GPU memory after model use."""
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        gc.collect()

# Use after intensive operations
model = whisper.load_model("large")
result = model.transcribe(audio_path)
del model
clear_gpu_memory()
```

### Memory-Efficient Loading

```python
import torch

# Load model with lower precision for memory savings
model = whisper.load_model("medium").half()  # FP16

# Or use CPU offloading for large models
model = whisper.load_model(
    "large",
    device="cpu"  # Load to CPU first
).to("cuda")  # Then move to GPU as needed
```

## CPU Fallback Pattern

```python
import torch

class HybridProcessor:
    """Processor that gracefully falls back to CPU."""
    
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
    
    def load_model(self, model_name: str):
        """Load model to appropriate device."""
        try:
            self.model = self._load_to_gpu(model_name)
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                print("GPU OOM, falling back to CPU")
                torch.cuda.empty_cache()
                self.device = "cpu"
                self.model = self._load_to_cpu(model_name)
            else:
                raise
    
    def _load_to_gpu(self, model_name):
        return whisper.load_model(model_name, device="cuda")
    
    def _load_to_cpu(self, model_name):
        return whisper.load_model(model_name, device="cpu")
```

## Performance Optimization

### Batch Size Tuning

```python
# Find optimal batch size for your GPU
def find_optimal_batch_size(model, sample_input):
    """Binary search for optimal batch size."""
    min_batch = 1
    max_batch = 256
    optimal = 1
    
    while min_batch <= max_batch:
        batch_size = (min_batch + max_batch) // 2
        try:
            batch = [sample_input] * batch_size
            model.encode(batch)
            optimal = batch_size
            min_batch = batch_size + 1
        except RuntimeError:
            torch.cuda.empty_cache()
            max_batch = batch_size - 1
    
    return optimal
```

### Mixed Precision Training

```python
from torch.cuda.amp import autocast, GradScaler

scaler = GradScaler()

for batch in dataloader:
    optimizer.zero_grad()
    
    with autocast():  # FP16 forward pass
        output = model(batch)
        loss = criterion(output)
    
    scaler.scale(loss).backward()  # Scaled backward pass
    scaler.step(optimizer)
    scaler.update()
```

## Monitoring

### GPU Utilization Check

```python
import subprocess

def get_gpu_status() -> dict:
    """Get current GPU status."""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=utilization.gpu,memory.used,memory.total',
             '--format=csv,noheader,nounits'],
            capture_output=True, text=True
        )
        parts = result.stdout.strip().split(', ')
        return {
            'utilization_pct': int(parts[0]),
            'memory_used_mb': int(parts[1]),
            'memory_total_mb': int(parts[2]),
            'memory_used_pct': int(parts[1]) / int(parts[2]) * 100
        }
    except Exception:
        return {'error': 'nvidia-smi not available'}

# Usage
status = get_gpu_status()
if status.get('memory_used_pct', 0) > 90:
    print("Warning: GPU memory nearly full")
```

## Dependencies

```txt
# GPU/CUDA packages
torch>=2.0.0
torchaudio>=2.0.0

# AI/ML models
openai-whisper>=20231117
sentence-transformers>=2.2.0

# Monitoring
nvidia-ml-py3>=7.352.0
```

## Related Resources

- `@data-engineer` - Data pipelines with GPU processing
- `python.instructions.md` - Python coding standards

---

## Project Defaults

> Read `project-config.md` to resolve placeholder values.
