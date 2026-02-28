import os

from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "https://hackapizza.datapizza.tech")
TEAM_ID = int(os.getenv("TEAM_ID", "0"))
TEAM_API_KEY = os.getenv("TEAM_API_KEY", "")
REGOLO_API_KEY = os.getenv("REGOLO_API_KEY", "")

if TEAM_ID <= 0:
    raise SystemExit("Set TEAM_ID environment variable")

if not TEAM_API_KEY:
    raise SystemExit("Set TEAM_API_KEY environment variable")

if not REGOLO_API_KEY:
    raise SystemExit("Set REGOLO_API_KEY environment variable")