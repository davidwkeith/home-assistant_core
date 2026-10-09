"""Tests for the EcoNet integration setup."""

from unittest.mock import AsyncMock, MagicMock, patch

from aiohttp import ClientError
from pyeconet.equipment import EquipmentType
from pyeconet.errors import PyeconetError
import pytest

from homeassistant.components.econet.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


@pytest.mark.parametrize(
    "exception",
    [
        pytest.param(PyeconetError(), id="library_error"),
        pytest.param(ClientError("certificate has expired"), id="client_error"),
    ],
)
async def test_login_error_retries_setup(
    hass: HomeAssistant, exception: Exception
) -> None:
    """Test setup is retried when logging in fails."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_EMAIL: "admin@localhost.com", CONF_PASSWORD: "password0"},
    )
    entry.add_to_hass(hass)

    with patch("pyeconet.EcoNetApiInterface.login", side_effect=exception):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_subscribe_runs_in_executor(hass: HomeAssistant) -> None:
    """Test the blocking MQTT subscribe is run in the executor."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_EMAIL: "admin@localhost.com", CONF_PASSWORD: "password0"},
    )
    entry.add_to_hass(hass)

    api = MagicMock()
    api.get_equipment_by_type = AsyncMock(
        return_value={EquipmentType.WATER_HEATER: [], EquipmentType.THERMOSTAT: []}
    )

    with (
        patch("pyeconet.EcoNetApiInterface.login", return_value=api),
        patch.object(
            hass, "async_add_executor_job", wraps=hass.async_add_executor_job
        ) as mock_executor_job,
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    mock_executor_job.assert_any_call(api.subscribe)
    api.subscribe.assert_called_once_with()
