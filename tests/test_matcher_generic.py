"""Generic fingerprints (core plan B2): confidential data that is not our stock register.

`fingerprint_fields: [all]` indexes e-mail addresses, phone and account numbers, identifiers, numbers, dates and passages
of text from a confidential tool's output; an outbound message that repeats any of them is caught. Paraphrase is still a
declared gap, and the index keeps hashes of passages, never the prose itself."""

from sentinel.matcher import FingerprintIndex


def indexed(text: str, fields=("all",)) -> FingerprintIndex:
    i = FingerprintIndex()
    i.add(text, list(fields), "read_customers")
    return i


def kinds(index: FingerprintIndex, text: str) -> set[str]:
    return {m.kind for m in index.scan_text(text)}


CUSTOMERS = ("Priya Nair, priya.nair@client.example, phone +91 98765 43210, account ACCT-00471, owes 48,500 rupees "
             "since 2026-09-14. Rahul Das, rahul.das@client.example, phone 98111 22233, account ACCT-00518.")


def test_an_e_mail_address_from_confidential_data_is_caught_in_any_case_or_wrapping():
    i = indexed(CUSTOMERS)
    for text in ("write to priya.nair@client.example", "PRIYA.NAIR@CLIENT.EXAMPLE", "Priya <Priya.Nair@Client.Example>"):
        assert "email" in kinds(i, text), text
    assert kinds(i, "write to nobody@client.example") == set()


def test_a_phone_or_account_number_is_the_same_number_however_it_is_written():
    i = indexed(CUSTOMERS)
    for text in ("call 9876543210", "call +91 98765 43210", "call +91-98765-43210", "call 98765.43210", "call ９８７６５４３２１０"):
        assert "digits" in kinds(i, text), text
    for text in ("call 9876543211", "call 98765", "ref 12345678"):
        assert "digits" not in kinds(i, text), text


def test_an_identifier_matches_regardless_of_separator_or_leading_zeros():
    i = indexed(CUSTOMERS)
    for text in ("account ACCT-00471", "acct 471", "ACCT_471", "ACCT00471"):
        assert "id" in kinds(i, text), text
    assert "id" not in kinds(i, "account ACCT-00999")


def test_numbers_and_dates_from_any_confidential_tool_are_indexed_too():
    i = indexed(CUSTOMERS)
    # "owes 48,500" must be indexed as 48500, not as the 500 left over once "owes 48" is mistaken for a depot code
    assert ("number", "48500") in i.entries and ("number", "500") not in i.entries
    assert "number" in kinds(i, "they owe 48500")
    assert "date" in kinds(i, "since 14 September 2026")


def test_a_copied_passage_is_caught_but_a_paraphrase_is_the_declared_gap():
    secret = ("The board has approved the acquisition of Northwind Traders for a price of two hundred crore, "
              "to be announced after the quarterly results next month.")
    i = indexed(secret)
    assert "text" in kinds(i, "FYI: the board has approved the acquisition of Northwind Traders for a price of two")
    assert "text" in kinds(i, secret.upper())
    assert kinds(i, "We are buying a company next month; details to follow.") == set()  # paraphrase: declared gap
    assert kinds(i, "the board has approved the budget") == set()  # a short common phrase is not a copy


def test_the_index_keeps_hashes_of_passages_never_the_prose():
    i = indexed("The unannounced merger terms are strictly confidential and must not leave the finance team.")
    assert all("merger" not in canonical for _, canonical in i.entries)


def test_all_does_not_index_the_weak_code_pattern_that_would_block_innocent_text():
    i = indexed("See page 12 of the handbook, item 7 on the agenda, and room 4 upstairs.")
    assert kinds(i, "please turn to page 12, item 7, room 4") == set()


def test_specific_fields_index_only_what_they_name():
    only_email = indexed(CUSTOMERS, ("email",))
    assert kinds(only_email, "9876543210 and ACCT-00471") == set() and "email" in kinds(only_email, "priya.nair@client.example")


def test_the_original_stock_register_fields_behave_exactly_as_before():
    i = indexed("9mm casings: 2,400 units at depot FSD-14, next dispatch 2026-11-02", ("quantity", "depot_code", "dispatch_date"))
    assert kinds(i, "we hold 2400 at fsd14 dispatching 2 November 2026") == {"number", "code", "date"}
    assert kinds(i, "contact a@b.example or 9876543210") == set()
