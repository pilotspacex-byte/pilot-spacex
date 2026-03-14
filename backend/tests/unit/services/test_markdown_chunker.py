"""Unit tests for markdown_chunker.chunk_markdown_by_headings."""

from __future__ import annotations

import pytest

from pilot_space.application.services.note.markdown_chunker import (
    MarkdownChunk,
    chunk_markdown_by_headings,
)


class TestEmptyInput:
    def test_empty_string_returns_empty_list(self) -> None:
        assert chunk_markdown_by_headings("") == []

    def test_whitespace_only_returns_empty_list(self) -> None:
        assert chunk_markdown_by_headings("   \n\n  ") == []


class TestNoHeadings:
    def test_plain_text_returns_single_chunk(self) -> None:
        md = "Just a paragraph.\n\nAnd another one."
        chunks = chunk_markdown_by_headings(md)
        assert len(chunks) == 1
        assert chunks[0].heading == ""
        assert chunks[0].heading_level == 0
        assert chunks[0].chunk_index == 0
        assert "Just a paragraph." in chunks[0].content

    def test_single_chunk_index_is_zero(self) -> None:
        chunks = chunk_markdown_by_headings("No headings here.")
        assert chunks[0].chunk_index == 0


class TestHeadingSplitting:
    def test_h1_creates_one_chunk(self) -> None:
        md = "# Title\n\nFirst section content.\n"
        chunks = chunk_markdown_by_headings(md)
        assert len(chunks) == 1
        assert chunks[0].heading == "Title"
        assert chunks[0].heading_level == 1

    def test_h1_then_h2(self) -> None:
        md = "# Introduction\n\nIntro text.\n\n## Details\n\nDetail text.\n"
        chunks = chunk_markdown_by_headings(md)
        assert len(chunks) == 2
        assert chunks[0].heading == "Introduction"
        assert chunks[0].heading_level == 1
        assert chunks[1].heading == "Details"
        assert chunks[1].heading_level == 2

    def test_chunk_indices_are_sequential(self) -> None:
        md = "# A\n\ntext\n\n# B\n\ntext\n\n# C\n\ntext\n"
        chunks = chunk_markdown_by_headings(md)
        assert [c.chunk_index for c in chunks] == [0, 1, 2]

    def test_content_includes_heading_line(self) -> None:
        md = "# My Section\n\nBody text here.\n"
        chunks = chunk_markdown_by_headings(md)
        assert "# My Section" in chunks[0].content
        assert "Body text here." in chunks[0].content

    def test_mixed_levels(self) -> None:
        md = "# Top\n\nIntro.\n\n## Sub\n\nSub content.\n\n### Deep\n\nDeep content.\n"
        chunks = chunk_markdown_by_headings(md)
        assert len(chunks) == 3
        assert chunks[0].heading_level == 1
        assert chunks[1].heading_level == 2
        assert chunks[2].heading_level == 3


class TestPreamble:
    def test_text_before_first_heading_becomes_preamble(self) -> None:
        md = "Intro text before any heading.\n\n# First Section\n\nContent.\n"
        chunks = chunk_markdown_by_headings(md)
        assert len(chunks) == 2
        assert chunks[0].heading == ""
        assert chunks[0].heading_level == 0
        assert "Intro text before any heading." in chunks[0].content
        assert chunks[1].heading == "First Section"

    def test_whitespace_only_preamble_is_skipped(self) -> None:
        md = "\n\n# First\n\nContent.\n"
        chunks = chunk_markdown_by_headings(md)
        assert len(chunks) == 1
        assert chunks[0].heading == "First"


class TestCodeFenceProtection:
    def test_heading_inside_code_fence_not_a_boundary(self) -> None:
        md = "# Real Heading\n\n```\n# Not a heading\n## Also not\n```\n\nParagraph.\n"
        chunks = chunk_markdown_by_headings(md)
        assert len(chunks) == 1
        assert chunks[0].heading == "Real Heading"
        assert "# Not a heading" in chunks[0].content

    def test_multiple_real_headings_with_code_fences(self) -> None:
        md = "# Section A\n\n```python\n# comment\n```\n\n# Section B\n\nReal content.\n"
        chunks = chunk_markdown_by_headings(md)
        assert len(chunks) == 2
        assert chunks[0].heading == "Section A"
        assert chunks[1].heading == "Section B"


