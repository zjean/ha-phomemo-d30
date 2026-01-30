"""Pytest fixtures for tests."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def hass(event_loop):
    """Provide a mock Home Assistant instance."""
    hass_mock = MagicMock()
    hass_mock.data = {}
    hass_mock.loop = event_loop

    # Mock config entries
    hass_mock.config_entries = MagicMock()
    hass_mock.config_entries.flow = MagicMock()
    # Initialize fresh _mock_entries for each test
    hass_mock.config_entries._mock_entries = []

    # Create flow manager mock
    flow_manager = MagicMock()
    flows = {}

    async def async_init(domain, context):
        """Mock async_init."""
        from custom_components.phomemo_d30 import config_flow
        from homeassistant.data_entry_flow import FlowResultType

        flow = config_flow.PhomemoConfigFlow()
        flow.hass = hass_mock
        flow.context = context
        flow.flow_id = str(len(flows))
        flow.handler = domain  # Set the domain as handler

        # The ConfigFlow base class methods will use hass.config_entries
        # Ensure hass.config_entries.async_entries works properly
        def async_entries_impl(domain_filter):
            """Return entries for domain."""
            return [e for e in hass_mock.config_entries._mock_entries if e.domain == domain_filter]

        def async_entry_for_domain_unique_id_impl(domain_filter, unique_id):
            """Return entry for domain and unique_id."""
            for entry in hass_mock.config_entries._mock_entries:
                if entry.domain == domain_filter and getattr(entry, 'unique_id', None) == unique_id:
                    return entry
            return None

        hass_mock.config_entries.async_entries = async_entries_impl
        hass_mock.config_entries.async_entry_for_domain_unique_id = async_entry_for_domain_unique_id_impl

        flow_id = str(len(flows))
        flows[flow_id] = flow
        result = await flow.async_step_user()
        result["flow_id"] = flow_id
        return result

    async def async_configure(flow_id, user_input):
        """Mock async_configure."""
        from homeassistant.data_entry_flow import FlowResultType

        flow = flows.get(flow_id)
        if not flow:
            raise ValueError(f"Flow {flow_id} not found")

        # Get the last result to determine which step we're on
        if not hasattr(flow, "_last_step"):
            flow._last_step = "user"

        # Determine which step method to call based on current step
        result = None
        try:
            if flow._last_step == "user":
                # After user step, call the appropriate mode-specific step
                if "mode" in user_input:
                    mode = user_input["mode"]
                    if mode == "mock":
                        result = await flow.async_step_mock()
                        flow._last_step = "mock"
                    elif mode == "bluetooth":
                        result = await flow.async_step_bluetooth_discovery()
                        # Discovery internally calls and returns bluetooth step
                        flow._last_step = "bluetooth"
                else:
                    result = await flow.async_step_user(user_input)
            elif flow._last_step == "mock":
                # Final mock configuration step
                result = await flow.async_step_mock(user_input)
            elif flow._last_step == "bluetooth":
                # Final bluetooth configuration step
                result = await flow.async_step_bluetooth(user_input)
            else:
                result = await flow.async_step_user(user_input)
        except Exception as e:
            # Check if it's an AbortFlow exception
            if hasattr(e, 'reason'):
                result = {"type": FlowResultType.ABORT, "reason": e.reason}
            else:
                raise

        if "flow_id" not in result or result.get("flow_id") is None:
            result["flow_id"] = flow_id
        return result

    flow_manager.async_init = async_init
    flow_manager.async_configure = async_configure

    hass_mock.config_entries.flow = flow_manager

    async def async_block_till_done():
        """Mock block till done."""
        await asyncio.sleep(0.01)

    hass_mock.async_block_till_done = async_block_till_done
    hass_mock.async_create_task = lambda coro: asyncio.create_task(coro)

    return hass_mock
