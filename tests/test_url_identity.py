"""Offline URL identity regressions. No scraping, publishing, or state writes."""
import pytest
from utils.helpers import canonical_url, url_to_id
from scraper.deduplicator import deduplicate

@pytest.mark.parametrize('url,expected', [
 ('https://example.com/story?utm_source=feed&utm_medium=rss#comments','https://example.com/story'),
 ('https://example.com/story?ref=feed&fbclid=abc&gclid=def','https://example.com/story'),
 ('https://news.ycombinator.com/item?id=123&utm_source=rss','https://news.ycombinator.com/item?id=123'),
 ('https://example.com/article?page=2&lang=en#top','https://example.com/article?page=2&lang=en'),
 ('https://example.com/story?UTM_CAMPAIGN=launch&ref_src=twsrc','https://example.com/story'),
])
def test_only_tracking_parameters_are_removed(url, expected):
    assert canonical_url(url) == expected

def test_query_identified_stories_keep_distinct_ids():
    assert url_to_id('https://news.ycombinator.com/item?id=123') != url_to_id('https://news.ycombinator.com/item?id=456')

def test_tracking_variants_keep_same_id():
    assert url_to_id('https://example.com/a?utm_source=x') == url_to_id('https://example.com/a?ref=y')

def test_distinct_query_stories_are_not_dropped_before_title_comparison():
    stories=[{'url':'https://news.ycombinator.com/item?id=123','title':'New telescope observes distant galaxy'}, {'url':'https://news.ycombinator.com/item?id=456','title':'Database engine adds transaction support'}]
    assert deduplicate(stories,past_urls=[]) == stories

def test_noncanonical_past_urls_are_normalized_for_history_dedup():
    assert deduplicate([{'url':'https://example.com/a?utm_source=new','title':'A fresh title'}],past_urls=['https://example.com/a?utm_source=old']) == []

@pytest.mark.parametrize('url', [
    'https://example.com/a;version=2?id=1&id=2&value=a%2Bb',
    'https://example.com/a?q=hello+world&empty=',
    'https://example.com/a?signature=A%2FB%3D&item=123',
])
def test_meaningful_query_encoding_order_and_path_params_are_preserved(url):
    assert canonical_url(url) == url

def test_file_state_history_is_normalized_without_reading_real_state(monkeypatch):
    monkeypatch.setattr('scraper.deduplicator.read_state',lambda:{'past_urls':['https://example.com/a?utm_source=old']})
    assert deduplicate([{'url':'https://example.com/a','title':'Already seen'}]) == []

@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    import socket
    def fail(*args, **kwargs):
        raise AssertionError('Network access is not permitted in URL identity tests')
    monkeypatch.setattr(socket.socket,'connect',fail)
    monkeypatch.setattr(socket,'create_connection',fail)
