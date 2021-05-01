class TagSyncFilter:

    def __init__(self, name, domain=None):
        self.tag_name = name
        self.tag_domain = domain


    def tag(self):
        return (self.tag_name, self.tag_domain)


    def __str__(self):
        if tag_domain == None:
            return self.tag_name
        return '{}.{}'.format(self.tag_domain, self.tag_name)
