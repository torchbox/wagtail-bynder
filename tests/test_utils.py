from unittest import mock

from django.test import SimpleTestCase

from wagtail_bynder.exceptions import BynderAssetDownloadError
from wagtail_bynder.utils import download_file


class DownloadFileTests(SimpleTestCase):
    """Tests for the download_file function's error handling"""

    def test_download_file_raises_error_on_non_200_status(self):
        """Test that download_file raises BynderAssetDownloadError for non-200 status codes"""
        mock_response = mock.Mock()
        mock_response.status_code = 502

        with (
            mock.patch("wagtail_bynder.utils.requests.get", return_value=mock_response),
            self.assertRaises(BynderAssetDownloadError) as cm,
        ):
            download_file("https://example.com/file.jpg", 5242880, "TEST_SETTING")

        # Verify error message includes filename
        self.assertIn("file.jpg", str(cm.exception))
        self.assertIn("Server error downloading", str(cm.exception))

    def test_download_file_raises_error_on_empty_response(self):
        """Test that download_file raises BynderAssetDownloadError for successful-but-empty responses"""
        mock_response = mock.Mock()
        mock_response.status_code = 200
        # Mock iter_content to return no chunks (empty file)
        mock_response.iter_content = mock.Mock(return_value=[])

        with (
            mock.patch("wagtail_bynder.utils.requests.get", return_value=mock_response),
            self.assertRaises(BynderAssetDownloadError) as cm,
        ):
            download_file("https://example.com/empty.jpg", 5242880, "TEST_SETTING")

        self.assertIn("empty.jpg", str(cm.exception))
        self.assertIn("empty", str(cm.exception).lower())

    def test_download_file_succeeds_on_200(self):
        """Test that download_file works correctly with 200 status"""
        mock_response = mock.Mock()
        mock_response.status_code = 200
        # Mock iter_content to return chunks
        mock_response.iter_content = mock.Mock(return_value=[b"test ", b"data"])

        with mock.patch(
            "wagtail_bynder.utils.requests.get", return_value=mock_response
        ):
            result = download_file(
                "https://example.com/good.jpg", 5242880, "TEST_SETTING"
            )

        # Should return an InMemoryUploadedFile
        self.assertEqual(result.name, "good.jpg")
        self.assertGreater(result.size, 0)
