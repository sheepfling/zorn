from __future__ import annotations

import unittest

from zorn.__main__ import main


class SmokeTest(unittest.TestCase):
    def test_cli_main_returns_success(self) -> None:
        self.assertEqual(main(), 0)


if __name__ == "__main__":
    unittest.main()