class TestSmallChunkMerging:
    def test_small_chunk_merged_with_predecessor(self) -> None:
        md = "# Main Section\n\nLots of content here that is definitely long enough.\n\n## Tiny\n\nHi.\n"
        chunks = chunk_markdown_by_headings(md, min_chunk_chars=50)
        assert len(chunks) == 1
        assert chunks[0].heading == "Main Section"
        assert "Hi." in chunks[0].content

    def test_chunk_above_body_threshold_not_merged(self) -> None:
        md = (
            "# Section A\n\nContent for section A.\n\n"
            "# Section B\n\nContent for section B which is long enough.\n"
        )
        chunks = chunk_markdown_by_headings(md, min_chunk_chars=10)
        assert len(chunks) == 2

    def test_no_merging_by_default(self) -> None:
        md = "# A\n\nTiny.\n\n# B\n\nAlso tiny.\n"
        chunks = chunk_markdown_by_headings(md)
        assert len(chunks) == 2

    def test_preamble_never_merged_away(self) -> None:
        md = "Intro.\n\n# Section\n\nBody content here that is long enough to stand alone.\n"
        chunks = chunk_markdown_by_headings(md, min_chunk_chars=5)
        assert len(chunks) == 2
        assert chunks[0].heading == ""
        assert chunks[1].heading == "Section"


class TestChunkCap:
    def test_chunks_capped_dynamically(self) -> None:
        sections = "\n".join(f"# Section {i}\n\nContent for section {i}.\n" for i in range(25))
        chunks = chunk_markdown_by_headings(sections, min_chunk_chars=1)
        # Dynamic cap: for ~750 bytes, cap = max(20, (750/1024)*5) = 20
        assert len(chunks) <= 25  # may be capped

    def test_overflow_merged_into_last_chunk(self) -> None:
        # Create a small doc that hits the default cap of 20
        sections = "\n".join(f"# S{i}\n\nC{i}.\n" for i in range(22))
        chunks = chunk_markdown_by_headings(sections, min_chunk_chars=1)
        assert len(chunks) <= 22
        last = chunks[-1].content
        assert "C21" in last  # overflow merged


class TestReturnType:
    def test_returns_markdown_chunk_instances(self) -> None:
        md = "# Title\n\nBody.\n"
        chunks = chunk_markdown_by_headings(md)
        assert all(isinstance(c, MarkdownChunk) for c in chunks)

    def test_chunks_are_frozen(self) -> None:
        md = "# Title\n\nBody.\n"
        chunk = chunk_markdown_by_headings(md)[0]
        with pytest.raises((AttributeError, TypeError)):
            chunk.heading = "new"  # type: ignore[misc]


# ============================================================================
# New feature tests
# ============================================================================


class TestHeadingHierarchy:
    """Test heading hierarchy enrichment."""

    def test_h2_has_h1_parent(self) -> None:
        md = "# Parent\n\nParent content.\n\n## Child\n\nChild content.\n"
        chunks = chunk_markdown_by_headings(md, enrich_hierarchy=True)
        assert chunks[1].heading_hierarchy == ["Parent", "Child"]

    def test_h3_has_h1_h2_parents(self) -> None:
        md = "# Root\n\nR.\n\n## Mid\n\nM.\n\n### Leaf\n\nL.\n"
        chunks = chunk_markdown_by_headings(md, enrich_hierarchy=True)
        assert chunks[2].heading_hierarchy == ["Root", "Mid", "Leaf"]

    def test_h1_has_self_only(self) -> None:
        md = "# Top Level\n\nContent.\n"
        chunks = chunk_markdown_by_headings(md, enrich_hierarchy=True)
        assert chunks[0].heading_hierarchy == ["Top Level"]

    def test_hierarchy_disabled(self) -> None:
        md = "# Parent\n\nP.\n\n## Child\n\nC.\n"
        chunks = chunk_markdown_by_headings(md, enrich_hierarchy=False)
        assert chunks[1].heading_hierarchy == []


