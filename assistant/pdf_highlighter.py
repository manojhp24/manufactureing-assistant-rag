"""
PDF citation highlighting service.

Uses PyMuPDF (fitz) to open original uploaded PDF manuals, locate cited
text passages, and generate highlighted PDF copies. Original PDFs are never
modified -- highlighted output is written to media/highlighted/ with
deterministic, cache-keyed filenames.

Safe fallback: if text cannot be located or highlighting fails, callers
receive the original PDF path so the user can still open the correct page.
"""

import hashlib
import logging
import os
from pathlib import Path

import pymupdf

from django.conf import settings

logger = logging.getLogger(__name__)


class CitationHighlightError(Exception):
    """Base exception for citation highlighting failures."""


class CitationTextNotFoundError(CitationHighlightError):
    """Raised when the cited text passage cannot be found on the target page."""


class InvalidPageNumberError(CitationHighlightError):
    """Raised when the cited page number is out of range."""


class MissingPDfError(CitationHighlightError):
    """Raised when the source PDF file is missing on disk."""


class PdfHighlighter:
    """
    Highlight cited text passages inside original PDF manuals.

    Usage::

        highlighter = PdfHighlighter()
        result = highlighter.highlight_citation(
            manual=manual,
            page_number=4,
            text_passage="Torque specification is 45 Nm",
            question_id=42,
            citation_index=0,
        )
        # result["highlighted_path"] -> absolute path to generated PDF
        # result["pdf_url"] -> media URL for the generated PDF
        # result["fallback"] -> bool, True if highlighting was unavailable
    """

    HIGHLIGHTED_DIR = "highlighted"
    HIGHLIGHT_COLOR = (1.0, 1.0, 0.0)  # Yellow in RGB (0-1 range)

    def __init__(self, media_root=None, media_url=None):
        self.media_root = Path(media_root or settings.MEDIA_ROOT)
        self.media_url = media_url or settings.MEDIA_URL
        self.highlighted_root = self.media_root / self.HIGHLIGHTED_DIR

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def highlight_citation(
        self,
        manual,
        page_number: int,
        text_passage: str,
        question_id: int,
        citation_index: int,
    ) -> dict:
        """
        Generate (or reuse) a highlighted PDF for a citation.

        Returns a dict with keys:
            - highlighted_path: absolute filesystem path to the PDF
            - pdf_url: URL to the protected Django view serving it
            - fallback: bool -- True if highlighting failed/unavailable
            - error: str | None -- human-readable failure reason
            - page_number: int -- the page that was targeted
        """
        result = {
            "highlighted_path": None,
            "pdf_url": None,
            "fallback": False,
            "error": None,
            "page_number": page_number,
        }

        # Validate inputs
        if not manual or not getattr(manual, "pdf_file", None):
            result["error"] = "Source manual PDF is not available."
            result["fallback"] = True
            return result

        if not text_passage or not text_passage.strip():
            result["error"] = "No text passage to highlight."
            result["fallback"] = True
            return result

        pdf_path = Path(manual.pdf_file.path)

        if not pdf_path.exists():
            result["error"] = f"Source PDF not found on disk: {pdf_path}"
            result["fallback"] = True
            return result

        # Build deterministic cache key: manual + revision + page + text
        cache_key = self._cache_key(manual, page_number, text_passage)
        output_path = self.highlighted_root / f"{cache_key}.pdf"

        # Reuse existing generated file if present
        if output_path.exists():
            result["highlighted_path"] = str(output_path)
            result["pdf_url"] = self._public_url(output_path)
            return result

        # Generate new highlighted PDF
        try:
            self._generate_highlighted_pdf(
                pdf_path=pdf_path,
                page_number=page_number,
                text_passage=text_passage,
                output_path=output_path,
            )
        except CitationTextNotFoundError as exc:
            logger.warning(
                "Citation text not found on page %s of %s: %s",
                page_number, pdf_path.name, exc,
            )
            result["error"] = f"Cited passage not found on page {page_number}."
            result["fallback"] = True
            return result
        except InvalidPageNumberError as exc:
            logger.warning("Invalid page number %s: %s", page_number, exc)
            result["error"] = f"Page {page_number} is out of range."
            result["fallback"] = True
            return result
        except MissingPDfError as exc:
            logger.warning("Missing PDF: %s", exc)
            result["error"] = "Source PDF not available."
            result["fallback"] = True
            return result
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception("Unexpected error highlighting citation:")
            result["error"] = f"PDF highlighting failed: {exc}"
            result["fallback"] = True
            return result

        result["highlighted_path"] = str(output_path)
        result["pdf_url"] = self._public_url(output_path)
        return result

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _cache_key(manual, page_number: int, text_passage: str) -> str:
        """Build a deterministic filename from manual + page + passage text."""
        material = (
            f"{manual.document_id}|{manual.revision}|"
            f"{page_number}|{text_passage}"
        )
        digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]
        safe_doc_id = "".join(
            c if c.isalnum() or c in "-_" else "_" for c in manual.document_id
        )
        return f"{safe_doc_id}_r{manual.revision}_p{page_number}_{digest}"

    def _public_url(self, output_path: Path) -> str:
        """Return the media URL for a generated highlighted PDF."""
        relative = output_path.relative_to(self.media_root)
        url = f"{self.media_url.rstrip('/')}/{relative.as_posix()}"
        return url

    def _generate_highlighted_pdf(
        self,
        pdf_path: Path,
        page_number: int,
        text_passage: str,
        output_path: Path,
    ) -> None:
        """
        Open the source PDF, locate text on the cited page, highlight it,
        and save a copy to output_path. Original file is never touched.
        """
        doc = pymupdf.open(str(pdf_path))

        try:
            # Convert 1-based page number to 0-based index
            page_index = page_number - 1
            if page_index < 0 or page_index >= doc.page_count:
                raise InvalidPageNumberError(
                    f"Page {page_number} is out of range "
                    f"(document has {doc.page_count} pages)."
                )

            page = doc[page_index]

            # Clean the passage for matching: collapse whitespace
            cleaned_passage = self._normalize_whitespace(text_passage)
            if not cleaned_passage:
                raise CitationTextNotFoundError("Empty text passage after normalization.")

            # Try exact match first, then fallback to substring matching
            matches = self._find_text_matches(page, cleaned_passage)

            if not matches:
                # Try matching individual sentences if full passage not found
                sentences = self._split_into_sentences(cleaned_passage)
                for sentence in sentences:
                    sentence = sentence.strip()
                    if len(sentence) < 5:
                        continue
                    sentence_matches = self._find_text_matches(page, sentence)
                    matches.extend(sentence_matches)
                    if matches:
                        break

            if not matches:
                raise CitationTextNotFoundError(
                    f"Text passage not found on page {page_number}."
                )

            # Apply highlights (deduplicate overlapping rectangles)
            self._apply_highlights(page, matches)

            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Save the highlighted copy (original remains untouched)
            doc.save(str(output_path), deflate=True, garbage=4)

        finally:
            doc.close()

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """Collapse runs of whitespace into single spaces, strip ends."""
        return " ".join(text.split())

    def _find_text_matches(self, page, query: str) -> list:
        """
        Search a PyMuPDF page for all occurrences of query.

        Returns a list of Rect objects covering matched text regions.
        Handles multi-line text via PyMuPDF's built-in search.
        """
        rects = []

        # PyMuPDF search_for finds exact text, handles line-wrapping internally
        text_rects = page.search_for(query)

        for rect in text_rects:
            rects.append(rect)

        return rects

    @staticmethod
    def _split_into_sentences(text: str) -> list:
        """Split text into sentence-like fragments for fallback matching."""
        import re

        # Split on common sentence boundaries
        parts = re.split(r"(?<=[.!?])\s+", text)
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def _apply_highlights(page, rects: list) -> None:
        """
        Add yellow highlight annotations to the given rectangles.

        Rectangles that overlap are merged to avoid redundant annotations.
        """
        if not rects:
            return

        # Sort by y then x to group nearby regions
        rects.sort(key=lambda r: (r.y0, r.x0))

        # Merge overlapping / adjacent rects within a small tolerance
        merged = []
        for rect in rects:
            if merged:
                last = merged[-1]
                # If this rect overlaps or touches the previous, extend it
                if (
                    rect.x0 <= last.x1 + 2
                    and rect.x1 >= last.x0 - 2
                    and rect.y0 <= last.y1 + 2
                    and rect.y1 >= last.y0 - 2
                ):
                    merged[-1] = pymupdf.Rect(
                        min(last.x0, rect.x0),
                        min(last.y0, rect.y0),
                        max(last.x1, rect.x1),
                        max(last.y1, rect.y1),
                    )
                    continue
            merged.append(rect)

        for rect in merged:
            annot = page.add_highlight_annot(rect)
            if annot:
                annot.set_colors(stroke=PdfHighlighter.HIGHLIGHT_COLOR)
                annot.update()