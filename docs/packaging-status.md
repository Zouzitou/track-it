# Packaging verification status

Windows standalone packaging was attempted twice on 2026-07-18 with Nuitka 2.8.10,
Python 3.11.15, PySide6 6.11.1, and PyTorch 2.12.1+cu130.

The first attempt ran for 903 seconds and failed inside Nuitka's optimizer while analyzing
`torch._dynamo.pgo` (`NuitkaOptimizationError: This statement does raise but didn't annotate an
exception exit`). The compiler generated `nuitka-crash-report.xml`; that generated diagnostic is
excluded from source control and contains local build paths.

The second attempt explicitly disabled Torch JIT and excluded unused `torch._dynamo`,
`torch._inductor`, and `torch.distributed` modules. It remained active for 1,204 seconds without
producing a completed executable and was terminated at the command's 20-minute ceiling; the
remaining child compiler processes were verified by command line and stopped.

No portable ZIP or checksum is claimed. The build script retains the narrowed workaround and
strictly checks native exit codes. Release automation is configured to produce the artifact on a
GitHub Windows runner; the prerelease must remain draft until that workflow completes and the
packaged self-test passes.
