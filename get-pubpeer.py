#!/usr/bin/env python

"""
 author: Ken Youens-Clark <kyclark@gmail.com>
 date  : 8 April 2014
"""

from __future__ import print_function
from datetime import datetime
import argparse
import itertools
import json
import pymysql
import requests
import sys

# ----------------------------------------------------------------------
def main():
    """main()"""

    argp = argparse.ArgumentParser(description='get PubPeer comment info')
    argp.add_argument('-p', dest='page', type=int)
    args = argp.parse_args()

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

    cursor = pdb.cursor()
    cursor.execute(
        """
        select UNIX_TIMESTAMP(max(last_modified)) from pubpeer_comments
        """
    );

    last_mod = cursor.fetchone()[0]
    last_run = datetime.fromtimestamp(last_mod) if last_mod else None;
    num_processed = 0
    num_bad = 0
    page = args.page or 1

    while True:
        print('Getting page %s' % page)

        url = url_tmpl % page
        req = requests.get(url)
        data = req.json()

        if not data.has_key('publications'):
            num_bad += 1
            continue

        pubs = data['publications']
        if len(pubs) == 0:
            print('No more publications, quitting.');
            break

        latest_comment = max(map(
            lambda x: x['date'],
            list(itertools.chain( *map(lambda x: x['comments'], pubs)))
        ))

        if latest_comment and last_run:
            max_date = datetime.fromtimestamp(int(latest_comment)) 
            if max_date < last_run:
                print('No new comments since %s, quitting.' % last_run)
                break

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

        page += 1

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

    pm_url_backup = ( 
        'http://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?'
        'db=pubmed&retmode=json&term=%s'
    )

    ret = 0
    if doi:
        url = pm_url % doi
        req = requests.get(url)
        data = req.json()
        error = ''

        if data.has_key('records'):
            for rec in data['records']:
                if rec.has_key('pmid'):
                    ret = rec['pmid']
                    break
                elif rec.has_key('errmsg'):
                    error = rec['errmsg']
                    break

        if not ret > 0:
            url = pm_url_backup % doi
            req = requests.get(url)
            data = req.json()

            if (
                data.has_key('esearchresult') 
                and int(data['esearchresult']['count']) == 1
            ):
                ret = data['esearchresult']['idlist'][0]

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
