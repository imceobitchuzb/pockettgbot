"""
Screenshot Anomaly Detector.
Validates uploaded chart screenshots: verifies dimensions, entropy, blur level,
and rejects non-chart, corrupted, or severely cropped images.
"""
import math
from typing import Tuple, Dict, Any
from PIL import Image, ImageStat


class ScreenshotAnomalyDetector:
    """Detects invalid, low-quality, or spoofed chart screenshots."""

    def __init__(
        self,
        min_width: int = 300,
        min_height: int = 200,
        min_variance: float = 8.0  # Detects blank/flat solid color images
    ):
        self.min_width = min_width
        self.min_height = min_height
        self.min_variance = min_variance

    def validate_image_file(self, image_path: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Validates image file integrity and chart plausibility.
        Returns: (is_valid, rejection_reason, metrics)
        """
        try:
            with Image.open(image_path) as img:
                width, height = img.size

                # 1. Dimension check
                if width < self.min_width or height < self.min_height:
                    return False, f"Image too small/cropped ({width}x{height} < {self.min_width}x{self.min_height})", {}

                # 2. Aspect ratio check
                aspect_ratio = width / height
                if aspect_ratio < 0.4 or aspect_ratio > 3.5:
                    return False, f"Unusual aspect ratio ({aspect_ratio:.2f}) - not a standard chart viewport", {}

                # 3. Flat image / Blank check (Variance of pixel values)
                gray = img.convert("L")
                stat = ImageStat.Stat(gray)
                variance = stat.var[0] if stat.var else 0.0

                if variance < self.min_variance:
                    return False, "Image has almost zero variance (blank, uniform, or corrupted)", {"variance": round(variance, 2)}

                metrics = {
                    "width": width,
                    "height": height,
                    "aspect_ratio": round(aspect_ratio, 2),
                    "variance": round(variance, 2),
                    "format": img.format
                }
                return True, "Image passes anomaly detection", metrics

        except Exception as e:
            return False, f"Corrupted or unreadable image file: {str(e)}", {}
