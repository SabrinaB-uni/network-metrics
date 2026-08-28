"""Hands back the Aruba client the rest of the app uses (the live API client)."""
from .live import LiveArubaClient


def get_client():
    return LiveArubaClient()
