# Model management

Weights are external and downloaded only by explicit action. Downloads use HTTPS, resumable
`.partial` files, a file lock, byte progress, minimum-size validation, SHA-256 recording, and
atomic replacement. CPU or under 4 GB selects Tiny; 4–9 GB Small; 10–15 GB Base+; 16 GB or more
Large. An 8 GB device never holds SAM 2 and optional Cutie simultaneously.
