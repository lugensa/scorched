import json
import os

import pytest

from scorched import SolrInterface


class Book:
    def __init__(self, name, author, **other_kwargs):
        self.title = name
        self.author = author
        self.other_kwargs = other_kwargs

    def __repr__(self):
        return 'Book("%s", "%s")' % (self.title, self.author)


@pytest.fixture(scope="module")
def books():
    file_ = os.path.join(os.path.dirname(__file__), "dumps", "books.json")
    with open(file_) as f:
        datajson = f.read()
        docs = json.loads(datajson)
    return docs


@pytest.fixture
def si(solr_url):
    si_ = SolrInterface(solr_url)
    yield si_
    si_.delete_all()
    si_.commit()


def test_get(si, books):
    res = si.get("978-1423103349")
    assert len(res) == 0

    si.add(books)
    res = si.get("978-1423103349")
    assert len(res) == 1
    assert res[0]["name"] == "The Sea of Monsters"

    res = si.get(["978-0641723445", "978-1423103349", "nonexist"])
    assert len(res) == 2
    assert [x["name"] for x in res] == ["The Lightning Thief", "The Sea of Monsters"]

    si.commit()

    res = si.get(ids="978-1423103349", fields=["author"])
    assert len(res) == 1
    assert list(res[0].keys()) == ["author"]


def test_query(si, books):
    si.add(books)
    si.commit()
    res = si.query(genre_s="fantasy").execute()
    assert res.result.numFound == 3

    res = si.delete_by_ids(res.result.docs[0]["id"])
    assert res.status == 0
    res = si.query(genre_s="fantasy").execute()
    si.commit()
    res = si.query(genre_s="fantasy").execute()
    assert res.result.numFound == 2
    res = si.query(genre_s="fantasy").execute(constructor=Book)

    # test constructor
    assert [x.title for x in res.result.docs] == [
        "The Sea of Monsters",
        "Sophie's World : The Greek Philosophers",
    ]


def test_cursor(si, books):
    si.add(books)
    si.commit()
    cursor = si.query(genre_s="fantasy").sort_by("id").cursor(rows=1)

    # Count how often we hit solr
    search_count = [0]
    old_search = cursor.search.interface.search

    def search_proxy(*args, **kwargs):
        search_count[0] += 1
        return old_search(*args, **kwargs)

    cursor.search.interface.search = search_proxy

    list(cursor)
    assert search_count[0] == 4  # 3 + 1 to realize we are done

    search_count = [0]
    cursor = si.query(genre_s="fantasy").sort_by("id").cursor(constructor=Book, rows=2)
    # test constructor
    assert [x.title for x in cursor] == [
        "The Lightning Thief",
        "The Sea of Monsters",
        "Sophie's World : The Greek Philosophers",
    ]

    assert search_count[0] == 3

    # empty results
    search_count = [0]
    cursor = si.query(genre_s="nonexist").sort_by("id").cursor(constructor=Book)
    assert list(cursor) == []
    assert search_count[0] == 1


def test_rollback(si, books):
    si.add(books)
    si.commit()
    res = si.query(genre_s="fantasy").execute()
    assert res.result.numFound == 3
    # delete
    res = si.delete_by_ids(res.result.docs[0]["id"])
    assert res.status == 0

    # rollback
    res = si.rollback()
    assert res.status == 0
    res = si.query(genre_s="fantasy").execute()
    assert res.result.numFound == 3


def test_chunked_add(si, books):
    assert len(books) == 4
    # chunk size = 1, chunks = 4
    si.delete_all()
    res = si.add(books, chunk=1)
    assert len(res) == 4
    assert [r.status for r in res] == [0] * 4
    si.commit()
    res = si.query(genre_s="fantasy").execute()
    assert res.result.numFound == 3
    # chunk size = 2, chunks = 2
    si.delete_all()

    res = si.add(books, chunk=2)
    assert len(res) == 2
    assert [r.status for r in res] == [0] * 2
    si.commit()
    res = si.query(genre_s="fantasy").execute()
    assert res.result.numFound == 3


def test_facet_query(si, books):
    res = si.add(books)
    assert res[0].status == 0
    si.commit()
    res = si.query(genre_s="fantasy").facet_by("cat").execute()
    assert res.result.numFound == 3
    assert [x["name"] for x in res.result.docs] == [
        "The Lightning Thief",
        "The Sea of Monsters",
        "Sophie's World : The Greek Philosophers",
    ]

    assert res.facet_counts.__dict__ == {
        "facet_fields": {"cat": [("book", 3), ("paperback", 2), ("hardcover", 1)]},
        "facet_dates": {},
        "facet_queries": {},
        "facet_ranges": {},
        "facet_pivot": {},
    }


def test_filter_query(si, books):
    si.add(books)
    si.commit()
    res = (
        si.query(si.Q(**{"*": "*"}))
        .filter(cat="hardcover")
        .filter(genre_s="fantasy")
        .execute()
    )
    assert res.result.numFound == 1
    assert [x["name"] for x in res.result.docs] == ["The Lightning Thief"]


