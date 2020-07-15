import asyncio

from .yapi import YggdrasilAPI
from .tkinter_extensions import AioTk, Table, tk, ttk


tabs = ('Overview', 'Peers', 'DHT', 'Sessions', 'Switch peers', 'Allowed keys')

entries_defaults = {
    'state':   'readonly',  
    'relief':  'flat', 
    'justify': tk.CENTER, 
    'font':    'Consolas  11 bold'
}

entries_place = {
    'height':   20, 
    'relwidth': 0.5, 
    'relx':     0
}


def init_interface():
    """
    Creates, configes and launch GUI
    """
    loop = asyncio.get_event_loop()
    ygg = YggdrasilAPI()

    root = AioTk('root')
    root.title('Verdandi')
    root.geometry('800x500')
    notebook = ttk.Notebook(root)

    tables = get_tables(ygg)
    for tab_name in tabs:
        frame = ttk.Frame(notebook, name=tab_name.lower())
        notebook.add(frame, text=tab_name)
        #this excludes Overview page
        if tab_name not in tables:
            continue
        table_params = tables[tab_name]
        table = Table(frame, **table_params, name='table')
        table.place(relheight=1, relwidth=5/6, relx=1/6, rely=0)
    notebook.place(relx=0, rely=0, relheight=1, relwidth=1)

    overview = notebook.children['overview']
    self_node = loop.run_until_complete(ygg.getSelf())

    addr_tvar = tk.StringVar()
    addr = tk.Entry(overview, textvariable=addr_tvar, **entries_defaults)
    addr_tvar.set(self_node['addr'])
    addr.place(rely=1/24, **entries_place)

    subnet_tvar = tk.StringVar()
    subnet = tk.Entry(overview, textvariable=subnet_tvar, **entries_defaults)
    subnet_tvar.set(self_node['subnet'])
    subnet.place(rely=4/24, **entries_place)

    peers_table: Table = notebook.children['switch peers'].children['table']
    nodes = Table(overview, ('№', 'IP', 'endpoint'), 'IP', ('port', 'ip', 'faddr'))
    peers_table.add_replicant(nodes)
    nodes.place(relheight=15/24, relwidth=0.49, relx=0, rely=9/24)

    sessions_table: Table = notebook.children['sessions'].children['table']
    sessions = Table(overview, ('IP', 'received', 'sent'), 'IP', ('addr', 'bytes_recvd', 'bytes_sent'))
    sessions_table.add_replicant(sessions)
    sessions.place(relheight=15/24, relwidth=0.49, relx=0.51, rely=9/24)

    root.mainloop()


def get_tables(ygg):
    return {
        'Peers': {
            'updater': ygg.getPeers,
            'headings': ('IP', 'received', 'sent', 'endpoint', 'uptime'),
            'params': ('addr', 'bytes_recvd', 'bytes_sent', 'endpoint', 'uptime'),
            'unique_heading': 'IP',
        },
        'DHT': {
            'updater': ygg.getDHT,
            'headings': ('IP', 'coordinates', 'last seen'),
            'params': ('addr', 'coords', 'last_seen'),
            'unique_heading': 'IP',
            'identity_lvl': 1
        },
        'Sessions': {
            'updater': ygg.getSessions,
            'headings': ('IP', 'received', 'sent', 'uptime', 'MTU', 'MTU fixed', 'coordinates'),
            'params': ('addr', 'bytes_recvd', 'bytes_sent', 'uptime', 'mtu', 'was_mtu_fixed', 'coords'),
            'unique_heading': 'IP'
        },
        'Switch peers': {
            'updater': ygg.getSwitchPeers,
            'headings': ('port', 'IP', 'endpoint', 'coordinates', 'received', 'sent'),
            'params': ('port', 'ip', 'faddr', 'coords', 'bytes_recvd', 'bytes_sent'),
            'unique_heading': 'IP'
        },
        'Allowed keys': {
            'updater': ygg.getAllowedEncryptionPublicKeys,
            'headings': ('Key',),
            'params': ('key',),
            'unique_heading': 'Key'
        }
    }