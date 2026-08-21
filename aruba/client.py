import config
from .mock import MockArubaClient
from .live import LiveArubaClient


def get_client():
    return MockArubaClient() if config.USE_MOCK else LiveArubaClient()
