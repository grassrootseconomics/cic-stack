class TagSyncFilter:
    """Holds tag name and domain for an implementing filter.

    :param name: Tag value 
    :type name: str
    :param domain: Tag domain
    :type domain: str
    """

    def __init__(self, name, domain=None):
        self.tag_name = name
        self.tag_domain = domain


    def tag(self):
        """Return tag value/domain.

        :rtype: Tuple
        :returns: tag value/domain.
        """
        return (self.tag_name, self.tag_domain)


    def __str__(self):
        if self.tag_domain == None:
            return self.tag_name
        return '{}.{}'.format(self.tag_domain, self.tag_name)
