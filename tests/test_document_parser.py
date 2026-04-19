"""
Tests for Document Parser — PDF, DOCX, TXT parsing.
"""

import pytest
from pathlib import Path

from backend.agents.document_parser import parse_document


class TestParseDocument:
    """Test document parsing"""

    def test_parse_text_file(self, sample_txt):
        result = parse_document(sample_txt)
        assert result["source_type"] == "document"
        assert result["title"] == "Test Document"
        assert "Python programming" in result["body_text"]
        assert result["metadata"]["file_type"] == "txt"
        assert result["metadata"]["file_size"] > 0

    def test_parse_markdown_file(self, tmp_path):
        md_path = tmp_path / "test.md"
        md_path.write_text("# My Title\n\nSome content here\n", encoding="utf-8")
        
        result = parse_document(str(md_path))
        assert result["title"] == "My Title"
        assert "Some content" in result["body_text"]

    def test_parse_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_document("/nonexistent/file.txt")

    def test_parse_unsupported_format(self, tmp_path):
        bad_file = tmp_path / "test.xyz"
        bad_file.write_text("content")
        with pytest.raises(ValueError, match="Unsupported file type"):
            parse_document(str(bad_file))

    def test_parse_pdf(self, sample_pdf):
        result = parse_document(sample_pdf)
        assert result["source_type"] == "document"
        assert result["metadata"]["file_type"] == "pdf"
        assert result["metadata"]["page_count"] >= 1

    def test_parse_docx(self, sample_docx):
        result = parse_document(sample_docx)
        assert result["source_type"] == "document"
        assert result["metadata"]["file_type"] == "docx"
        assert "Test Document" in result["title"]
        assert "Python" in result["body_text"]

    def test_body_text_limit(self, tmp_path):
        """Test that body text is truncated to 15000 chars"""
        large_txt = tmp_path / "large.txt"
        large_txt.write_text("A" * 20000, encoding="utf-8")
        
        result = parse_document(str(large_txt))
        assert len(result["body_text"]) <= 15000
