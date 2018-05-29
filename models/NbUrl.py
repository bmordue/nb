class NbUrl:
    def __init__(self, url):
        self.url = url

    def get_domain_info(self):
        domain = self.url.split('/')[2]
        toplevel = '.'.join(domain.split('.')[-2:])
        if len(domain.split('.')) > 2:
            toplevel_new = '.'.join(domain.split('.')[1:])
        else:
            toplevel_new = domain
        return (domain, toplevel, toplevel_new)