def test_edismax_query(si, books):
    si.add(books)
    si.commit()
    res = (
        si.query(si.Q(**{"*": "*"}))
        .filter(cat="hardcover")
        .filter(genre_s="fantasy")
        .alt_parser("edismax")
        .execute()
    )
    assert res.result.numFound == 1
    assert [x["name"] for x in res.result.docs] == ["The Lightning Thief"]


def test_mlt_component_query(si, books):
    si.add(books)
    si.commit()
    res = si.query(id="978-0641723445").mlt("genre_s", mintf=1, mindf=1).execute()
    # query shows only one
    assert res.result.numFound == 1
    # but in more like this we get two
    assert len(res.more_like_these["978-0641723445"].docs), 2
    assert [x["author"] for x in res.more_like_these["978-0641723445"].docs] == [
        "Rick Riordan",
        "Jostein Gaarder",
    ]


def test_encoding(si):
    docs = {
        "id": "978-0641723445",
        "cat": ["book", "hardcover"],
        "name": "The Höhlentripp Strauß",
        "author": "Röüß Itoa",
        "series_t": "Percy Jackson and \N{UMBRELLA}nicode",
        "sequence_i": 1,
        "genre_s": "fantasy",
        "inStock": True,
        "price": 12.50,
        "pages_i": 384,
    }
    si.add(docs)
    si.commit()
    res = si.query(author=u"Röüß").execute()
    assert res.result.numFound == 1
    for k, v in docs.items():
        assert res.result.docs[0][k] == v


def test_multi_value_dates(si):
    docs = {
        "id": "978",
        "important_dts": [
            "1969-01-01",
            "1969-01-02",
        ],
    }
    si.add(docs)
    si.commit()
    _ = si.query(id=u"978").execute()


def test_highlighting(si):
    docs = {
        "id": "978-0641723445",
        "cat": ["book", "hardcover"],
        "name": "The Höhlentripp Strauß",
        "author": "Röüß Itoa",
        "series_t": "Percy Jackson and \N{UMBRELLA}nicode",
        "sequence_i": 1,
        "genre_s": "fantasy",
        "inStock": True,
        "price": 12.50,
        "pages_i": 384,
    }
    si.add(docs)
    si.commit()
    res = si.query(author=u"Röüß").highlight("author").execute()
    highlighted_field_result = "<em>Röüß</em> Itoa"
    # Does the highlighting attribute work?
    assert res.highlighting["978-0641723445"]["author"][0] == highlighted_field_result

    # Does each item have highlighting attributes?
    assert (
        res.result.docs[0]["solr_highlights"]["author"][0] == highlighted_field_result
    )


def test_count(si):
    docs = [
        {
            "id": "1",
            "genre_s": "fantasy",
        },
        {
            "id": "2",
            "genre_s": "fantasy",
        },
    ]
    si.add(docs)
    si.commit()
    ungrouped_count = si.query(genre_s="fantasy").count()
    ungrouped_count_expected = 2
    assert ungrouped_count == ungrouped_count_expected
    grouped_count = si.query(genre_s="fantasy").group_by("genre_s").count()
    grouped_count_expected = 1
    assert grouped_count == grouped_count_expected


def test_debug(si):
    docs = {
        "id": "978-0641723445",
        "cat": ["book", "hardcover"],
        "name": "The Höhlentripp Strauß",
        "author": "Röüß Itoa",
        "series_t": "Percy Jackson and \N{UMBRELLA}nicode",
        "sequence_i": 1,
        "genre_s": "fantasy",
        "inStock": True,
        "price": 12.50,
        "pages_i": 384,
    }
    si.add(docs)
    si.commit()
    res = si.query(author="Röüß").debug().execute()
    assert res.result.numFound == 1
    for k, v in docs.items():
        assert res.result.docs[0][k] == v
    assert "explain" in res.debug
    # deactivate
    res = si.query(author="Röüß").execute()
    assert "explain" not in res.debug


def test_spellcheck(si):
    opts = si.query(name=u"Monstes").spellcheck().options()
    assert {"q": "name:Monstes", "spellcheck": True} == opts


def test_extract(si):
    pdf = os.path.join(os.path.dirname(__file__), "data", "lipsum.pdf")
    with open(pdf, "rb") as f:
        data = si.extract(f)
    assert 0 == data.status
    assert "Lorem ipsum" in data.text
    assert ["pdfTeX-1.40.13"] == data.metadata["producer"]


def test_mlt(si, books):
    si.add(books)
    si.commit()
    res = (
        si.mlt_query("genre_s", interestingTerms="details", mintf=1, mindf=1)
        .query(id="978-0641723445")
        .execute()
    )
    assert res.result.numFound == 2
    assert res.interesting_terms == ["genre_s:fantasy", 1.0]
    assert [x["author"] for x in res.result.docs] == ["Rick Riordan", "Jostein Gaarder"]
