import json
import requests
import logging
import re

# Setup custom logging levels for Odoo client
DEBUG_RPC = 8
DEBUG_RPC_ANSWER = 4
logging.addLevelName(DEBUG_RPC, 'DEBUG_RPC')
logging.addLevelName(DEBUG_RPC_ANSWER, 'DEBUG_RPC_ANSWER')

class rpc_exception(Exception):
    def __init__(self, code, message, data=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data or message
        
    def __str__(self):
        return f"RPC Error {self.code}: {self.message}"

class JSONRPCClient:
    def __init__(self, url):
        self.url = url.rstrip('/')
        self.session = requests.Session()
        self.db = None
        self.uid = None
        self.password = None
        self.context = {}

    def authenticate(self, db, login, password):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "db": db,
                "login": login,
                "password": password
            },
            "id": 1
        }
        try:
            response = self.session.post(f"{self.url}/web/session/authenticate", 
                                        json=payload, timeout=15)
            response.raise_for_status()
            res = response.json()
            
            if 'error' in res:
                err = res['error']
                raise rpc_exception(err.get('code'), err.get('message'), err.get('data'))
            
            result = res['result']
            self.db = db
            self.uid = result.get('uid')
            self.password = password
            self.context = result.get('user_context', {})
            return result
        except Exception as e:
            if isinstance(e, rpc_exception): raise
            raise rpc_exception('connection_error', str(e))

    def call_kw(self, model, method, args=None, kwargs=None):
        if args is None: args = []
        if kwargs is None: kwargs = {}
        
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model,
                "method": method,
                "args": args,
                "kwargs": kwargs
            },
            "id": 1
        }
        
        url = f"{self.url}/web/dataset/call_kw"
        try:
            response = self.session.post(url, json=payload, timeout=60)
            response.raise_for_status()
            res = response.json()
            
            if 'error' in res:
                err = res['error']
                data = err.get('data', {})
                msg = err.get('message', 'Odoo Server Error')
                
                print(f"DEBUG: RPC ERROR: {msg}")
                if isinstance(data, dict) and 'debug' in data:
                    print(f"DEBUG: RPC TRACEBACK: {data['debug']}")
                
                # Dynamic field filtering logic (from stabilization phase)
                if isinstance(data, dict):
                    real_msg = data.get('message', msg)
                    debug = data.get('debug', '')
                    
                    bad_field = None
                    if "Invalid field" in debug or "Invalid field" in real_msg:
                        match = re.search(r"Invalid field '([^']+)'", debug or real_msg)
                        if match: bad_field = match.group(1)
                    elif "KeyError" in debug:
                        match = re.search(r"KeyError: '([^']+)'", debug)
                        if match: bad_field = match.group(1)
                    
                    if bad_field:
                        logging.warning(f"RPC: Auto-filtering invalid field '{bad_field}' and retrying...")
                        if method in ('read', 'search_read'):
                            if len(args) > 1 and isinstance(args[1], list):
                                if bad_field in args[1]:
                                    args[1] = [f for f in args[1] if f != bad_field]
                                    return self.call_kw(model, method, args, kwargs)
                            
                            # Check kwargs fields
                            if isinstance(kwargs, dict) and 'fields' in kwargs:
                                if bad_field in kwargs['fields']:
                                    kwargs['fields'] = [f for f in kwargs['fields'] if f != bad_field]
                                    return self.call_kw(model, method, args, kwargs)
                        
                        elif method in ('write', 'create'):
                            val_idx = 1 if method == 'write' else 0
                            if len(args) > val_idx and isinstance(args[val_idx], dict):
                                if bad_field in args[val_idx]:
                                    del args[val_idx][bad_field]
                                    return self.call_kw(model, method, args, kwargs)

                raise rpc_exception(err.get('code'), msg, data)
                
            return res['result']
        except Exception as e:
            if isinstance(e, rpc_exception): raise
            logging.error(f"RPC: JSON-RPC call_kw error: {e}")
            raise rpc_exception('connection_error', str(e))

    def execute(self, model, method, *args):
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "service": "object",
                "method": "execute",
                "args": (self.db, self.uid, self.password, model, method) + args
            },
            "id": 1
        }
        try:
            response = self.session.post(f"{self.url}/jsonrpc", json=payload, timeout=30)
            response.raise_for_status()
            res = response.json()
            if 'error' in res:
                err = res['error']
                raise rpc_exception(err.get('code'), err.get('message'), err.get('data'))
            return res['result']
        except Exception as e:
            if isinstance(e, rpc_exception): raise
            raise rpc_exception('connection_error', str(e))

    def get_view(self, model, view_id=None, view_type='form', context=None):
        if view_type == 'tree':
            view_type = 'list'
            
        kwargs = {
            'view_id': view_id,
            'view_type': view_type,
            'context': context or self.context
        }
        
        print(f"DEBUG: get_view for {model} ({view_type})", flush=True)
        try:
            res = self.call_kw(model, 'get_view', [], kwargs)
            
            if res and 'arch' in res and isinstance(res['arch'], str):
                # Legacy compatibility: replace <list> with <tree>
                res['arch'] = res['arch'].replace('<list ', '<tree ').replace('<list>', '<tree>').replace('</list>', '</tree>')
                
            # Process sub-models fields if present (from legacy model)
            if res and 'models' in res:
                if 'fields' not in res:
                    res['fields'] = {}
                for m_name, m_fields in res['models'].items():
                    if m_name == model and isinstance(m_fields, list):
                        print(f"DEBUG: fetching field definitions for {m_name}...", flush=True)
                        m_defs = self.call_kw(m_name, 'fields_get', [m_fields], {'context': context or self.context})
                        res['fields'].update(m_defs)
                    elif isinstance(m_fields, dict):
                        res['fields'].update(m_fields)
            
            return res
        except Exception as e:
            print(f"ERROR: get_view failed for {model}: {e}")
            raise e

    def load_menus(self):
        from gi.repository import GLib
        print("DEBUG: Loading all menus via search_read...")
        try:
            # Fetch all menus where the user has access
            all_menus = self.call_kw('ir.ui.menu', 'search_read', [[]], {
                'fields': ['id', 'name', 'parent_id', 'action', 'sequence'],
                'order': 'sequence, id'
            })
            
            # Build tree locally
            menu_map = {}
            for m in all_menus:
                m['children'] = []
                # Escape name for GTK markup
                name = m.get('name') or 'Menu'
                m['name'] = GLib.markup_escape_text(name)
                menu_map[m['id']] = m
            
            top_menus = []
            
            # First pass: build hierarchy
            for m in all_menus:
                parent = m.get('parent_id')
                parent_id = parent[0] if isinstance(parent, (list, tuple)) else parent
                
                if not parent_id or parent_id not in menu_map:
                    top_menus.append(m)
                else:
                    menu_map[parent_id]['children'].append(m)
            
            # Second pass: sort children by sequence
            def sort_menu_recursive(menus):
                menus.sort(key=lambda x: (x.get('sequence', 10), x.get('id', 0)))
                for m in menus:
                    if m.get('children'):
                        sort_menu_recursive(m['children'])
            
            sort_menu_recursive(top_menus)
            
            print(f"DEBUG: Menu tree built with {len(top_menus)} root modules.")
            return top_menus
        except Exception as e:
            print(f"DEBUG: search_read menus failed: {e}")
            # Final fallback: try load_menus_root
            try:
                res = self.call_kw('ir.ui.menu', 'load_menus_root', [], {})
                return res.get('children', []) if isinstance(res, dict) else []
            except:
                return []
