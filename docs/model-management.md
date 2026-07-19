# Model management

Weights are external. The first press of **Create green screen** downloads the verified 176 MB
SAM 2.1 Small checkpoint after the UI discloses this first-run requirement. Downloads use HTTPS,
resumable `.partial` files, a file lock, exact byte bounds, a pinned SHA-256 digest, and atomic
replacement. Later runs verify and reuse the local checkpoint. CUDA is used when the active
PyTorch runtime supports it; otherwise processing runs on CPU.
