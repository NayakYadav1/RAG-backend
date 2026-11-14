from unittest import TestCase
from unittest.mock import Mock, patch

from sqlalchemy.orm import Session

from app.services.booking import process_booking_turn


class BookingRoutingTests(TestCase):
    def test_unrelated_message_skips_gemini_classification(self) -> None:
        db = Mock(spec=Session)

        with (
            patch("app.services.booking._get_booking_state", return_value=None),
            patch("app.services.booking._extract_booking_turn") as extract_turn,
        ):
            result = process_booking_turn(
                db=db,
                session_id="test-session",
                message="What does the uploaded document say?",
            )

        self.assertIsNone(result)
        extract_turn.assert_not_called()