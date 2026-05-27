import os

# Force all hardware to mock mode before any app imports
os.environ["RPI_MOCK"] = "1"

import pytest
from app.config import load_settings, Settings
from app.state import AgentState


@pytest.fixture
def settings() -> Settings:
    return load_settings()


@pytest.fixture
def fresh_state() -> AgentState:
    return AgentState()
