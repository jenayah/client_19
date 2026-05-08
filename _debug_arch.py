import sys; sys.path.insert(0, '.')
from core.session import session
session.connect('http://localhost:1969', 'odoo19', 'admin', 'admin')
res = session.client.get_view('product.template', view_type='form')
arch = res['arch']
import xml.etree.ElementTree as ET
root = ET.fromstring(arch)
def show(n, depth=0):
    tag = n.tag
    if tag in ('form','sheet','group','notebook','page','field','div','header'):
        a = ' '.join(f'{k}={repr(v)[:30]}' for k,v in n.attrib.items() if k in ('name','string','widget','class','col'))
        print(' '*(depth*2) + f'<{tag} {a}>')
    for c in n:
        show(c, depth+1)
show(root)
