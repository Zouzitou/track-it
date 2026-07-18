from pathlib import Path

APP_NAME = "Track it"
APP_ID = "TrackIt"
ORGANIZATION = "TrackItOpenSource"
PROJECT_SUFFIX = ".trackit"
SCHEMA_VERSION = 1
MASK_CHUNK_SIZE = 32
PROXY_MAX_SIDE = 1280
PROXY_JPEG_QUALITY = 92
PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
ASSET_ROOT = REPOSITORY_ROOT / "assets"
