# Troubleshooting

- **FFmpeg not found:** install FFmpeg or choose its folder in Settings.
- **Video moved:** relink the original file; Track it validates its fingerprint before attaching.
- **GPU out of memory:** completed masks remain saved while resolution is lowered once, followed
  by one smaller-model fallback.
- **Model verification failed:** delete the checkpoint and download it again.
- **CUDA unavailable:** run diagnostics and verify a stable official PyTorch CUDA wheel and driver.
