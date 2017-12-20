import pytest
from graphapi.schema import schema
from opencivicdata.legislative.models import Bill
from .utils import populate_db


@pytest.mark.django_db
def setup():
    populate_db()


@pytest.mark.django_db
def test_bill_by_id(django_assert_num_queries):
    with django_assert_num_queries(17):
        result = schema.execute(''' {
            bill(id:"ocd-bill/1") {
                title
                classification
                subject
                abstracts {
                    abstract
                }
                otherTitles {
                    title
                }
                otherIdentifiers {
                    identifier
                }
                actions {
                    description
                    organization {
                        name
                        classification
                    }
                    relatedEntities {
                        name
                        entityType
                        organization { name }
                        person { name }
                    }
                }
                sponsorships {
                    name
                    classification
                }
                documents {
                    note
                    links { url }
                }
                versions {
                    note
                    links { url }
                }
                relatedBills {
                    legislativeSession
                    identifier
                    relationType
                    relatedBill {
                        title
                    }
                }
                sources { url }
                votes {
                    edges {
                        node {
                            votes {
                                option
                                voterName
                                voter { id name }
                            }
                            counts {
                                option
                                value
                            }
                        }
                    }
                }
            }
        }''')

    assert result.errors is None
    assert result.data['bill']['title'] == 'Moose Freedom Act'
    assert result.data['bill']['classification'] == ['bill', 'constitutional amendment']
    assert result.data['bill']['subject'] == ['nature']
    assert len(result.data['bill']['abstracts']) == 2
    assert len(result.data['bill']['otherTitles']) == 3
    assert len(result.data['bill']['actions']) == 3
    assert result.data['bill']['actions'][0]['organization']['classification'] == 'lower'
    assert result.data['bill']['actions'][0]['relatedEntities'][0]['person']['name'] != ''
    assert result.data['bill']['actions'][0]['relatedEntities'][0]['organization'] is None
    assert len(result.data['bill']['sponsorships']) == 2
    assert len(result.data['bill']['documents'][0]['links']) == 1
    assert len(result.data['bill']['versions'][0]['links']) == 2
    assert len(result.data['bill']['sources']) == 3
    assert len(result.data['bill']['relatedBills']) == 1
    assert 'Alces' in result.data['bill']['relatedBills'][0]['relatedBill']['title']
    assert len(result.data['bill']['votes']['edges']) == 1

    for vote in result.data['bill']['votes']['edges'][0]['node']['votes']:
        if vote['voterName'] == 'Amanda Adams':
            assert vote['voter']['name'] == 'Amanda Adams'
            break
    else:
        assert False, 'never found amanda'


@pytest.mark.django_db
def test_bill_by_jurisdiction_id_session_identifier(django_assert_num_queries):
    with django_assert_num_queries(1):
        result = schema.execute(''' {
            bill(jurisdiction:"ocd-jurisdiction/country:us/state:ak",
                 session:"2018",
                 identifier:"HB 1") {
                title
            }
        }''')
        assert result.errors is None
        assert result.data['bill']['title'] == 'Moose Freedom Act'


@pytest.mark.django_db
def test_bill_by_jurisdiction_name_session_identifier(django_assert_num_queries):
    with django_assert_num_queries(1):
        result = schema.execute(''' {
            bill(jurisdiction:"Alaska", session:"2018", identifier:"HB 1") {
                title
            }
        }''')
        assert result.errors is None
        assert result.data['bill']['title'] == 'Moose Freedom Act'


@pytest.mark.django_db
def test_bill_by_jurisdiction_session_identifier_incomplete():
    result = schema.execute(''' {
        bill(jurisdiction:"Alaska", identifier:"HB 1") {
            title
        }
    }''')
    assert len(result.errors) == 1
    assert 'must either pass' in result.errors[0].message


@pytest.mark.django_db
def test_bill_by_jurisdiction_session_identifier_404():
    result = schema.execute(''' {
        bill(jurisdiction:"Alaska", session:"2018" identifier:"HB 404") {
            title
        }
    }''')
    assert len(result.errors) == 1
    assert 'does not exist' in result.errors[0].message


@pytest.mark.django_db
def test_bills_by_jurisdiction(django_assert_num_queries):
    # 2 bills queries + 2 count queries
    with django_assert_num_queries(4):
        result = schema.execute(''' {
            ak: bills(jurisdiction:"Alaska") {
                edges { node { title } }
            }
            wy: bills(jurisdiction:"ocd-jurisdiction/country:us/state:wy") {
                edges { node { title } }
            }
        }''')
    assert result.errors is None
    # 26 total bills created
    assert len(result.data['ak']['edges'] + result.data['wy']['edges']) == 26


@pytest.mark.django_db
def test_bills_by_chamber(django_assert_num_queries):
    with django_assert_num_queries(4):
        result = schema.execute(''' {
            lower: bills(chamber:"lower") {
                edges { node { title } }
            }
            upper: bills(chamber:"upper") {
                edges { node { title } }
            }
        }''')
    assert result.errors is None
    # 26 total bills created
    assert len(result.data['lower']['edges'] + result.data['upper']['edges']) == 26


