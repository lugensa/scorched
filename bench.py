from __future__ import print_function
from __future__ import unicode_literals
import scorched
import time
import datetime

from matplotlib import pyplot
from scorched.compat import is_py2

if is_py2:
    import sunburnt


def build(n):
    docs = []
    for i in range(n):
        doc = {'author_t': 'George R.R. Martin',
               'cat': 'book',
               'date_dt': datetime.datetime(2014, 3, 11, 10, 49, 0, 747991),
               'genre_s': 'fantasy',
               'id': '%s' % i,
               'inStock': True,
               'name': 'A fisch of Thrones',
               'price': 7.99,
               'sequence_i': 1,
               'series_t': 'A Song of Ice and Fire'}
        docs.append(doc)
    return docs


def run(n, interface):
    docs = build(n)
    si = interface("http://localhost:8983/solr/")
    start = time.clock()
    si.add(docs)
    si.commit()
    elapsed = (time.clock() - start)
    print("%s docs took %ss" % (len(docs), elapsed))
    query = si.query(name='fisch')
    res = si.search(**query.options())
    print("found %s" % res.result.numFound)
    si.delete_all()
    si.commit()
    return {'x': n, 'y': elapsed}

count = 21
if is_py2:
    data_sunburnt = []
    for i in [x*1000 for x in range(1, count)]:
        data_sunburnt.append(run(i, sunburnt.SolrInterface))

data_scorched = []
for i in [x*1000 for x in range(1, count)]:
    data_scorched.append(run(i, scorched.SolrInterface))

if is_py2:
    pyplot.plot(
        [x['x'] for x in data_sunburnt], [y['y'] for y in data_sunburnt], '-')
pyplot.plot(
    [x['x'] for x in data_scorched], [y['y'] for y in data_scorched], '-')
pyplot.title('Plotting adding speed')
pyplot.xlabel('Number documents')
pyplot.ylabel('Time in seconds (less is better)')
if is_py2:
    pyplot.legend(['sunburnt', 'scorched'])
else:
    pyplot.legend(['scorched'])
pyplot.savefig('bench.png')
pyplot.show()