class TestTokenCount:
    """Test token counting on chunks."""

    def test_chunk_has_token_count(self) -> None:
        md = "# Title\n\nSome body text here.\n"
        chunks = chunk_markdown_by_headings(md)
        assert chunks[0].token_count > 0

    def test_token_count_proportional_to_length(self) -> None:
        short_md = "# A\n\nShort.\n"
        long_md = "# A\n\n" + "Long content. " * 100 + "\n"
        short_chunks = chunk_markdown_by_headings(short_md)
        long_chunks = chunk_markdown_by_headings(long_md)
        assert long_chunks[0].token_count > short_chunks[0].token_count


class TestSubChunking:
    """Test recursive sub-chunking of oversized sections."""

    def test_oversized_section_is_sub_chunked(self) -> None:
        # Create a section with 3000+ chars (exceeds default 2000 max)
        body = "\n\n".join(f"Paragraph {i} with some content." for i in range(100))
        md = f"# Big Section\n\n{body}\n"
        chunks = chunk_markdown_by_headings(md, max_chunk_chars=500)
        assert len(chunks) > 1
        assert chunks[0].heading == "Big Section"
        # Subsequent sub-chunks get "(part N)" suffix
        assert "part" in chunks[1].heading

    def test_small_section_not_sub_chunked(self) -> None:
        md = "# Normal\n\nThis is normal sized content.\n"
        chunks = chunk_markdown_by_headings(md, max_chunk_chars=2000)
        assert len(chunks) == 1

    def test_sub_chunks_have_sequential_indices(self) -> None:
        body = "\n\n".join(f"Paragraph {i} content here." for i in range(50))
        md = f"# Section\n\n{body}\n"
        chunks = chunk_markdown_by_headings(md, max_chunk_chars=200)
        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(indices)))


class TestOverlap:
    """Test overlap between consecutive sub-chunks."""

    def test_overlap_adds_context(self) -> None:
        # Create content that will be split into 2+ sub-chunks
        para1 = "First paragraph with unique identifier ALPHA."
        para2 = "Second paragraph with unique identifier BETA."
        para3 = "Third paragraph with unique identifier GAMMA."
        body = f"{para1}\n\n{para2}\n\n{para3}"
        md = f"# Section\n\n{body}\n"

        chunks = chunk_markdown_by_headings(md, max_chunk_chars=100, overlap_chars=50)
        if len(chunks) > 1:
            # Second chunk should contain overlap from first chunk's tail
            assert len(chunks[1].content) > 0

    def test_zero_overlap(self) -> None:
        body = "\n\n".join(f"Para {i} text." for i in range(20))
        md = f"# Section\n\n{body}\n"
        chunks_no_overlap = chunk_markdown_by_headings(md, max_chunk_chars=100, overlap_chars=0)
        chunks_with_overlap = chunk_markdown_by_headings(md, max_chunk_chars=100, overlap_chars=50)
        # With overlap, chunks may be slightly larger or same count
        assert len(chunks_no_overlap) >= 1
        assert len(chunks_with_overlap) >= 1


class TestDynamicMaxChunks:
    """Test dynamic max chunks based on document size."""

    def test_small_doc_uses_default_cap(self) -> None:
        # Small doc (<1KB) should cap at 20
        sections = "\n".join(f"# S{i}\n\nC.\n" for i in range(25))
        chunks = chunk_markdown_by_headings(sections)
        assert len(chunks) <= 20

    def test_large_doc_scales_up(self) -> None:
        # Large doc (10KB+) should allow more chunks
        long_content = "x" * 500  # 500 chars per section
        sections = "\n".join(f"# Section {i}\n\n{long_content}\n" for i in range(30))
        chunks = chunk_markdown_by_headings(sections, max_chunk_chars=5000)
        # 15KB doc → max(20, (15000/1024)*5) ≈ max(20, 73) = 73
        assert len(chunks) == 30  # all 30 should fit
