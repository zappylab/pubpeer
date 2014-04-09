#!/usr/bin/env python

"""
 author: Ken Youens-Clark <kyclark@gmail.com>
 date  : 8 April 2014
"""

from __future__ import print_function
import json
import pymysql
import requests
import sys

# ----------------------------------------------------------------------
def main():
    """main()"""

    url_tmpl = (
        'http://api.pubpeer.com/v1/publications/dump/%s?'
        'devkey=9bb8f08ebef172ec518f5a4504344ceb'
    )

    pdb = pymysql.connect(
        host='127.0.0.1',
        port=3306,
        user='kclark',
        passwd='',
        db='pubchase'
    )

    num_processed = 0
    num_bad = 0
    for page in range(1, 40):
        print('Getting page %s' % page)

        url = url_tmpl % page
        req = requests.get(url)
        data = req.json()

        if not data.has_key('publications'):
            num_bad += 1
            continue

        pubs = data['publications']

        if len(pubs) == 0:
            continue

        for pub in pubs:
            num_processed += 1

            if not pub.has_key('doi'):
                num_bad += 1
                continue

            ret = update(pub, pdb)

            if not ret:
                num_bad += 1

            print('%3d: %s (%s) => %s' % (
                num_processed,
                pub['pubpeer_id'],
                pub['comments_count'],
                'ok' if ret else 'bad'
            ))

    pdb.close()
    print('Done, processed %s, %s were bad, ratio: %d%%.' % (
        num_processed,
        num_bad,
        (num_bad * 100 /num_processed) if num_bad > 0 else 0,
    ))
    sys.exit(0)

# ----------------------------------------------------------------------
def update(pub, pdb):
    """inserts/updates the mysql db with pubpeer comment data"""

    comments = pub['comments']

    if (
        not pub['pubpeer_id']
        or pub['comments_count'] < 1
        or len(comments) == 0
    ):
        return False

    cur = pdb.cursor()
    cur.execute(
        """
        select count(*) as count
        from   pubpeer_comments
        where  pubpeer_id=%s
        """,
        (pub['pubpeer_id'])
    )

    exists = cur.fetchone()[0]

    if exists:
        cur.execute(
            """
            update pubpeer_comments
            set    comment_count=%s
            where  pubpeer_id=%s
            """,
            (pub['comments_count'], pub['pubpeer_id'])
        )
    else:
        pmid = get_pm_id(pub['doi'], pdb)

        if pmid:
            cur.execute(
                """
                insert
                into   pubpeer_comments
                       ( article_id, doi, comment_count, pubpeer_id,
                        link, comments )
                values ( %s, %s, %s, %s, %s, %s )
                """,
                (
                    pmid,
                    pub['doi'],
                    pub['comments_count'],
                    pub['pubpeer_id'],
                    pub['link'],
                    json.dumps(pub['comments'], indent=0)
                )
            )
            pdb.commit()
        else:
            return False

    return True

# ----------------------------------------------------------------------
def get_pm_id(doi, pdb):
    """converts DOI to pubmed id"""

    pm_url = (
        'http://www.pubmedcentral.nih.gov/utils/idconv/v1.0/?'
        'format=json&ids=%s'
    )

    ret = 0
    if doi:
        url = pm_url % doi
        req = requests.get(url)
        data = req.json()
        error = ''

        if not data.has_key('records'):
            error = 'no data from "%s"' % (url)
        else:
            for rec in data['records']:
                if rec.has_key('pmid'):
                    ret = rec['pmid']
                    break
                elif rec.has_key('errmsg'):
                    error = rec['errmsg']
                    break

    if not ret > 0:
        print(
            'Error getting PMID for "%s": %s' %
            (doi, error if error else 'unknown error'),
             file=sys.stderr
        )

        cur = pdb.cursor()
        cur.execute(
            """
            replace
            into   pubpeer_bad_doi (doi)
            values (%s)
            """,
            (doi)
        )
        pdb.commit()

    return ret

# ----------------------------------------------------------------------
main()
