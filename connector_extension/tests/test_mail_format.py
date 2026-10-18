from connector_extension.mail_format import email_html


def test_email_has_readable_sections_clickable_report_and_escaped_content():
    text='Purchasing briefing\n\nRestock priorities\n<script>alert(1)</script> & Co\nStock: 10\n\nOpen the report\nhttps://docs.google.com/spreadsheets/d/test/edit'
    rendered=email_html(text)
    assert '<script>' not in rendered
    assert '&lt;script&gt;' in rendered
    assert '<h2' in rendered and 'white-space:pre-line' in rendered
    assert 'href="https://docs.google.com/spreadsheets/d/test/edit"' in rendered
    assert 'Stock: 10' in rendered
