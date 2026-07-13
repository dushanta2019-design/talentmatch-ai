from app.services.embeddings import chunk_text


def test_short_text_single_chunk():
    assert chunk_text("hello") == ["hello"]


def test_empty_text_no_chunks():
    assert chunk_text("   ") == []


def test_long_text_chunks_cover_content():
    text = "\n".join(f"Paragraph {i}: " + "word " * 40 for i in range(30))
    chunks = chunk_text(text)
    assert len(chunks) > 1
    assert all(len(c) <= 1500 for c in chunks)
    # first and last content survive chunking
    assert "Paragraph 0" in chunks[0]
    assert "Paragraph 29" in chunks[-1]
