"""Compute device selection shared by embedding and reranking models."""


def get_compute_device() -> str:
    """Prefer Apple MPS, then CUDA, and fall back to CPU."""
    import torch

    mps_backend = getattr(torch.backends, "mps", None)
    if mps_backend is not None and mps_backend.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"
