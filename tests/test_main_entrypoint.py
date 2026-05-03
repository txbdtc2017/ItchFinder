import unittest
from unittest import mock

import main


class LocalPortSelectionTests(unittest.TestCase):
    def test_localhost_port_available_rejects_existing_localhost_listener(self):
        checker = getattr(main, "_localhost_port_available", None)
        self.assertIsNotNone(checker, "main._localhost_port_available should exist")

        with mock.patch("socket.create_connection") as connect:
            self.assertFalse(checker(8765))

        connect.assert_called_once_with(("localhost", 8765), timeout=0.2)

    def test_find_local_port_skips_ports_that_are_not_available_for_localhost(self):
        selector = getattr(main, "_find_local_port", None)
        self.assertIsNotNone(selector, "main._find_local_port should exist")

        with mock.patch.object(
            main,
            "_localhost_port_available",
            side_effect=[False, True],
        ) as available:
            self.assertEqual(selector(8000, max_attempts=2), 8001)

        self.assertEqual([call.args[0] for call in available.call_args_list], [8000, 8001])

    def test_find_local_port_reports_when_all_candidates_are_blocked(self):
        selector = getattr(main, "_find_local_port", None)
        self.assertIsNotNone(selector, "main._find_local_port should exist")

        with mock.patch.object(main, "_localhost_port_available", return_value=False):
            with self.assertRaises(RuntimeError) as ctx:
                selector(8000, max_attempts=2)

        self.assertIn("8000-8001", str(ctx.exception))

    def test_resolve_bind_address_defaults_to_localhost_with_auto_port(self):
        resolver = getattr(main, "_resolve_bind_address", None)
        self.assertIsNotNone(resolver, "main._resolve_bind_address should exist")

        with mock.patch.dict("os.environ", {}, clear=True):
            with mock.patch.object(main, "_find_local_port", return_value=8001) as find_port:
                self.assertEqual(resolver(), ("127.0.0.1", 8001))

        find_port.assert_called_once_with(8000)

    def test_resolve_bind_address_allows_container_bind_host_and_port(self):
        resolver = getattr(main, "_resolve_bind_address", None)
        self.assertIsNotNone(resolver, "main._resolve_bind_address should exist")

        with mock.patch.dict(
            "os.environ",
            {"ITCHFINDER_HOST": "0.0.0.0", "ITCHFINDER_PORT": "8000"},
            clear=True,
        ):
            with mock.patch.object(main, "_find_local_port") as find_port:
                self.assertEqual(resolver(), ("0.0.0.0", 8000))

        find_port.assert_not_called()

    def test_resolve_public_url_prefers_explicit_runtime_url(self):
        resolver = getattr(main, "_resolve_public_url", None)
        self.assertIsNotNone(resolver, "main._resolve_public_url should exist")

        with mock.patch.dict(
            "os.environ",
            {"ITCHFINDER_PUBLIC_URL": "http://127.0.0.1:18081"},
            clear=True,
        ):
            self.assertEqual(resolver("0.0.0.0", 8000), "http://127.0.0.1:18081")

    def test_resolve_public_url_maps_container_host_to_localhost(self):
        resolver = getattr(main, "_resolve_public_url", None)
        self.assertIsNotNone(resolver, "main._resolve_public_url should exist")

        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertEqual(resolver("0.0.0.0", 8000), "http://127.0.0.1:8000")
