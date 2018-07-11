from datadog import statsd

from models.NbUrl import NbUrl
from utility import nb_logging, client_factory

logger = nb_logging.setup_logger('add_domains')


@statsd.timed('nb.add_domains.add_domains')
def add_domains():
    db_client = client_factory.get_db_client()
    db_client.ensure_domains_table_exists()

    rows = db_client.list_urls()

    for row in rows:
        # nb_hash = row['nb_hash']
        # nb_url = NbUrl(row['url'])
        nb_hash = row[0]
        nb_url = NbUrl(row[1])
        domain, toplevel, toplevel_new = nb_url.get_domain_info()
        db_client.insert_domain_entry(nb_hash, nb_url.url, domain, toplevel, toplevel_new)


if __name__ == "__main__":
    add_domains()
