"""Template matching module using OpenCV."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from src.utils.logger import get_logger


@dataclass
class Match:
    """Represents a template match result."""

    x: int
    y: int
    width: int
    height: int
    confidence: float

    @property
    def center(self) -> Tuple[int, int]:
        """Get center point of the match."""
        return (self.x + self.width // 2, self.y + self.height // 2)

    @property
    def bottom_center(self) -> Tuple[int, int]:
        """Get bottom center point (useful for clicking items)."""
        return (self.x + self.width // 2, self.y + self.height)

    @property
    def region(self) -> Tuple[int, int, int, int]:
        """Get region as (x, y, width, height)."""
        return (self.x, self.y, self.width, self.height)

    @property
    def rect(self) -> Tuple[int, int, int, int]:
        """Get rectangle as (x1, y1, x2, y2)."""
        return (self.x, self.y, self.x + self.width, self.y + self.height)


class TemplateMatcher:
    """
    Template matching using OpenCV.

    Loads templates from disk and provides methods to find
    them in screenshots using cv2.matchTemplate.
    """

    # Default matching method
    DEFAULT_METHOD = cv2.TM_CCOEFF_NORMED

    # Default threshold for considering a match valid
    DEFAULT_THRESHOLD = 0.8

    # Minimum distance between matches to consider them distinct
    DEFAULT_MIN_DISTANCE = 10

    def __init__(
        self,
        template_dir: str = "assets/templates",
        method: int = DEFAULT_METHOD,
        default_threshold: float = DEFAULT_THRESHOLD,
    ):
        """
        Initialize template matcher.

        Args:
            template_dir: Base directory containing template images
            method: OpenCV matching method (default: TM_CCOEFF_NORMED)
            default_threshold: Default confidence threshold
        """
        self.template_dir = Path(template_dir)
        self.method = method
        self.default_threshold = default_threshold
        self.log = get_logger()

        # Template cache: name -> (template_image, grayscale_version)
        self._cache: Dict[str, Tuple[np.ndarray, np.ndarray]] = {}

    def _get_template_path(self, name: str) -> Path:
        """
        Get full path for a template name.

        Args:
            name: Template name (with or without extension)
                  Can include subdirectory: "screens/main_menu"

        Returns:
            Full path to template file
        """
        # Add .png extension if not present
        if not name.endswith(('.png', '.jpg', '.jpeg')):
            name = f"{name}.png"

        return self.template_dir / name

    def load_template(self, name: str) -> Optional[np.ndarray]:
        """
        Load a template image from disk.

        Args:
            name: Template name (e.g., "screens/main_menu" or "hud/health_orb")

        Returns:
            Template image as numpy array (BGR), or None if not found
        """
        # Check cache first
        if name in self._cache:
            return self._cache[name][0]

        path = self._get_template_path(name)

        if not path.exists():
            self.log.warning(f"Template not found: {path}")
            return None

        # Load image
        template = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if template is None:
            self.log.error(f"Failed to load template: {path}")
            return None

        # Create grayscale version for matching
        gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

        # Cache both versions
        self._cache[name] = (template, gray)

        self.log.debug(f"Loaded template: {name} ({template.shape[1]}x{template.shape[0]})")
        return template

    def _get_template_gray(self, name: str) -> Optional[np.ndarray]:
        """Get grayscale version of template."""
        if name not in self._cache:
            self.load_template(name)

        if name in self._cache:
            return self._cache[name][1]
        return None

    def _get_template_size(self, name: str) -> Optional[Tuple[int, int]]:
        """Get template dimensions (width, height)."""
        template = self.load_template(name)
        if template is not None:
            return (template.shape[1], template.shape[0])
        return None

    def find(
        self,
        screen: np.ndarray,
        template_name: str,
        threshold: Optional[float] = None,
        use_grayscale: bool = True,
    ) -> Optional[Match]:
        """
        Find a single best match of template in screen.

        Args:
            screen: Screenshot to search in (BGR format)
            template_name: Name of template to find
            threshold: Minimum confidence threshold (default: self.default_threshold)
            use_grayscale: Convert to grayscale before matching (faster)

        Returns:
            Match object if found above threshold, None otherwise
        """
        if threshold is None:
            threshold = self.default_threshold

        # Load template
        if use_grayscale:
            template = self._get_template_gray(template_name)
            if template is None:
                return None
            search_img = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        else:
            template = self.load_template(template_name)
            if template is None:
                return None
            search_img = screen

        # Get template dimensions
        h, w = template.shape[:2]

        # Perform template matching
        try:
            result = cv2.matchTemplate(search_img, template, self.method)
        except cv2.error as e:
            self.log.error(f"Template matching failed: {e}")
            return None

        # Find best match location
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)

        # For TM_SQDIFF methods, minimum is best match
        if self.method in (cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED):
            confidence = 1 - min_val if self.method == cv2.TM_SQDIFF_NORMED else min_val
            loc = min_loc
        else:
            confidence = max_val
            loc = max_loc

        # Check threshold
        if confidence < threshold:
            return None

        return Match(
            x=loc[0],
            y=loc[1],
            width=w,
            height=h,
            confidence=confidence,
        )

    def find_all(
        self,
        screen: np.ndarray,
        template_name: str,
        threshold: Optional[float] = None,
        use_grayscale: bool = True,
        min_distance: int = DEFAULT_MIN_DISTANCE,
        max_matches: int = 100,
    ) -> List[Match]:
        """
        Find all matches of template in screen above threshold.

        Args:
            screen: Screenshot to search in (BGR format)
            template_name: Name of template to find
            threshold: Minimum confidence threshold
            use_grayscale: Convert to grayscale before matching
            min_distance: Minimum pixel distance between matches
            max_matches: Maximum number of matches to return

        Returns:
            List of Match objects, sorted by confidence (highest first)
        """
        if threshold is None:
            threshold = self.default_threshold

        # Load template
        if use_grayscale:
            template = self._get_template_gray(template_name)
            if template is None:
                return []
            search_img = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        else:
            template = self.load_template(template_name)
            if template is None:
                return []
            search_img = screen

        # Get template dimensions
        h, w = template.shape[:2]

        # Perform template matching
        try:
            result = cv2.matchTemplate(search_img, template, self.method)
        except cv2.error as e:
            self.log.error(f"Template matching failed: {e}")
            return []

        # Find all locations above threshold
        if self.method in (cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED):
            # For SQDIFF, lower is better
            locations = np.where(result <= (1 - threshold))
        else:
            locations = np.where(result >= threshold)

        # Build list of matches with confidence scores
        matches = []
        for pt in zip(*locations[::-1]):  # Switch x and y
            confidence = result[pt[1], pt[0]]
            if self.method in (cv2.TM_SQDIFF, cv2.TM_SQDIFF_NORMED):
                confidence = 1 - confidence

            matches.append(Match(
                x=pt[0],
                y=pt[1],
                width=w,
                height=h,
                confidence=confidence,
            ))

        # Sort by confidence (highest first)
        matches.sort(key=lambda m: m.confidence, reverse=True)

        # Filter nearby duplicates (non-maximum suppression)
        filtered = self._filter_nearby_matches(matches, min_distance)

        # Limit results
        return filtered[:max_matches]

    def _filter_nearby_matches(
        self,
        matches: List[Match],
        min_distance: int,
    ) -> List[Match]:
        """
        Filter out matches that are too close to each other.

        Keeps the match with highest confidence when matches overlap.

        Args:
            matches: List of matches (should be sorted by confidence)
            min_distance: Minimum pixel distance between match centers

        Returns:
            Filtered list of matches
        """
        if not matches:
            return []

        filtered = []

        for match in matches:
            # Check if this match is too close to any already accepted match
            is_duplicate = False
            for accepted in filtered:
                dist = self._distance(match.center, accepted.center)
                if dist < min_distance:
                    is_duplicate = True
                    break

            if not is_duplicate:
                filtered.append(match)

        return filtered

    @staticmethod
    def _distance(p1: Tuple[int, int], p2: Tuple[int, int]) -> float:
        """Calculate Euclidean distance between two points."""
        return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5

    def find_any(
        self,
        screen: np.ndarray,
        template_names: List[str],
        threshold: Optional[float] = None,
    ) -> Optional[Tuple[str, Match]]:
        """
        Find the first matching template from a list.

        Args:
            screen: Screenshot to search in
            template_names: List of template names to try
            threshold: Minimum confidence threshold

        Returns:
            Tuple of (template_name, Match) or None if none found
        """
        for name in template_names:
            match = self.find(screen, name, threshold)
            if match:
                return (name, match)
        return None

    def find_best(
        self,
        screen: np.ndarray,
        template_names: List[str],
        threshold: Optional[float] = None,
    ) -> Optional[Tuple[str, Match]]:
        """
        Find the best matching template from a list.

        Args:
            screen: Screenshot to search in
            template_names: List of template names to try
            threshold: Minimum confidence threshold

        Returns:
            Tuple of (template_name, Match) with highest confidence, or None
        """
        best_name = None
        best_match = None

        for name in template_names:
            match = self.find(screen, name, threshold)
            if match and (best_match is None or match.confidence > best_match.confidence):
                best_name = name
                best_match = match

        if best_match:
            return (best_name, best_match)
        return None

    def preload_templates(self, names: List[str]) -> int:
        """
        Preload templates into cache.

        Args:
            names: List of template names to preload

        Returns:
            Number of templates successfully loaded
        """
        loaded = 0
        for name in names:
            if self.load_template(name) is not None:
                loaded += 1
        self.log.info(f"Preloaded {loaded}/{len(names)} templates")
        return loaded

    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._cache.clear()
        self.log.debug("Template cache cleared")

    def get_cached_templates(self) -> List[str]:
        """Get list of cached template names."""
        return list(self._cache.keys())

    def draw_match(
        self,
        image: np.ndarray,
        match: Match,
        color: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2,
        label: bool = True,
    ) -> np.ndarray:
        """
        Draw a rectangle around a match on an image.

        Args:
            image: Image to draw on (will be modified)
            match: Match to highlight
            color: BGR color for rectangle
            thickness: Line thickness
            label: Whether to draw confidence label

        Returns:
            Image with match highlighted
        """
        # Draw rectangle
        cv2.rectangle(
            image,
            (match.x, match.y),
            (match.x + match.width, match.y + match.height),
            color,
            thickness,
        )

        # Draw confidence label
        if label:
            text = f"{match.confidence:.2f}"
            cv2.putText(
                image,
                text,
                (match.x, match.y - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
            )

        return image

    def draw_matches(
        self,
        image: np.ndarray,
        matches: List[Match],
        color: Tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2,
    ) -> np.ndarray:
        """
        Draw rectangles around multiple matches.

        Args:
            image: Image to draw on
            matches: List of matches to highlight
            color: BGR color for rectangles
            thickness: Line thickness

        Returns:
            Image with matches highlighted
        """
        for match in matches:
            self.draw_match(image, match, color, thickness)
        return image