@pytest.mark.django_db
def test_bills_by_session(django_assert_num_queries):
    with django_assert_num_queries(4):
        result = schema.execute(''' {
            y2018: bills(session:"2018") {
                edges { node { title } }
            }
            y2017: bills(session:"2017") {
                edges { node { title } }
            }
        }''')
    assert result.errors is None
    # 26 total bills created
    assert len(result.data['y2017']['edges'] + result.data['y2018']['edges']) == 26


@pytest.mark.django_db
def test_bills_by_classification(django_assert_num_queries):
    with django_assert_num_queries(4):
        result = schema.execute(''' {
            bills: bills(classification: "bill") {
                edges { node { title } }
            }
            resolutions: bills(classification: "resolution") {
                edges { node { title } }
            }
        }''')
    assert result.errors is None
    # 26 total bills created
    assert len(result.data['bills']['edges'] + result.data['resolutions']['edges']) == 26


@pytest.mark.django_db
def test_bills_by_subject():
    result = schema.execute(''' {
        a: bills(subject:"a") {
            edges { node { title, subject } }
        }
        b: bills(subject:"b") {
            edges { node { title, subject } }
        }
        c: bills(subject:"c") {
            edges { node { title, subject } }
        }
        d: bills(subject:"d") {
            edges { node { title, subject } }
        }
        e: bills(subject:"e") {
            edges { node { title, subject } }
        }
        f: bills(subject:"f") {
            edges { node { title, subject } }
        }
    }''')
    assert result.errors is None

    # some sanity checking on subject responses
    count = 0
    for subj, bills in result.data.items():
        for bill in bills['edges']:
            assert subj in bill['node']['subject']
            count += 1
    assert count > 0


@pytest.mark.django_db
def test_bills_by_updated_since():
    # set updated timestamps
    middle_date = Bill.objects.all().order_by('updated_at')[20].updated_at

    result = schema.execute('''{
        all: bills(updatedSince: "2017-01-01T00:00:00Z") {
            edges { node { title } }
        }
        some: bills(updatedSince: "%s") {
            edges { node { title } }
        }
        none: bills(updatedSince: "2030-01-01T00:00:00Z") {
            edges { node { title } }
        }
    }''' % middle_date)

    assert result.errors is None
    assert len(result.data['all']['edges']) == 26
    assert len(result.data['some']['edges']) == 6
    assert len(result.data['none']['edges']) == 0


@pytest.mark.django_db
def test_bills_queries(django_assert_num_queries):
    with django_assert_num_queries(21):
        result = schema.execute(''' {
            bills { edges { node {
                title
                classification
                subject
                abstracts {
                    abstract
                }
                otherTitles {
                    title
                }
                otherIdentifiers {
                    identifier
                }
                actions {
                    description
                    organization {
                        name
                        classification
                    }
                    relatedEntities {
                        name
                        entityType
                        organization { name }
                        person { name }
                    }
                }
                sponsorships {
                    name
                    classification
                }
                documents {
                    note
                    links { url }
                }
                versions {
                    note
                    links { url }
                }
                relatedBills {
                    legislativeSession
                    identifier
                    relationType
                    relatedBill {
                        title
                    }
                }
                sources { url }
                votes {
                    edges {
                        node {
                            votes {
                                option
                                voterName
                                voter { id }
                            }
                            counts {
                                option
                                value
                            }
                        }
                    }
                }
            } } }
        }''')

    assert result.errors is None
    assert len(result.data['bills']['edges']) == 26


@pytest.mark.django_db
def test_bills_pagination_forward():
    bills = []

    result = schema.execute('''{
        bills(first: 5) {
            edges { node { identifier } }
            pageInfo { endCursor hasNextPage }
        }
    }''')
    page = [n['node']['identifier'] for n in result.data['bills']['edges']]
    bills += page

    while result.data['bills']['pageInfo']['hasNextPage']:
        result = schema.execute('''{
            bills(first: 5, after:"%s") {
                edges { node { identifier } }
                pageInfo { endCursor hasNextPage }
            }
        }''' % result.data['bills']['pageInfo']['endCursor'])
        page = [n['node']['identifier'] for n in result.data['bills']['edges']]
        bills += page
        assert len(page) <= 5

    assert len(bills) == 26


@pytest.mark.django_db
def test_bills_pagination_backward():
    bills = []

    result = schema.execute('''{
        bills(last: 5) {
            edges { node { identifier } }
            pageInfo { startCursor hasPreviousPage }
        }
    }''')
    page = [n['node']['identifier'] for n in result.data['bills']['edges']]
    bills += page

    while result.data['bills']['pageInfo']['hasPreviousPage']:
        result = schema.execute('''{
            bills(last: 5, before:"%s") {
                edges { node { identifier } }
                pageInfo { startCursor hasPreviousPage }
            }
        }''' % result.data['bills']['pageInfo']['startCursor'])
        page = [n['node']['identifier'] for n in result.data['bills']['edges']]
        bills += page
        assert len(page) <= 5

    assert len(bills) == 26
