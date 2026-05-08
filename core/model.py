from .session import session

class Model:
    def __init__(self, name):
        self.name = name

    def search_read(self, domain=None, fields=None, offset=0, limit=80, order=None, context=None):
        if domain is None: domain = []
        if fields is None: fields = ['id', 'display_name']
        
        ctx = dict(session.client.context or {})
        if context:
            ctx.update(context)
        
        return session.client.call_kw(self.name, 'search_read', [], {
            'domain': domain,
            'fields': fields,
            'offset': offset,
            'limit': limit,
            'order': order,
            'context': ctx
        })

    def read(self, ids, fields=None):
        return session.client.call_kw(self.name, 'read', [ids, fields], {
            'context': session.client.context
        })

    def get_view(self, view_id=None, view_type='form'):
        return session.client.get_view(self.name, view_id, view_type)
