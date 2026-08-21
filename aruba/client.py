"""
Factory that returns the right Aruba client based on config.

Everything else in the app calls `get_client()` and never imports the mock or
live class directly — so flipping USE_MOCK in .env switches the whole app.
"""
import config
from .mock import MockArubaClient
from .live import LiveArubaClient


def get_client():
    return MockArubaClient() if config.USE_MOCK else LiveArubaClient()
